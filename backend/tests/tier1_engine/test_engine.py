from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.engine.engine import RuleEngine, RuleSnapshot
from app.engine.expressions import FakeJudgeClient

NY = ZoneInfo("America/New_York")


def _hours():
    return {
        "timezone": "America/New_York",
        "hours_by_day": {
            "mon": {"start": "07:00", "end": "19:00"},
            "tue": {"start": "07:00", "end": "19:00"},
            "wed": {"start": "07:00", "end": "19:00"},
            "thu": {"start": "07:00", "end": "19:00"},
            "fri": {"start": "07:00", "end": "19:00"},
            "sat": {"start": "07:00", "end": "19:00"},
        },
        "closed_days": ["sun"],
        "block_message": "Closed Sunday",
    }


def _zips():
    return {
        "allowed_zips": ["32801", "32802"],
        "denied_zips": ["32803"],
        "block_message": "Out of area",
    }


def _services():
    return {
        "allowed_services": ["hvac", "plumbing"],
        "block_message": "Outside trade",
    }


def _eligibility():
    return {
        "homeowner_required": True,
        "exclude_renters": True,
        "membership_required": False,
        "block_message": "Homeowner only",
        "required_state_fields": ["is_homeowner"],
    }


def _lead_time():
    return {
        "minimum_hours": 48,
        "applies_to_service_types": ["hvac"],
        "bypass_if_state_field": "is_emergency",
        "bypass_if_state_value": True,
        "block_message": "Need 48h",
    }


def _conditional_after_hours():
    return {
        "trigger": {
            "op": "all_of",
            "children": [
                {"op": "eq", "field": "args.is_after_hours", "value": True},
                {"op": "eq", "field": "state.is_existing_customer", "value": False},
            ],
        },
        "block_message": "Members only after-hours",
    }


def _snap(rule_type: str, params: dict, *, priority: int = 100, name: str = "rule") -> RuleSnapshot:
    return RuleSnapshot(
        id=uuid4(),
        rule_type=rule_type,
        name=name,
        parameters=params,
        applies_to_tools=["book_appointment"],
        priority=priority,
    )


# -------------------- business_hours --------------------


SUN_NOON = datetime(2026, 5, 24, 12, 0, tzinfo=NY)        # Sunday
MON_NOON = datetime(2026, 5, 25, 12, 0, tzinfo=NY)        # Monday at noon
MON_EVENING = datetime(2026, 5, 25, 22, 0, tzinfo=NY)     # Monday 10 PM


@pytest.mark.parametrize(
    "appointment,expected",
    [
        # Sunday 10 AM proposed — always blocked (closed_days)
        ({"date": "2026-05-24", "time": "10:00"}, "blocked"),
        # Monday 12:00 PM proposed — within hours
        ({"date": "2026-05-25", "time": "12:00"}, "accepted"),
        # Monday 10 PM proposed — outside hours
        ({"date": "2026-05-25", "time": "22:00"}, "blocked"),
        # No date supplied — needs_info ("you'd never dispatch right now")
        ({}, "needs_info"),
    ],
)
def test_business_hours(appointment, expected):
    eng = RuleEngine([_snap("business_hours", _hours(), priority=200, name="hours")])
    args = {"service_type": "hvac", **appointment}
    res = eng.check("book_appointment", args, business=None, state=None, current_time=MON_NOON)
    assert res.outcome == expected


# -------------------- service_area_zip --------------------


def test_zip_pass_block_needs_info():
    eng = RuleEngine([_snap("service_area_zip", _zips(), priority=180, name="zips")])
    pass_res = eng.check("book_appointment", {"address_zip": "32801"}, None, None, MON_NOON)
    block_res = eng.check("book_appointment", {"address_zip": "99999"}, None, None, MON_NOON)
    deny_res = eng.check("book_appointment", {"address_zip": "32803"}, None, None, MON_NOON)
    needs_res = eng.check("book_appointment", {}, None, None, MON_NOON)
    assert pass_res.outcome == "accepted"
    assert block_res.outcome == "blocked"
    assert deny_res.outcome == "blocked"
    assert needs_res.outcome == "needs_info"
    assert "address_zip" in needs_res.required_fields


# -------------------- services_offered --------------------


def test_services_pass_and_block():
    eng = RuleEngine([_snap("services_offered", _services(), name="services")])
    assert eng.check("book_appointment", {"service_type": "hvac"}, None, None, MON_NOON).outcome == "accepted"
    assert eng.check("book_appointment", {"service_type": "roofing"}, None, None, MON_NOON).outcome == "blocked"


def test_services_needs_info_when_missing():
    eng = RuleEngine([_snap("services_offered", _services(), name="services")])
    res = eng.check("book_appointment", {}, None, None, MON_NOON)
    assert res.outcome == "needs_info"
    assert "service_type" in res.required_fields


# -------------------- customer_eligibility --------------------


def test_eligibility_needs_info_then_block_then_pass():
    rule = _snap("customer_eligibility", _eligibility(), priority=170, name="elig")
    eng = RuleEngine([rule])
    no_state = eng.check("book_appointment", {}, None, None, MON_NOON)
    assert no_state.outcome == "needs_info"
    not_homeowner = eng.check("book_appointment", {}, None, {"is_homeowner": False}, MON_NOON)
    assert not_homeowner.outcome == "blocked"
    homeowner = eng.check("book_appointment", {}, None, {"is_homeowner": True}, MON_NOON)
    assert homeowner.outcome == "accepted"


def test_eligibility_service_type_filter_passes_through_unrelated_services():
    """When applies_to_service_types is set, the rule short-circuits for other services."""
    params = {**_eligibility(), "applies_to_service_types": ["hvac_install", "electrical_install"]}
    rule = _snap("customer_eligibility", params, priority=170, name="elig_scoped")
    eng = RuleEngine([rule])
    # In-scope service: rule fires (needs_info because no homeowner state)
    in_scope = eng.check(
        "book_appointment", {"service_type": "hvac_install"}, None, None, MON_NOON
    )
    assert in_scope.outcome == "needs_info"
    # Out-of-scope service: rule short-circuits to pass
    out_of_scope = eng.check(
        "book_appointment", {"service_type": "drain_cleaning"}, None, None, MON_NOON
    )
    assert out_of_scope.outcome == "accepted"
    # Out-of-scope with renter: rule still doesn't fire (passes)
    renter_repair = eng.check(
        "book_appointment",
        {"service_type": "hvac_repair"},
        None,
        {"is_homeowner": False},
        MON_NOON,
    )
    assert renter_repair.outcome == "accepted"


# -------------------- lead_time_minimum --------------------


def test_lead_time_block_and_bypass():
    rule = _snap("lead_time_minimum", _lead_time(), name="lead")
    eng = RuleEngine([rule])
    soon = MON_NOON.replace(hour=14)  # 2 hours from now (well under 48)
    block_res = eng.check(
        "book_appointment",
        {"service_type": "hvac", "date": soon.date().isoformat(), "time": soon.time().isoformat(timespec="minutes")},
        None,
        None,
        MON_NOON,
    )
    assert block_res.outcome == "blocked"

    bypass_res = eng.check(
        "book_appointment",
        {"service_type": "hvac", "date": soon.date().isoformat(), "time": soon.time().isoformat(timespec="minutes")},
        None,
        {"is_emergency": True},
        MON_NOON,
    )
    assert bypass_res.outcome == "accepted"


def test_lead_time_does_not_apply_to_other_services():
    rule = _snap("lead_time_minimum", _lead_time(), name="lead")
    eng = RuleEngine([rule])
    soon = MON_NOON.replace(hour=14)
    res = eng.check(
        "book_appointment",
        {"service_type": "plumbing", "date": soon.date().isoformat(), "time": soon.time().isoformat(timespec="minutes")},
        None,
        None,
        MON_NOON,
    )
    assert res.outcome == "accepted"


# -------------------- conditional_block --------------------


def test_conditional_block_after_hours_member():
    rule = _snap("conditional_block", _conditional_after_hours(), name="afterhours")
    eng = RuleEngine([rule])
    not_member = eng.check(
        "book_appointment",
        {"is_after_hours": True},
        None,
        {"is_existing_customer": False},
        MON_NOON,
    )
    member = eng.check(
        "book_appointment",
        {"is_after_hours": True},
        None,
        {"is_existing_customer": True},
        MON_NOON,
    )
    daytime = eng.check(
        "book_appointment",
        {"is_after_hours": False},
        None,
        {"is_existing_customer": False},
        MON_NOON,
    )
    assert not_member.outcome == "blocked"
    assert member.outcome == "accepted"
    assert daytime.outcome == "accepted"


def test_conditional_block_with_llm_judge():
    rule_params = {
        "trigger": {
            "op": "all_of",
            "children": [
                {"op": "eq", "field": "args.kind", "value": "after_hours"},
                {
                    "op": "not",
                    "child": {
                        "op": "llm_judge",
                        "field": "state.reported_issue",
                        "question": "Is this an emergency requiring immediate attention?",
                    },
                },
            ],
        },
        "block_message": "After hours and not an emergency",
    }
    rule = _snap("conditional_block", rule_params, name="afteremergency")
    eng = RuleEngine([rule], judge=FakeJudgeClient(answers={"emergency": True}))
    not_emergency_eng = RuleEngine(
        [rule], judge=FakeJudgeClient(answers={"emergency": False})
    )
    args = {"kind": "after_hours"}
    state = {"reported_issue": "leak"}
    assert eng.check("book_appointment", args, None, state, MON_NOON).outcome == "accepted"
    assert not_emergency_eng.check("book_appointment", args, None, state, MON_NOON).outcome == "blocked"


# -------------------- aggregation --------------------


def test_aggregation_needs_info_dominates_block():
    biz_hours = _snap("business_hours", _hours(), priority=200, name="hours")
    services = _snap("services_offered", _services(), priority=160, name="services")
    eng = RuleEngine([biz_hours, services])
    # Sunday + missing service_type → both fire; needs_info should win.
    res = eng.check("book_appointment", {}, None, None, SUN_NOON)
    assert res.outcome == "needs_info"
    assert "service_type" in res.required_fields


def test_aggregation_priority_picks_primary_blocker():
    high_pri = _snap("business_hours", _hours(), priority=300, name="biz")
    low_pri = _snap("services_offered", _services(), priority=100, name="services")
    eng = RuleEngine([low_pri, high_pri])
    # Sunday booking + roofing → both block; primary should be the higher-priority biz hours.
    res = eng.check(
        "book_appointment",
        {"service_type": "roofing", "date": "2026-05-24", "time": "10:00"},
        None,
        None,
        MON_NOON,
    )
    assert res.outcome == "blocked"
    assert res.primary_rule_name == "biz"
    assert len(res.fired_rules) == 2


def test_engine_filters_by_applies_to_tools():
    rule = _snap("services_offered", _services(), name="services")
    eng = RuleEngine([rule])
    res = eng.check("escalate_to_human", {}, None, None, MON_NOON)
    assert res.outcome == "accepted"


def test_required_state_fields_aggregated():
    rules = [
        _snap("customer_eligibility", _eligibility(), name="elig"),
        _snap("service_area_zip", _zips(), name="zips"),
    ]
    eng = RuleEngine(rules)
    fields = eng.required_state_fields("book_appointment")
    assert "is_homeowner" in fields
    assert "address_zip" in fields
