"""Idempotent seed for the three case-study businesses (§ 15).

Each business carries a rule set deliberately chosen to exercise different
evaluator paths — typed rules, llm_judge, nested combinators, multiple
required_state_fields, lead-time bypass, different timezones, etc.

`run_if_empty()` runs on every backend boot; `wipe_rules_and_reseed()` is
called by POST /api/admin/reseed-rules to refresh the rule set without
touching conversations / audit history.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import AuditLog, Business, Conversation, Message, Rule, TestCase

log = logging.getLogger(__name__)

DEL_AIR_ID = UUID("aaaa1111-aaaa-1111-aaaa-111111111111")  # renamed to Sunrise Home Services
IMPROVEIT_ID = UUID("bbbb2222-bbbb-2222-bbbb-222222222222")
PIPEDREAMS_ID = UUID("cccc3333-cccc-3333-cccc-333333333333")
# 9 fictional cross-trade businesses for the 500-test corpus
CASCADE_ID = UUID("dddd4444-dddd-4444-dddd-444444444444")
MOUNTAIN_VIEW_ID = UUID("eeee5555-eeee-5555-eeee-555555555555")
ATLANTIC_POOL_ID = UUID("ffff6666-ffff-6666-ffff-666666666666")
BAY_AREA_ID = UUID("11117777-1111-7777-1111-777777777777")
PRAIRIEFENCE_ID = UUID("22228888-2222-8888-2222-888888888888")
GARDENWORKS_ID = UUID("33339999-3333-9999-3333-999999999999")
DOORMASTER_ID = UUID("4444aaaa-4444-aaaa-4444-aaaaaaaaaaaa")
PURE_AIR_ID = UUID("5555bbbb-5555-bbbb-5555-bbbbbbbbbbbb")
SUNSET_BATH_ID = UUID("6666cccc-6666-cccc-6666-cccccccccccc")


# --------------------------------------------------------------------------- #
# Rule-builder helpers
# --------------------------------------------------------------------------- #


def _r(
    rule_type: str,
    name: str,
    description: str,
    parameters: dict[str, Any],
    *,
    applies_when_description: str = "",
    applies_to_tools: list[str] | None = None,
    enforcement_mode: str = "block",
    priority: int = 100,
    source_prompt: str | None = None,
) -> dict[str, Any]:
    return {
        "rule_type": rule_type,
        "name": name,
        "description": description,
        "parameters": parameters,
        "applies_when_description": applies_when_description,
        "applies_to_tools": applies_to_tools or [],
        "enforcement_mode": enforcement_mode,
        "priority": priority,
        "is_active": True,
        "source_prompt": source_prompt,
    }


# --------------------------------------------------------------------------- #
# Sunrise Home Services — Florida HVAC / plumbing / electrical / IAQ. Eastern time.
# Rule mix exercises: typed rules, llm_judge on reported_issue, multiple
# required_state_fields, lead-time bypass, numeric state-field comparison
# (property_year_built), and two output_constraint severities.
# --------------------------------------------------------------------------- #


def _del_air() -> dict[str, Any]:
    return {
        "id": DEL_AIR_ID,
        "name": "Sunrise Home Services",
        "timezone": "America/New_York",
        "description": "Florida multi-trade — HVAC, plumbing, electrical, indoor air quality. Care Club membership for after-hours emergencies.",
        "rules": [
            _r(
                "business_hours",
                "Standard operating hours",
                "Open Mon-Fri 7 AM–7 PM, Sat 8 AM–4 PM, closed Sundays.",
                {
                    "timezone": "America/New_York",
                    "hours_by_day": {
                        **{d: {"start": "07:00", "end": "19:00"} for d in ("mon", "tue", "wed", "thu", "fri")},
                        "sat": {"start": "08:00", "end": "16:00"},
                    },
                    "closed_days": ["sun"],
                    "block_message": "We're closed Sundays — we'll be back at 7 AM Monday.",
                },
                applies_when_description="Customer wants to book or check availability.",
                applies_to_tools=["book_appointment", "check_availability"],
                priority=200,
            ),
            _r(
                "service_area_zip",
                "Central Florida service ZIPs",
                "Tampa, Orlando, and surrounding ZIP codes only. Hyde Park (33606) is on the deny-list because we don't have crews there yet.",
                {
                    "allowed_zips": [
                        "32801","32803","32804","32805","32806","32807","32809","32812",
                        "32814","32820","32822","32824","32825","32827","32828","32829",
                        "32831","32832","32833","32835","32836","32837","32839",
                        "33602","33603","33604","33605","33607","33609","33610","33611",
                        "33612","33613","33614","33615","33616","33617","33618","33619",
                        "33620","33621","33624","33625","33626","33629","33647",
                    ],
                    "denied_zips": ["33606"],
                    "block_message": "We don't service that ZIP — happy to refer a partner.",
                },
                applies_when_description="Customer requests work outside our service area.",
                applies_to_tools=["book_appointment", "lookup_service_area"],
                priority=180,
            ),
            _r(
                "services_offered",
                "Services we offer",
                "HVAC, plumbing, electrical, and indoor air quality only.",
                {
                    "allowed_services": ["hvac", "plumbing", "electrical", "indoor_air_quality"],
                    "block_message": "That's outside our trade — try someone who specializes in it.",
                },
                applies_to_tools=["book_appointment"],
                priority=160,
            ),
            _r(
                "conditional_block",
                "Members-only after-hours emergencies",
                "After-hours emergency dispatch is reserved for existing Comfort Club members.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.is_after_hours", "value": True},
                            {"op": "eq", "field": "state.is_existing_customer", "value": False},
                        ],
                    },
                    "block_message": "After-hours emergency service is reserved for Comfort Club members. Want me to start a regular morning appointment instead?",
                },
                applies_when_description="Caller is non-member asking for after-hours dispatch.",
                applies_to_tools=["book_appointment"],
                priority=150,
                source_prompt="Members-only emergency service after hours",
            ),
            _r(
                "conditional_block",
                "Late-day plumbing requires emergency",
                "Plumbing booked after 4 PM is only accepted when the reported issue actually sounds like an emergency.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "plumbing"},
                            {"op": "gte", "field": "args.time", "value": "16:00"},
                            {
                                "op": "not",
                                "child": {
                                    "op": "llm_judge",
                                    "field": "state.reported_issue",
                                    "question": "Does this sound like a plumbing emergency requiring same-day attention (e.g. flooding, no water, sewage backup)?",
                                },
                            },
                        ],
                    },
                    "block_message": "We can't dispatch plumbing this late unless it's an emergency. Let's pick a morning slot instead.",
                },
                applies_when_description="Customer asks for plumbing late in the day.",
                applies_to_tools=["book_appointment"],
                priority=145,
                source_prompt="Block plumbing after 4 PM unless it sounds like an emergency",
            ),
            _r(
                "lead_time_minimum",
                "HVAC installs require 48 hours notice",
                "New HVAC installations need at least 48 hours of advance scheduling. Bypassed when the conversation state says is_emergency.",
                {
                    "minimum_hours": 48,
                    "applies_to_service_types": ["hvac"],
                    "bypass_if_state_field": "is_emergency",
                    "bypass_if_state_value": True,
                    "block_message": "HVAC installs need at least 48 hours of lead time. We can fast-track if it's an emergency.",
                },
                applies_when_description="Customer wants HVAC install on a tight timeline.",
                applies_to_tools=["book_appointment"],
                priority=140,
            ),
            _r(
                "conditional_block",
                "Older homes need a site visit before whole-home rewires",
                "Homes built before 1970 require an in-person electrical inspection before booking a whole-home rewire.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "electrical"},
                            {"op": "eq", "field": "args.scope", "value": "whole_home"},
                            {"op": "lt", "field": "state.property_year_built", "value": 1970},
                        ],
                    },
                    "block_message": "For pre-1970 homes we need a quick in-person inspection before quoting a whole-home rewire. Want to book the inspection?",
                },
                applies_when_description="Whole-home electrical rewire on a vintage property.",
                applies_to_tools=["book_appointment"],
                priority=130,
                source_prompt="Pre-1970 homes can't get whole-home rewires without a site visit",
            ),
            _r(
                "output_constraint",
                "Mention Comfort Club benefits",
                "When discussing service plans, mention the Comfort Club membership benefits in a friendly, low-pressure way.",
                {
                    "instruction": "When the customer asks about ongoing service, recurring maintenance, service plans, discounts, pricing, or weekend/after-hours availability, mention the **Comfort Club** membership by name in your reply. Be specific (priority scheduling, discounted repairs, after-hours access). Skip the mention when the customer is in a stressful moment (active emergency, cancellation), is already a Comfort Club member, or has already declined the offer in this conversation.",
                    "severity": "guidance",
                },
                priority=80,
            ),
            _r(
                "output_constraint",
                "Empathetic tone for emergencies",
                "When state.is_emergency is true or the customer describes flooding/no-AC-in-summer/etc, lead with empathy.",
                {
                    "instruction": "If the conversation state shows an emergency or the customer describes a clearly urgent issue (flooding, broken AC in summer, no hot water in winter), open the response with empathy before any logistics.",
                    "severity": "must",
                },
                priority=70,
            ),
        ],
    }


# --------------------------------------------------------------------------- #
# ImproveIt — Midwest + Mid-Atlantic remodeling. Eastern time.
# Rule mix exercises: homeowner_required + exclude_renters, single-line
# conditional_block on numeric arg, llm_judge as positive trigger, lead-time
# with category filter, regex-driven block on free text.
# --------------------------------------------------------------------------- #


def _improveit() -> dict[str, Any]:
    return {
        "id": IMPROVEIT_ID,
        "name": "ImproveIt Home Remodeling",
        "timezone": "America/New_York",
        "description": "Bath, shower, roofing, siding, and window remodeling — Midwest + Mid-Atlantic.",
        "rules": [
            _r(
                "business_hours",
                "Standard hours",
                "Mon–Fri 8 AM to 8 PM, Sat 9 AM to 5 PM, closed Sunday.",
                {
                    "timezone": "America/New_York",
                    "hours_by_day": {
                        "mon": {"start": "08:00", "end": "20:00"},
                        "tue": {"start": "08:00", "end": "20:00"},
                        "wed": {"start": "08:00", "end": "20:00"},
                        "thu": {"start": "08:00", "end": "20:00"},
                        "fri": {"start": "08:00", "end": "20:00"},
                        "sat": {"start": "09:00", "end": "17:00"},
                    },
                    "closed_days": ["sun"],
                    "block_message": "We're closed Sundays — we'll follow up first thing Monday.",
                },
                applies_to_tools=["book_appointment", "check_availability"],
                priority=200,
            ),
            _r(
                "service_area_zip",
                "Midwest + Mid-Atlantic ZIPs",
                "Selected ZIPs across Ohio, Pennsylvania, Maryland, Virginia, and North Carolina.",
                {
                    "allowed_zips": [
                        "43017","43054","43081","43082","43085","43209","43215","43219","43221","43230",
                        "15201","15202","15203","15206","15208","15217","15218","15220","15221","15222",
                        "21043","21044","21045","21075","21076","21090","21117","21208",
                        "23230","23233","23235","23236","23294",
                        "27513","27518","27519","27560","27607","27612",
                    ],
                    "denied_zips": [],
                    "block_message": "We're not in that area yet — happy to share a referral.",
                },
                applies_to_tools=["book_appointment", "lookup_service_area"],
                priority=180,
            ),
            _r(
                "services_offered",
                "Remodeling services",
                "Bath remodel, shower install, roofing, siding, windows.",
                {
                    "allowed_services": ["bath_remodel", "shower_install", "roofing", "siding", "windows"],
                    "block_message": "That's not part of our remodeling lineup.",
                },
                applies_to_tools=["book_appointment"],
                priority=160,
            ),
            _r(
                "customer_eligibility",
                "Homeowner required for remodels",
                "Remodels require the customer to be the homeowner. Renters explicitly excluded.",
                {
                    "homeowner_required": True,
                    "exclude_renters": True,
                    "membership_required": False,
                    "block_message": "Remodel work requires the homeowner — we can't proceed if it's a rental.",
                    "required_state_fields": ["is_homeowner"],
                },
                applies_when_description="Customer asks for any remodel work.",
                applies_to_tools=["book_appointment"],
                priority=170,
            ),
            _r(
                "conditional_block",
                "Bath installs are one-day jobs",
                "Bath installations are scoped as single-day work; longer estimates need to be requoted.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "bath_remodel"},
                            {"op": "gte", "field": "args.estimated_days", "value": 2},
                        ],
                    },
                    "block_message": "Bath installs are one-day jobs — let's plan around a single appointment.",
                },
                applies_to_tools=["book_appointment"],
                priority=150,
                source_prompt="Bath installs are one-day only",
            ),
            _r(
                "conditional_block",
                "Storm-damage roofing routes to emergency",
                "When a roofing request describes storm damage, the regular booking flow is blocked so we route the customer to the storm-damage emergency channel.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "roofing"},
                            {
                                "op": "llm_judge",
                                "field": "state.reported_issue",
                                "question": "Does this sound like storm or weather damage requiring rapid response (e.g. wind damage, hail, leaks after a storm)?",
                            },
                        ],
                    },
                    "block_message": "Storm damage gets routed through our emergency line, not the regular schedule. I'll connect you to dispatch right now.",
                },
                applies_when_description="Roofing customer describes storm/weather damage.",
                applies_to_tools=["book_appointment"],
                priority=155,
                source_prompt="If reported issue is storm damage, route roofing to emergency dispatch",
            ),
            _r(
                "lead_time_minimum",
                "Roofing needs 7 days advance",
                "New roofing jobs need at least 7 days of scheduling lead time. Bypassed by is_emergency.",
                {
                    "minimum_hours": 168,
                    "applies_to_service_types": ["roofing"],
                    "bypass_if_state_field": "is_emergency",
                    "bypass_if_state_value": True,
                    "block_message": "Roofing jobs need a week of lead time so we can get the right crew. We can fast-track for emergencies.",
                },
                applies_to_tools=["book_appointment"],
                priority=140,
            ),
            _r(
                "conditional_block",
                "No 'cash deal' or unpermitted work",
                "If the reported issue mentions cash-only or unpermitted work, block — those need a manager.",
                {
                    "trigger": {
                        "op": "any_of",
                        "children": [
                            {"op": "matches_regex", "field": "state.reported_issue", "value": "(?i)\\bcash\\s+(deal|only)\\b"},
                            {"op": "matches_regex", "field": "state.reported_issue", "value": "(?i)\\bunpermitted\\b"},
                        ],
                    },
                    "block_message": "We can't book that here — let me get a manager to talk through the details with you.",
                },
                applies_to_tools=["book_appointment"],
                priority=145,
                source_prompt="Block jobs flagged as cash deal or unpermitted",
            ),
            _r(
                "output_constraint",
                "Mention free in-home consultations",
                "Promote the free in-home consultation when scheduling.",
                {
                    "instruction": "When the customer is undecided about scope, mention that we offer free in-home consultations to scope the project precisely.",
                    "severity": "guidance",
                },
                priority=80,
            ),
        ],
    }


# --------------------------------------------------------------------------- #
# Pipedreams — Bay Area plumbing / HVAC / drain. Pacific time. Different
# timezone exercises business_hours TZ math. Rule mix uses nested combinators
# (any_of inside not), llm_judge as an in-scope classifier, contains + numeric
# composite, and a "must"-severity output constraint.
# --------------------------------------------------------------------------- #


def _pipedreams() -> dict[str, Any]:
    return {
        "id": PIPEDREAMS_ID,
        "name": "Pipedreams",
        "timezone": "America/Los_Angeles",
        "description": "Plumbing, HVAC, drain cleaning — focused San Francisco coverage.",
        "rules": [
            _r(
                "business_hours",
                "Standard hours",
                "Mon–Fri 8 AM to 5 PM Pacific, closed weekends.",
                {
                    "timezone": "America/Los_Angeles",
                    "hours_by_day": {
                        d: {"start": "08:00", "end": "17:00"}
                        for d in ("mon", "tue", "wed", "thu", "fri")
                    },
                    "closed_days": ["sat", "sun"],
                    "block_message": "We're closed weekends — we'll respond first thing Monday.",
                },
                applies_to_tools=["book_appointment", "check_availability"],
                priority=200,
            ),
            _r(
                "service_area_zip",
                "San Francisco coverage",
                "Inner SF ZIPs only.",
                {
                    "allowed_zips": [
                        "94102","94103","94104","94105","94107","94108",
                        "94109","94110","94111","94114","94115","94117",
                    ],
                    "denied_zips": [],
                    "block_message": "We don't cover that ZIP — happy to recommend someone.",
                },
                applies_to_tools=["book_appointment", "lookup_service_area"],
                priority=180,
            ),
            _r(
                "services_offered",
                "What we do",
                "Plumbing, HVAC, drain cleaning.",
                {
                    "allowed_services": ["plumbing", "hvac", "drain_cleaning"],
                    "block_message": "That's outside what we cover.",
                },
                applies_to_tools=["book_appointment"],
                priority=160,
            ),
            _r(
                "lead_time_minimum",
                "Minimum 4-hour lead time",
                "Every booking needs at least 4 hours of advance notice. Bypassed by is_emergency.",
                {
                    "minimum_hours": 4,
                    "applies_to_service_types": None,
                    "bypass_if_state_field": "is_emergency",
                    "bypass_if_state_value": True,
                    "block_message": "We need at least 4 hours of lead time on regular jobs. Same-day works for emergencies — should I escalate?",
                },
                applies_to_tools=["book_appointment"],
                priority=140,
            ),
            _r(
                "conditional_block",
                "After-hours drain cleaning needs a member or emergency",
                "Drain cleaning outside business hours requires either an existing customer relationship or a real emergency.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "drain_cleaning"},
                            {"op": "eq", "field": "args.is_after_hours", "value": True},
                            {
                                "op": "not",
                                "child": {
                                    "op": "any_of",
                                    "children": [
                                        {"op": "eq", "field": "state.is_existing_customer", "value": True},
                                        {
                                            "op": "llm_judge",
                                            "field": "state.reported_issue",
                                            "question": "Does this sound like an active emergency (e.g. sewage backup, flooding) requiring same-night response?",
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                    "block_message": "After-hours drain calls are reserved for members or genuine emergencies. Want me to schedule first thing in the morning?",
                },
                applies_to_tools=["book_appointment"],
                priority=150,
                source_prompt="After-hours drain cleaning requires existing customer or emergency",
            ),
            _r(
                "conditional_block",
                "Estimate intent classifier",
                "If the reported issue doesn't actually describe a plumbing/HVAC/drain problem, we won't book — we'll route to general info instead.",
                {
                    "trigger": {
                        "op": "not",
                        "child": {
                            "op": "llm_judge",
                            "field": "state.reported_issue",
                            "question": "Does this clearly describe a plumbing, HVAC, or drain-cleaning problem (as opposed to e.g. an unrelated handyman task or a question about pricing)?",
                        },
                    },
                    "block_message": "I'm not sure that's something we cover — could you describe the plumbing or HVAC issue you're seeing?",
                },
                applies_when_description="Reported issue doesn't read as a real service request.",
                applies_to_tools=["book_appointment"],
                priority=130,
                source_prompt="Block bookings whose described issue isn't actually plumbing/HVAC/drain",
            ),
            _r(
                "conditional_block",
                "Re-quote stale estimates",
                "If the customer references an estimate older than 7 days, we re-quote before booking.",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "contains", "field": "state.reported_issue", "value": "estimate"},
                            {"op": "gt", "field": "args.estimate_age_days", "value": 7},
                        ],
                    },
                    "block_message": "That estimate is more than a week old — let's re-quote before booking.",
                },
                applies_to_tools=["book_appointment"],
                priority=145,
                source_prompt="Prioritize follow-up on estimates within 7 days",
            ),
            _r(
                "output_constraint",
                "Reference original estimate scope",
                "When following up on an estimate, anchor the conversation in the original estimate's scope.",
                {
                    "instruction": "When the customer references a prior estimate, restate the scope of the original estimate before discussing changes — so the customer knows what's being recapped.",
                    "severity": "must",
                },
                priority=80,
            ),
        ],
    }


# --------------------------------------------------------------------------- #
# Idempotent insert
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# 9 fictional cross-trade businesses (corpus-test contexts)
# --------------------------------------------------------------------------- #


def _std_hours_rule(timezone: str, weekdays_open: str, sat_open: str | None, sun_open: str | None,
                    *, block_msg: str = "We're closed then — try us next business day.") -> dict[str, Any]:
    """Helper: standard business_hours rule from a compact spec.

    weekdays_open / sat_open / sun_open are "HH:MM-HH:MM" or None for closed.
    """
    def _parse(spec: str | None) -> dict | None:
        if spec is None:
            return None
        a, b = spec.split("-")
        return {"start": a.strip(), "end": b.strip()}
    hours = {}
    if weekdays_open:
        rng = _parse(weekdays_open)
        for d in ("mon", "tue", "wed", "thu", "fri"):
            hours[d] = rng
    if sat_open:
        hours["sat"] = _parse(sat_open)
    if sun_open:
        hours["sun"] = _parse(sun_open)
    closed = [d for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun") if d not in hours]
    return _r(
        "business_hours",
        "Standard hours",
        "Standard operating hours.",
        {"timezone": timezone, "hours_by_day": hours, "closed_days": closed, "block_message": block_msg},
        applies_when_description="Customer wants to book or check availability.",
        applies_to_tools=["book_appointment", "check_availability"],
        priority=200,
    )


def _zip_rule(zips: list[str], block_msg: str, *, denied: list[str] | None = None) -> dict[str, Any]:
    return _r(
        "service_area_zip", "Service area",
        "ZIP allow-list defining the geographic service area.",
        {"allowed_zips": zips, "denied_zips": denied or [], "block_message": block_msg},
        applies_when_description="Customer requests work outside the service area.",
        applies_to_tools=["book_appointment", "lookup_service_area"],
        priority=180,
    )


def _services_rule(services: list[str], block_msg: str) -> dict[str, Any]:
    return _r(
        "services_offered", "Services we offer",
        "Allow-list of service types.",
        {"allowed_services": services, "block_message": block_msg},
        applies_to_tools=["book_appointment"], priority=160,
    )


def _lead_rule(name: str, hours: int, services: list[str] | None, block_msg: str) -> dict[str, Any]:
    return _r(
        "lead_time_minimum", name,
        f"Minimum {hours}-hour lead time" + (f" for {', '.join(services)}." if services else "."),
        {
            "minimum_hours": hours, "applies_to_service_types": services,
            "bypass_if_state_field": "is_emergency", "bypass_if_state_value": True,
            "block_message": block_msg,
        },
        applies_to_tools=["book_appointment"], priority=140,
    )


def _output_rule(name: str, instruction: str, severity: str = "guidance", priority: int = 80) -> dict[str, Any]:
    return _r(
        "output_constraint", name,
        instruction[:60] + "…" if len(instruction) > 60 else instruction,
        {"instruction": instruction, "severity": severity},
        priority=priority,
    )


def _cascade_plumbing() -> dict[str, Any]:
    """Cascade Plumbing & Drain — Seattle metro, plumbing only."""
    return {
        "id": CASCADE_ID, "name": "Cascade Plumbing & Drain",
        "timezone": "America/Los_Angeles",
        "description": "Plumbing-only operator — Seattle metro. Drain cleaning, water heaters, repipes.",
        "rules": [
            _std_hours_rule("America/Los_Angeles", "07:00-18:00", "08:00-15:00", None,
                            block_msg="We're closed weekends — voicemail picks up emergencies."),
            _zip_rule([
                "98101","98102","98103","98104","98105","98106","98107","98108","98109","98112",
                "98115","98116","98117","98118","98119","98121","98122","98125","98126","98133",
                "98144","98146","98148","98155","98166","98168","98177","98178","98199",
            ], "We don't cover that ZIP — try a Greater Seattle plumber."),
            _services_rule([
                "plumbing_repair", "plumbing_install", "drain_cleaning",
                "water_heater_repair", "water_heater_install", "repiping",
            ], "We're plumbing-only — try a different specialty."),
            _lead_rule("Repipe lead time", 72, ["repiping"],
                       "Repipes need 3 days of lead time."),
            _r("conditional_block", "Hydro jetting needs prior camera inspection",
               "Hydro-jet customers should have had a camera inspection first.",
               {"trigger": {"op": "all_of", "children": [
                   {"op": "eq", "field": "args.service_type", "value": "drain_cleaning"},
                   {"op": "contains", "field": "state.reported_issue", "value": "hydro"},
               ]},
                "block_message": "Hydro jetting works best after a camera inspection — let's start there."},
               applies_to_tools=["book_appointment"], priority=145,
               source_prompt="Hydro jetting requires a camera inspection first"),
        ],
    }


def _mountain_view_roofing() -> dict[str, Any]:
    """Mountain View Roofing — Denver metro, roofing/gutters."""
    return {
        "id": MOUNTAIN_VIEW_ID, "name": "Mountain View Roofing",
        "timezone": "America/Denver",
        "description": "Roofing and gutter specialist — Denver metro. Storm damage emergency channel.",
        "rules": [
            _std_hours_rule("America/Denver", "07:00-17:00", "09:00-14:00", None,
                            block_msg="We're closed — call back during business hours."),
            _zip_rule([
                "80014","80015","80016","80017","80018","80019","80020","80021","80022","80023",
                "80024","80027","80030","80031","80033","80034","80035","80201","80202","80203",
                "80204","80205","80206","80207","80208","80209","80210","80211","80212","80214",
                "80215","80216","80218","80219","80220","80221","80222","80223","80224","80226",
            ], "We don't cover that area — try a Front Range roofer."),
            _services_rule(["roof_repair","roof_replacement","gutter_install","gutter_repair"],
                           "We're roofing-only — try a multi-trade contractor."),
            _r("customer_eligibility", "Homeowner required for roof replacement",
               "Roof replacement requires the homeowner's authorization.",
               {"homeowner_required": True, "exclude_renters": True, "membership_required": False,
                "block_message": "Roof replacement requires the homeowner — could the owner call us?",
                "required_state_fields": ["is_homeowner"],
                "applies_to_service_types": ["roof_replacement"]},
               applies_when_description="Roof replacement bookings.",
               applies_to_tools=["book_appointment"], priority=170),
            _lead_rule("Roof replacement lead time", 168, ["roof_replacement"],
                       "Roof replacements need at least 1 week to order materials."),
            _r("conditional_block", "Storm damage routes to emergency",
               "Storm-damage roofing requests bypass the regular schedule.",
               {"trigger": {"op": "all_of", "children": [
                   {"op": "eq", "field": "args.service_type", "value": "roof_repair"},
                   {"op": "llm_judge", "field": "state.reported_issue",
                    "question": "Does this sound like storm or weather damage requiring rapid response?"},
               ]},
                "block_message": "Storm damage gets routed through our emergency line — connecting you now."},
               applies_to_tools=["book_appointment"], priority=155,
               source_prompt="Storm damage roofing routes to emergency"),
        ],
    }


def _atlantic_pool() -> dict[str, Any]:
    """Atlantic Pool & Spa — South FL, pools (seasonal)."""
    return {
        "id": ATLANTIC_POOL_ID, "name": "Atlantic Pool & Spa",
        "timezone": "America/New_York",
        "description": "Pools and hot tubs — South Florida. Pool installs are multi-week projects.",
        "rules": [
            _std_hours_rule("America/New_York", "08:00-17:00", "09:00-15:00", None,
                            block_msg="We're closed — back during business hours."),
            _zip_rule([
                "33101","33102","33109","33125","33126","33127","33128","33129","33130","33131",
                "33132","33133","33134","33135","33136","33137","33138","33139","33140","33141",
                "33142","33143","33144","33145","33146","33147","33149","33150","33154","33155",
            ], "We're South Florida only — try a regional pool company."),
            _services_rule(["pool_install","pool_maintenance","pool_repair","hot_tub_install",
                            "water_feature","pool_opening","pool_closing"],
                           "Pools and hot tubs only — try a different specialty."),
            _lead_rule("Pool install lead time", 336, ["pool_install"],
                       "Pool installs need 2 weeks of lead time minimum (permits + crew)."),
            _r("conditional_block", "Seasonal closure for pool services Nov–Mar",
               "Pool maintenance and opening services are seasonal (April-October).",
               {"trigger": {"op": "any_of", "children": [
                   {"op": "in", "field": "args.month", "value": [11, 12, 1, 2, 3]},
                   {"op": "contains", "field": "state.reported_issue", "value": "winter"},
               ]},
                "block_message": "Pool services pause November through March — we'll be back in April."},
               applies_to_tools=["book_appointment"], priority=150,
               source_prompt="Pool services are seasonal Nov-Mar"),
        ],
    }


def _bay_area_electric() -> dict[str, Any]:
    """Bay Area Electric — SF Bay, electrical/EV chargers."""
    return {
        "id": BAY_AREA_ID, "name": "Bay Area Electric",
        "timezone": "America/Los_Angeles",
        "description": "Electrical and EV charger specialist — SF Bay Area. Licensing-strict.",
        "rules": [
            _std_hours_rule("America/Los_Angeles", "08:00-17:00", "09:00-13:00", None,
                            block_msg="Licensed electricians — we're closed off-hours."),
            _zip_rule([
                "94102","94103","94104","94105","94107","94108","94109","94110","94111","94112",
                "94114","94115","94116","94117","94118","94121","94122","94123","94124","94127",
                "94131","94132","94133","94134","94158",
            ], "We cover San Francisco proper — for the Peninsula, try a regional electrician."),
            _services_rule(["electrical_repair","electrical_install","ev_charger_install",
                            "panel_upgrade","generator_install"],
                           "Electrical and EV charger work only."),
            _r("customer_eligibility", "Homeowner required for panel upgrades",
               "Panel upgrades require the homeowner's authorization.",
               {"homeowner_required": True, "exclude_renters": False, "membership_required": False,
                "block_message": "Panel upgrades need the homeowner — please have them call us.",
                "required_state_fields": ["is_homeowner"],
                "applies_to_service_types": ["panel_upgrade","ev_charger_install"]},
               applies_to_tools=["book_appointment"], priority=170),
            _lead_rule("Panel upgrade lead time", 72, ["panel_upgrade"],
                       "Panel upgrades need 3 days for permitting."),
        ],
    }


def _prairiefence() -> dict[str, Any]:
    """PrairieFence Co. — Twin Cities fencing, frozen-ground seasonality."""
    return {
        "id": PRAIRIEFENCE_ID, "name": "PrairieFence Co.",
        "timezone": "America/Chicago",
        "description": "Fence and gate installer — Twin Cities. Seasonal frozen-ground constraints.",
        "rules": [
            _std_hours_rule("America/Chicago", "07:00-18:00", "08:00-14:00", None,
                            block_msg="We're closed — try us during business hours."),
            _zip_rule([
                "55101","55102","55104","55105","55106","55107","55108","55109","55113","55116",
                "55117","55118","55401","55402","55403","55404","55405","55406","55407","55408",
                "55409","55410","55411","55412","55413","55414","55415","55416","55417","55418",
            ], "We cover the Twin Cities — try a regional fence company."),
            _services_rule(["fence_install","fence_repair","gate_install","gate_repair"],
                           "Fences and gates only."),
            _r("conditional_block", "Frozen ground — no installs Dec/Jan/Feb",
               "Fence installs are blocked December through February (frozen ground).",
               {"trigger": {"op": "all_of", "children": [
                   {"op": "eq", "field": "args.service_type", "value": "fence_install"},
                   {"op": "in", "field": "args.month", "value": [12, 1, 2]},
               ]},
                "block_message": "We can't install in frozen ground — we'll book you for spring (March on)."},
               applies_to_tools=["book_appointment"], priority=150,
               source_prompt="No fence installs December through February (frozen ground)"),
            _lead_rule("Cedar fence lead time", 504, ["fence_install"],
                       "Cedar fence installs need 3 weeks for material delivery."),
        ],
    }


def _gardenworks() -> dict[str, Any]:
    """GardenWorks Irrigation — Phoenix, water-restriction state."""
    return {
        "id": GARDENWORKS_ID, "name": "GardenWorks Irrigation",
        "timezone": "America/Phoenix",
        "description": "Irrigation and drip systems — Phoenix metro. Drought-restriction-aware.",
        "rules": [
            _std_hours_rule("America/Phoenix", "06:00-15:00", "07:00-12:00", None,
                            block_msg="We're closed — early starts to beat the heat."),
            _zip_rule([
                "85001","85003","85004","85006","85007","85008","85009","85013","85014","85015",
                "85016","85017","85018","85019","85020","85021","85022","85023","85024","85027",
                "85028","85029","85031","85032","85033","85034","85035","85037","85040","85041",
            ], "We cover Phoenix metro — try a regional irrigation company."),
            _services_rule(["irrigation_install","irrigation_repair","drip_install","sprinkler_repair"],
                           "Irrigation only."),
            _r("output_constraint", "Mention water-restriction tier",
               "Phoenix has tiered watering rules — mention them when relevant.",
               {"instruction": "When discussing scheduling or system design, mention the local water-restriction tier (Stage 1/2/3) and how the install will respect it.",
                "severity": "guidance"},
               priority=80),
        ],
    }


def _doormaster() -> dict[str, Any]:
    """DoorMaster Garage — DFW, garage doors."""
    return {
        "id": DOORMASTER_ID, "name": "DoorMaster Garage",
        "timezone": "America/Chicago",
        "description": "Garage doors — Dallas-Fort Worth. Quick-service skewed.",
        "rules": [
            _std_hours_rule("America/Chicago", "07:00-19:00", "08:00-17:00", "09:00-15:00",
                            block_msg="We're closed — back at our next opening."),
            _zip_rule([
                "75201","75202","75203","75204","75205","75206","75207","75208","75209","75210",
                "75211","75212","75214","75215","75216","75217","75218","75219","75220","75223",
                "75224","75225","75226","75227","75228","75229","75230","75231","75232","75233",
            ], "We cover DFW — try a regional garage-door installer."),
            _services_rule(["garage_door_install","garage_door_repair",
                            "garage_door_opener_install","garage_door_opener_repair"],
                           "Garage doors only."),
            _output_rule("24-hour repair guarantee", "Mention our 24-hour repair guarantee on repair calls.", priority=80),
        ],
    }


def _pure_air() -> dict[str, Any]:
    """Pure Air IAQ — Nashville, indoor air specialty."""
    return {
        "id": PURE_AIR_ID, "name": "Pure Air IAQ",
        "timezone": "America/Chicago",
        "description": "Indoor air quality specialist — Nashville. Duct cleaning, air purifiers, allergen testing.",
        "rules": [
            _std_hours_rule("America/Chicago", "08:00-17:00", "09:00-13:00", None,
                            block_msg="We're closed — call back during business hours."),
            _zip_rule([
                "37201","37203","37204","37205","37206","37207","37208","37209","37210","37211",
                "37212","37213","37214","37215","37216","37217","37218","37219","37220","37221",
            ], "We cover Nashville metro — try a regional IAQ specialist."),
            _services_rule(["duct_cleaning","air_purifier_install","allergen_test","mold_inspection",
                            "humidity_control"],
                           "Indoor air quality work only."),
            _r("output_constraint", "Mention allergy-season urgency",
               "When the customer mentions allergies or seasonal symptoms, prioritize duct cleaning + allergen testing.",
               {"instruction": "If the customer mentions allergies, asthma, congestion, or seasonal symptoms, recommend a duct cleaning + allergen test combo and explain why timing matters.",
                "severity": "must"},
               priority=70),
        ],
    }


def _sunset_bath() -> dict[str, Any]:
    """Sunset Bath Remodel — SoCal, bath remodel high-ticket."""
    return {
        "id": SUNSET_BATH_ID, "name": "Sunset Bath Remodel",
        "timezone": "America/Los_Angeles",
        "description": "Bathroom remodel specialist — Southern California. Multi-week project lead times.",
        "rules": [
            _std_hours_rule("America/Los_Angeles", "08:00-18:00", "09:00-15:00", None,
                            block_msg="We're closed — call back during business hours."),
            _zip_rule([
                "90001","90002","90003","90004","90005","90006","90007","90008","90010","90011",
                "90012","90013","90014","90015","90016","90017","90018","90019","90020","90021",
                "92602","92603","92604","92606","92610","92612","92614","92618","92620","92625",
                "91361","91362","91364","91367","91387","92595","92596","92670","92672","92673",
            ], "We cover SoCal — try a regional remodel firm."),
            _services_rule(["bathroom_remodel","tub_to_shower","bathtub_install",
                            "shower_install","accessibility_install"],
                           "Bath remodels only."),
            _r("customer_eligibility", "Homeowner required for remodels",
               "Bath remodels require the homeowner's authorization.",
               {"homeowner_required": True, "exclude_renters": True, "membership_required": False,
                "block_message": "Bath remodels require the homeowner — please have them call us.",
                "required_state_fields": ["is_homeowner"],
                "applies_to_service_types": ["bathroom_remodel","tub_to_shower"]},
               applies_to_tools=["book_appointment"], priority=170),
            _lead_rule("Bath remodel lead time", 504, ["bathroom_remodel"],
                       "Bath remodels need 3 weeks of lead time minimum."),
            _output_rule("Mention free in-home consultation",
                         "When customers are scoping a remodel, mention our free in-home consultation.",
                         priority=80),
        ],
    }


def _ensure_business(db: Session, payload: dict[str, Any]) -> Business:
    biz = db.get(Business, payload["id"])
    if biz is None:
        biz = Business(
            id=payload["id"],
            name=payload["name"],
            timezone=payload["timezone"],
            description=payload["description"],
        )
        db.add(biz)
        db.flush()
    else:
        biz.name = payload["name"]
        biz.timezone = payload["timezone"]
        biz.description = payload["description"]
    return biz


def _ensure_rule(db: Session, business_id: UUID, payload: dict[str, Any]) -> None:
    existing = db.execute(
        select(Rule).where(Rule.business_id == business_id, Rule.name == payload["name"])
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(
        Rule(
            business_id=business_id,
            rule_type=payload["rule_type"],
            name=payload["name"],
            description=payload["description"],
            applies_when_description=payload.get("applies_when_description", ""),
            parameters=payload["parameters"],
            applies_to_tools=payload.get("applies_to_tools", []),
            enforcement_mode=payload.get("enforcement_mode", "block"),
            priority=payload.get("priority", 100),
            is_active=payload.get("is_active", True),
            source_prompt=payload.get("source_prompt"),
        )
    )


def all_payloads() -> list[dict[str, Any]]:
    return [
        _del_air(), _improveit(), _pipedreams(),
        _cascade_plumbing(), _mountain_view_roofing(), _atlantic_pool(),
        _bay_area_electric(), _prairiefence(), _gardenworks(),
        _doormaster(), _pure_air(), _sunset_bath(),
    ]


def run_if_empty() -> None:
    """If no businesses exist yet, insert the three case studies.

    The demo-conversations seed is gated separately on the conversations
    table being empty, so we always call it — fresh deploys get demo
    activity, and deploys that already have conversations are no-ops.
    """
    with session_scope() as db:
        any_business = db.execute(select(Business.id).limit(1)).scalar_one_or_none()
        if any_business is None:
            for payload in all_payloads():
                biz = _ensure_business(db, payload)
                for rule in payload["rules"]:
                    _ensure_rule(db, biz.id, rule)
            log.info("seed: inserted 3 businesses with rule sets")
        else:
            log.info("seed: businesses already present, skipping rule seed")
    seed_demo_conversations_if_empty()


def seed_demo_conversations_if_empty() -> None:
    """Populate the activity feed with 5 representative conversations.

    Only runs when the conversations table is empty (i.e. fresh deploy).
    Each conversation is built by routing realistic args through the live
    `RuleEngine`, then writing audit rows that mirror the shape
    `_check_and_audit` produces in production — so the demo data on
    /activity is structurally indistinguishable from a real chat. The
    assistant text is hand-written deterministic copy (no LLM call needed).
    """
    with session_scope() as db:
        any_conv = db.execute(select(Conversation.id).limit(1)).scalar_one_or_none()
        if any_conv is not None:
            log.info("seed: conversations already present, skipping demo seed")
            return

        from app.engine.engine import RuleEngine

        # Build a quick lookup of rules per business so each demo can pick
        # the right engine without re-querying.
        businesses = db.execute(select(Business)).scalars().all()
        rules_by_biz: dict[UUID, list[Rule]] = {b.id: [] for b in businesses}
        for r in db.execute(select(Rule).where(Rule.is_active.is_(True))).scalars():
            rules_by_biz.setdefault(r.business_id, []).append(r)
        biz_by_id = {b.id: b for b in businesses}

        sunrise_id = DEL_AIR_ID  # renamed in this codebase but the UUID is stable
        atlantic_id = ATLANTIC_POOL_ID

        # Reference time for the demos. Picked so demo "Tuesday 10 AM"
        # is in the future relative to the seeded current_time.
        ref = datetime(2026, 6, 15, 14, 0)  # Mon Jun 15 2 PM

        if sunrise_id in biz_by_id:
            _seed_demo_clean_accept(db, biz_by_id[sunrise_id], rules_by_biz[sunrise_id], ref)
            _seed_demo_block_hours(db, biz_by_id[sunrise_id], rules_by_biz[sunrise_id], ref)
            _seed_demo_block_zip(db, biz_by_id[sunrise_id], rules_by_biz[sunrise_id], ref)
            _seed_demo_needs_info(db, biz_by_id[sunrise_id], rules_by_biz[sunrise_id], ref)
        if atlantic_id in biz_by_id:
            _seed_demo_service_not_offered(
                db, biz_by_id[atlantic_id], rules_by_biz[atlantic_id], ref
            )

        log.info("seed: inserted demo conversations across activity")


def _engine_for(rules: list[Rule]):
    """Build a RuleEngine from active ORM rules — same shape the agent uses."""
    from app.engine.engine import RuleEngine

    return RuleEngine.for_business(rules, judge=None)


def _new_conv(
    db: Session,
    business: Business,
    customer: str,
    state: dict[str, Any] | None = None,
) -> Conversation:
    conv = Conversation(
        business_id=business.id,
        customer_identifier=customer,
        state=state or {},
        message_count=0,
        had_accepted_action=False,
        had_blocked_action=False,
        blocked_rule_ids=[],
        is_test=False,
        system_prompt_snapshot="(demo seed — system prompt not captured)",
    )
    db.add(conv)
    db.flush()
    return conv


def _msg(db: Session, conv: Conversation, role: str, content: str) -> None:
    db.add(Message(conversation_id=conv.id, role=role, content=content))
    conv.message_count += 1


def _audit_for_check(
    db: Session,
    conv: Conversation,
    business: Business,
    rules: list[Rule],
    tool_name: str,
    args: dict[str, Any],
    state: dict[str, Any],
    current_time: datetime,
    *,
    user_facing_block: str | None = None,
) -> str:
    """Run the rule engine for these args + write audit rows in the same
    shape `_check_and_audit` produces. Returns the engine outcome
    ('accepted' / 'blocked' / 'needs_info') so the caller can decide what
    the assistant says next.
    """
    from app.engine.engine import RuleEngine
    from app.schemas.conversation_state import ConversationState

    engine = _engine_for(rules)
    state_obj = ConversationState.model_validate(state)
    result = engine.check(tool_name, args, business, state_obj, current_time)

    if result.fired_rules:
        for fired in result.fired_rules:
            db.add(
                AuditLog(
                    business_id=business.id,
                    conversation_id=conv.id,
                    customer_identifier=conv.customer_identifier,
                    event_type="tool_call",
                    outcome="blocked" if fired.outcome == "block" else fired.outcome,
                    tool_name=tool_name,
                    fired_rule_id=fired.rule_id,
                    fired_rule_type=fired.rule_type,
                    fired_rule_name=fired.rule_name,
                    tool_args=args,
                    user_facing_message=fired.user_facing_message,
                    internal_reason=fired.internal_reason,
                    required_fields=fired.required_fields or None,
                )
            )
            if fired.outcome == "block":
                conv.had_blocked_action = True
                conv.blocked_rule_ids = list(set(conv.blocked_rule_ids) | {fired.rule_id})
    else:
        # rule_considered rows precede the headline tool_call row
        for rule in rules:
            if rule.rule_type == "output_constraint":
                continue
            applies = not rule.applies_to_tools or tool_name in rule.applies_to_tools
            if not applies:
                continue
            db.add(
                AuditLog(
                    business_id=business.id,
                    conversation_id=conv.id,
                    customer_identifier=conv.customer_identifier,
                    event_type="rule_considered",
                    outcome="passed",
                    tool_name=tool_name,
                    fired_rule_id=rule.id,
                    fired_rule_type=rule.rule_type,
                    fired_rule_name=rule.name,
                    tool_args=args,
                )
            )
        db.add(
            AuditLog(
                business_id=business.id,
                conversation_id=conv.id,
                customer_identifier=conv.customer_identifier,
                event_type="tool_call",
                outcome=result.outcome,
                tool_name=tool_name,
                tool_args=args,
            )
        )
        if result.outcome == "accepted":
            conv.had_accepted_action = True

    return result.outcome


def _audit_state_update(
    db: Session, conv: Conversation, business: Business, field: str, value: Any
) -> None:
    db.add(
        AuditLog(
            business_id=business.id,
            conversation_id=conv.id,
            customer_identifier=conv.customer_identifier,
            event_type="state_update",
            outcome="info",
            tool_name="update_conversation_state",
            tool_args={"field": field, "value": value},
        )
    )


def _seed_demo_clean_accept(
    db: Session, business: Business, rules: list[Rule], ref: datetime
) -> None:
    """A booking that flows through cleanly — rule_considered rows + accept."""
    conv = _new_conv(db, business, "Demo · Clean accept #c1a2")
    _msg(db, conv, "user", "Hi, can I book HVAC service Tuesday at 10 AM, ZIP 32801? I'm the homeowner.")
    state = {"address_zip": "32801", "is_homeowner": True}
    conv.state = state
    _audit_state_update(db, conv, business, "address_zip", "32801")
    _audit_state_update(db, conv, business, "is_homeowner", True)
    _audit_for_check(
        db, conv, business, rules,
        "book_appointment",
        {"date": "2026-06-16", "time": "10:00", "service_type": "hvac", "address_zip": "32801"},
        state,
        ref,
    )
    _msg(db, conv, "assistant", "Got it — booked for Tuesday, June 16 at 10 AM. We'll see you then.")


def _seed_demo_block_hours(
    db: Session, business: Business, rules: list[Rule], ref: datetime
) -> None:
    """A booking blocked by Standard hours (Sunday request)."""
    conv = _new_conv(db, business, "Demo · Sunday block #s2b9")
    _msg(db, conv, "user", "Can someone come out this Sunday morning to fix my AC?")
    _audit_for_check(
        db, conv, business, rules,
        "book_appointment",
        {"date": "2026-06-21", "time": "10:00", "service_type": "hvac"},
        {},
        ref,
    )
    _msg(db, conv, "assistant", "We're closed Sundays — let me know a weekday that works and I'll get you booked.")


def _seed_demo_block_zip(
    db: Session, business: Business, rules: list[Rule], ref: datetime
) -> None:
    """A booking blocked by Service area (out-of-area ZIP)."""
    conv = _new_conv(db, business, "Demo · Out-of-area #z4f1")
    _msg(db, conv, "user", "HVAC tune-up Tuesday at 10 AM, ZIP 99999.")
    state = {"address_zip": "99999"}
    conv.state = state
    _audit_state_update(db, conv, business, "address_zip", "99999")
    _audit_for_check(
        db, conv, business, rules,
        "book_appointment",
        {"date": "2026-06-16", "time": "10:00", "service_type": "hvac", "address_zip": "99999"},
        state,
        ref,
    )
    _msg(db, conv, "assistant", "We don't service ZIP 99999 — try a regional HVAC company in your area.")


def _seed_demo_needs_info(
    db: Session, business: Business, rules: list[Rule], ref: datetime
) -> None:
    """A booking that surfaces needs_info, then accepts after state update."""
    conv = _new_conv(db, business, "Demo · State gather #ng3k")
    _msg(db, conv, "user", "HVAC Tuesday 10 AM, ZIP 32801.")
    state = {"address_zip": "32801"}
    conv.state = state
    _audit_state_update(db, conv, business, "address_zip", "32801")
    # First booking attempt — needs_info on is_homeowner
    args = {"date": "2026-06-16", "time": "10:00", "service_type": "hvac", "address_zip": "32801"}
    _audit_for_check(db, conv, business, rules, "book_appointment", args, state, ref)
    _msg(db, conv, "assistant", "Quick check — are you the homeowner at this address?")
    _msg(db, conv, "user", "Yes, I own.")
    state["is_homeowner"] = True
    conv.state = dict(state)
    _audit_state_update(db, conv, business, "is_homeowner", True)
    _audit_for_check(db, conv, business, rules, "book_appointment", args, state, ref)
    _msg(db, conv, "assistant", "Perfect — booked for Tuesday, June 16 at 10 AM.")


def _seed_demo_service_not_offered(
    db: Session, business: Business, rules: list[Rule], ref: datetime
) -> None:
    """The exact failure-mode case from the deploy bug: customer asks for
    a service the business doesn't offer; the agent calls the tool, the
    engine blocks, the audit captures it."""
    conv = _new_conv(db, business, "Demo · Out-of-vocab service #pl5m")
    _msg(db, conv, "user", "Can I book a plumbing appointment for Tuesday?")
    _audit_for_check(
        db, conv, business, rules,
        "book_appointment",
        {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        {},
        ref,
    )
    _msg(db, conv, "assistant", "We don't offer plumbing — only pools and hot tubs. Want me to suggest a referral?")


def force_reseed() -> None:
    """Add any missing rules without removing existing ones (legacy helper)."""
    with session_scope() as db:
        for payload in all_payloads():
            biz = _ensure_business(db, payload)
            for rule in payload["rules"]:
                _ensure_rule(db, biz.id, rule)


def wipe_rules_and_reseed() -> dict[str, int]:
    """Delete every rule (and its test cases via cascade) for the seeded
    businesses, then reinsert the canonical rule sets. Conversations,
    messages, and audit log are untouched.
    """
    counts = {"deleted_test_cases": 0, "deleted_rules": 0, "inserted_rules": 0}
    with session_scope() as db:
        for payload in all_payloads():
            biz = _ensure_business(db, payload)
            rule_ids = [
                r.id
                for r in db.execute(
                    select(Rule).where(Rule.business_id == biz.id)
                ).scalars().all()
            ]
            if rule_ids:
                counts["deleted_test_cases"] += db.execute(
                    delete(TestCase).where(TestCase.rule_id.in_(rule_ids))
                ).rowcount
                counts["deleted_rules"] += db.execute(
                    delete(Rule).where(Rule.id.in_(rule_ids))
                ).rowcount
            for rule in payload["rules"]:
                _ensure_rule(db, biz.id, rule)
                counts["inserted_rules"] += 1
        db.flush()
    log.info(f"seed: wipe+reseed counts={counts}")
    return counts


def wipe_all_and_reseed() -> dict[str, int]:
    """Hard reset for the corpus runner — wipes EVERYTHING then reseeds.

    Used by `POST /api/admin/wipe-all-and-reseed` so the runner can start
    every test run from a deterministic 12-business state. Conversations,
    messages, and audit log get cleared too (use `wipe_rules_and_reseed()`
    if you want to preserve audit history).
    """
    from app.models import AuditLog, Conversation, Message  # local import to avoid cycles
    counts = {
        "deleted_messages": 0, "deleted_audit": 0, "deleted_conversations": 0,
        "deleted_test_cases": 0, "deleted_rules": 0, "deleted_businesses": 0,
        "inserted_businesses": 0, "inserted_rules": 0,
    }
    with session_scope() as db:
        counts["deleted_messages"] = db.execute(delete(Message)).rowcount
        counts["deleted_audit"] = db.execute(delete(AuditLog)).rowcount
        counts["deleted_conversations"] = db.execute(delete(Conversation)).rowcount
        counts["deleted_test_cases"] = db.execute(delete(TestCase)).rowcount
        counts["deleted_rules"] = db.execute(delete(Rule)).rowcount
        counts["deleted_businesses"] = db.execute(delete(Business)).rowcount
        for payload in all_payloads():
            biz = _ensure_business(db, payload)
            counts["inserted_businesses"] += 1
            for rule in payload["rules"]:
                _ensure_rule(db, biz.id, rule)
                counts["inserted_rules"] += 1
        db.flush()
    log.info(f"seed: wipe-ALL+reseed counts={counts}")
    return counts
