"""Synthetic business + rule fixtures for engine-only eval cases.

Each fixture function returns a list[RuleSnapshot] ready to install on a
RuleEngine. These are deliberately simpler than the production seed —
focused on exercising one rule pattern at a time.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.engine.engine import RuleSnapshot


def _snap(
    rule_type: str,
    parameters: dict[str, Any],
    *,
    name: str = "rule",
    priority: int = 100,
    applies_to_tools: list[str] | None = None,
) -> RuleSnapshot:
    return RuleSnapshot(
        id=uuid4(),
        rule_type=rule_type,
        name=name,
        parameters=parameters,
        applies_to_tools=applies_to_tools or [],
        priority=priority,
    )


# --------------------------------------------------------------------------- #
# Family A — pure typed rule fixtures
# --------------------------------------------------------------------------- #


def hours_mon_fri(*, name: str = "Standard hours", priority: int = 200) -> RuleSnapshot:
    return _snap(
        "business_hours",
        {
            "timezone": "America/New_York",
            "hours_by_day": {
                "mon": {"start": "08:00", "end": "18:00"},
                "tue": {"start": "08:00", "end": "18:00"},
                "wed": {"start": "08:00", "end": "18:00"},
                "thu": {"start": "08:00", "end": "18:00"},
                "fri": {"start": "08:00", "end": "18:00"},
            },
            "closed_days": ["sat", "sun"],
            "block_message": "We're closed then.",
        },
        name=name,
        priority=priority,
    )


def zip_allow_deny(*, name: str = "Service area") -> RuleSnapshot:
    return _snap(
        "service_area_zip",
        {
            "allowed_zips": ["32801", "32802", "32803"],
            "denied_zips": ["32804"],
            "block_message": "That ZIP is outside our service area.",
        },
        name=name,
        priority=180,
    )


def services_hvac_plumbing(*, name: str = "Allowed trades") -> RuleSnapshot:
    return _snap(
        "services_offered",
        {
            "allowed_services": ["hvac", "plumbing"],
            "block_message": "We don't offer that service.",
        },
        name=name,
        priority=170,
    )


def homeowner_required(*, name: str = "Homeowner required") -> RuleSnapshot:
    return _snap(
        "customer_eligibility",
        {
            "homeowner_required": True,
            "exclude_renters": True,
            "membership_required": False,
            "block_message": "We only book with the homeowner.",
            "required_state_fields": ["is_homeowner"],
        },
        name=name,
        priority=160,
    )


def lead_time_48h_emergency_bypass(*, name: str = "48h lead time") -> RuleSnapshot:
    return _snap(
        "lead_time_minimum",
        {
            "minimum_hours": 48,
            "applies_to_service_types": ["hvac"],
            "bypass_if_state_field": "is_emergency",
            "bypass_if_state_value": True,
            "block_message": "We need 48 hours' notice unless it's an emergency.",
        },
        name=name,
        priority=140,
    )


# --------------------------------------------------------------------------- #
# Family B — group-scoped triggers (conditional_block patterns)
# --------------------------------------------------------------------------- #


def no_plumbing_after_4pm(*, name: str = "Late plumbing block") -> RuleSnapshot:
    return _snap(
        "conditional_block",
        {
            "trigger": {
                "op": "all_of",
                "children": [
                    {"op": "eq", "field": "args.service_type", "value": "plumbing"},
                    {"op": "gte", "field": "args.time", "value": "16:00"},
                ],
            },
            "block_message": "We don't dispatch plumbing after 4 PM.",
        },
        name=name,
        priority=150,
    )


def pre_1978_block(*, name: str = "Pre-1978 home block") -> RuleSnapshot:
    return _snap(
        "conditional_block",
        {
            "trigger": {
                "op": "lt",
                "field": "state.property_year_built",
                "value": 1978,
            },
            "block_message": "Pre-1978 homes need lead-safe-certified handling.",
        },
        name=name,
        priority=150,
    )


# --------------------------------------------------------------------------- #
# Family C — preconditioned rules
# --------------------------------------------------------------------------- #


def hoa_approval_required(*, name: str = "HOA approval gate") -> RuleSnapshot:
    """HOA bookings require homeowner confirmation.

    `required_precondition` here is the *gate that activates the rule*:
    if the property isn't HOA-governed, the rule short-circuits to pass.
    The `trigger` then blocks when is_homeowner isn't affirmatively true.
    Demonstrates the documented engine semantics in `app/engine/conditional.py`:
    `required_precondition` filters which calls the rule applies to;
    `trigger` decides block vs pass within those calls.
    """
    return _snap(
        "conditional_block",
        {
            "required_precondition": {
                "op": "eq",
                "field": "state.hoa_governed",
                "value": True,
            },
            "trigger": {
                "op": "neq",
                "field": "state.is_homeowner",
                "value": True,
            },
            "block_message": "HOA-governed bookings need the homeowner directly.",
        },
        name=name,
        priority=150,
    )
