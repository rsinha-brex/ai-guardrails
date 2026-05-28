"""Per-rule evaluators for the five typed rules.

Each function takes a rule's parameters dict (already validated server-side via
the Pydantic schemas), the tool args, the conversation state (any object with
matching attrs or dict), and the current_time, and returns a RuleOutcome.

Returning needs_info trumps blocking — the engine aggregates accordingly.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.schemas.conversation_state import STATE_FIELDS
from app.schemas.rules import (
    BusinessHoursParameters,
    CustomerEligibilityParameters,
    LeadTimeParameters,
    OutcomeBlock,
    OutcomeNeedsInfo,
    OutcomePass,
    RuleOutcome,
    ServiceAreaZipParameters,
    ServicesOfferedParameters,
    Weekday,
)

_WEEKDAY_FROM_INT = {
    0: Weekday.MON,
    1: Weekday.TUE,
    2: Weekday.WED,
    3: Weekday.THU,
    4: Weekday.FRI,
    5: Weekday.SAT,
    6: Weekday.SUN,
}


def _state_get(state: Any, name: str) -> Any:
    if state is None:
        return None
    if isinstance(state, dict):
        return state.get(name)
    return getattr(state, name, None)


# --------------------------------------------------------------------------- #
# business_hours
# --------------------------------------------------------------------------- #


def evaluate_business_hours(
    params: BusinessHoursParameters,
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    """Block when the proposed appointment moment falls outside open hours.

    Always evaluates against `args.date` (+ optional `args.time`) — that's the
    moment the customer is asking about. We never silently fall back to "right
    now" because nobody's dispatching a tech this instant. If `args.date` is
    somehow missing (the tool signatures require it, but we belt-and-suspender
    here), surface needs_info so the agent asks the customer for a date.
    """
    tz = ZoneInfo(params.timezone)
    when_local = _resolve_when_local(args, tz)
    if when_local is None:
        return OutcomeNeedsInfo(
            required_fields=["date"],
            user_facing_message="What date were you thinking?",
        )
    weekday = _WEEKDAY_FROM_INT[when_local.weekday()]

    if weekday in params.closed_days:
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason=f"Closed on {weekday.value}",
        )

    range_today = params.hours_by_day.get(weekday)
    if range_today is None:
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason=f"No hours configured for {weekday.value}",
        )

    open_t = time.fromisoformat(range_today.start)
    close_t = time.fromisoformat(range_today.end)
    target_t = when_local.time()

    if open_t <= target_t < close_t:
        return OutcomePass()

    return OutcomeBlock(
        block_message=params.block_message,
        internal_reason=f"Outside hours {range_today.start}-{range_today.end} on {weekday.value}",
    )


def _resolve_when_local(args: dict[str, Any], tz: ZoneInfo) -> datetime | None:
    """Parse args.date (+ optional args.time) into a tz-aware datetime.

    Returns None if no usable date is provided — the caller decides what that
    means (typically: needs_info on `date`).
    """
    date_arg = args.get("date") if args else None
    if not date_arg:
        return None
    time_arg = args.get("time") if args else None
    try:
        target = datetime.fromisoformat(
            f"{date_arg}T{time_arg}" if time_arg else str(date_arg)
        )
    except (ValueError, TypeError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=tz)
    return target.astimezone(tz)


def required_state_fields_business_hours(_: BusinessHoursParameters) -> list[str]:
    return []


# --------------------------------------------------------------------------- #
# service_area_zip
# --------------------------------------------------------------------------- #


def evaluate_service_area_zip(
    params: ServiceAreaZipParameters,
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    zip_code = args.get("address_zip") or _state_get(state, "address_zip")
    if zip_code is None:
        return OutcomeNeedsInfo(
            required_fields=["address_zip"],
            user_facing_message="What ZIP code is the work at?",
        )
    if zip_code in (params.denied_zips or []):
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason=f"ZIP {zip_code} explicitly denied",
        )
    if zip_code in params.allowed_zips:
        return OutcomePass()
    return OutcomeBlock(
        block_message=params.block_message,
        internal_reason=f"ZIP {zip_code} not in allowed list",
    )


def required_state_fields_service_area_zip(_: ServiceAreaZipParameters) -> list[str]:
    return ["address_zip"]


# --------------------------------------------------------------------------- #
# services_offered
# --------------------------------------------------------------------------- #


def evaluate_services_offered(
    params: ServicesOfferedParameters,
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    service = args.get("service_type")
    if service is None:
        return OutcomeNeedsInfo(
            required_fields=["service_type"],
            user_facing_message="What kind of work is this for?",
        )
    allowed = set(params.allowed_services)
    if service in allowed:
        return OutcomePass()
    return OutcomeBlock(
        block_message=params.block_message,
        internal_reason=f"Service {service} not in allowed list",
    )


def required_state_fields_services_offered(_: ServicesOfferedParameters) -> list[str]:
    return []


# --------------------------------------------------------------------------- #
# customer_eligibility
# --------------------------------------------------------------------------- #


def evaluate_customer_eligibility(
    params: CustomerEligibilityParameters,
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    # Service-type filter: short-circuit if the rule scopes to specific
    # service types and the current request isn't one of them. Mirrors the
    # lead_time_minimum pattern.
    if params.applies_to_service_types is not None:
        allowed_types = set(params.applies_to_service_types)
        service = args.get("service_type")
        if service not in allowed_types:
            return OutcomePass()

    missing: list[str] = []
    for f in params.required_state_fields:
        if _state_get(state, f.value) is None:
            missing.append(f.value)
    if missing:
        return OutcomeNeedsInfo(
            required_fields=missing,
            user_facing_message=f"I need to confirm: {', '.join(missing)}.",
        )

    if params.homeowner_required and _state_get(state, "is_homeowner") is False:
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason="Customer is not a homeowner",
        )
    if params.exclude_renters and _state_get(state, "is_homeowner") is False:
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason="Renters are not eligible",
        )
    if params.membership_required and _state_get(state, "is_existing_customer") is False:
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason="Membership required",
        )
    return OutcomePass()


def required_state_fields_customer_eligibility(p: CustomerEligibilityParameters) -> list[str]:
    return [f.value for f in p.required_state_fields]


# --------------------------------------------------------------------------- #
# lead_time_minimum
# --------------------------------------------------------------------------- #


def evaluate_lead_time(
    params: LeadTimeParameters,
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    # Bypass via state field
    if params.bypass_if_state_field is not None:
        if _state_get(state, params.bypass_if_state_field.value) == params.bypass_if_state_value:
            return OutcomePass()

    # Service-type filter
    if params.applies_to_service_types is not None:
        allowed_types = set(params.applies_to_service_types)
        service = args.get("service_type")
        if service not in allowed_types:
            return OutcomePass()

    # Compute lead time vs args.date/time
    date_val = args.get("date")
    time_val = args.get("time")
    if date_val is None:
        return OutcomePass()  # nothing to compare against — let other rules handle it
    try:
        if time_val:
            target = datetime.fromisoformat(f"{date_val}T{time_val}")
        else:
            target = datetime.fromisoformat(str(date_val))
    except ValueError:
        return OutcomePass()
    if current_time.tzinfo and target.tzinfo is None:
        target = target.replace(tzinfo=current_time.tzinfo)
    delta = target - current_time
    if delta < timedelta(hours=params.minimum_hours):
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason=f"{delta.total_seconds()/3600:.1f}h < {params.minimum_hours}h required",
        )
    return OutcomePass()


def required_state_fields_lead_time(p: LeadTimeParameters) -> list[str]:
    if p.bypass_if_state_field is not None:
        return [p.bypass_if_state_field.value]
    return []


# --------------------------------------------------------------------------- #
# Convenience dispatcher
# --------------------------------------------------------------------------- #


_DISPATCH = {
    "business_hours": (
        BusinessHoursParameters,
        evaluate_business_hours,
        required_state_fields_business_hours,
    ),
    "service_area_zip": (
        ServiceAreaZipParameters,
        evaluate_service_area_zip,
        required_state_fields_service_area_zip,
    ),
    "services_offered": (
        ServicesOfferedParameters,
        evaluate_services_offered,
        required_state_fields_services_offered,
    ),
    "customer_eligibility": (
        CustomerEligibilityParameters,
        evaluate_customer_eligibility,
        required_state_fields_customer_eligibility,
    ),
    "lead_time_minimum": (
        LeadTimeParameters,
        evaluate_lead_time,
        required_state_fields_lead_time,
    ),
}


def has_typed_evaluator(rule_type: str) -> bool:
    return rule_type in _DISPATCH


def evaluate_typed(
    rule_type: str,
    raw_parameters: dict[str, Any],
    args: dict[str, Any],
    state: Any,
    current_time: datetime,
) -> RuleOutcome:
    model_cls, fn, _ = _DISPATCH[rule_type]
    parsed = model_cls.model_validate(raw_parameters)
    return fn(parsed, args, state, current_time)


def required_state_fields_for(rule_type: str, raw_parameters: dict[str, Any]) -> list[str]:
    if rule_type not in _DISPATCH:
        return []
    model_cls, _, fields_fn = _DISPATCH[rule_type]
    parsed = model_cls.model_validate(raw_parameters)
    out = fields_fn(parsed)
    return [f for f in out if f in STATE_FIELDS]
