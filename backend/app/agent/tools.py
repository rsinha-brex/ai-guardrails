"""Pydantic AI tools — 5 action + 3 introspection.

Every tool runs through the rule engine and writes an audit row. Tools share a
`Deps` object via `RunContext` carrying the SQLAlchemy session, business,
conversation, state, and current_time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic_ai import RunContext
from pydantic_ai.tools import Tool
from sqlalchemy import select

from app.engine.engine import RuleEngine
from app.models import Business, Conversation, Rule
from app.schemas.conversation_state import STATE_FIELDS, ConversationState
from app.services import audit


# --------------------------------------------------------------------------- #
# Deps + ToolResult
# --------------------------------------------------------------------------- #


@dataclass
class AgentDeps:
    db: Any  # sqlalchemy Session
    business_id: UUID
    conversation_id: UUID
    customer_identifier: str
    current_time: datetime
    judge: Any | None = None
    # Mutable per-turn state — bumped by update_conversation_state.
    state: dict[str, Any] = field(default_factory=dict)
    state_dirty: bool = False
    # Bookkeeping for the conversation row at end of turn.
    blocked_rule_ids: set[UUID] = field(default_factory=set)
    accepted_action: bool = False


class ToolResult(BaseModel):
    status: str  # accepted | blocked | needs_info | failed
    user_facing_message: str
    internal_reason: str = ""
    proposed_action: dict[str, Any] | None = None
    fired_rule_id: str | None = None
    fired_rule_type: str | None = None
    required_fields: list[str] | None = None
    error_code: str | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _load_engine(db, business_id: UUID, judge: Any) -> tuple[RuleEngine, Business]:
    biz = db.get(Business, business_id)
    rules = db.execute(
        select(Rule).where(Rule.business_id == business_id, Rule.is_active.is_(True))
    ).scalars().all()
    return RuleEngine.for_business(rules, judge=judge), biz


def _audit(deps: AgentDeps, **kw: Any) -> None:
    """Thin wrapper that captures the 4 always-identical audit.record kwargs
    (db, business_id, conversation_id, customer_identifier) so call sites
    only have to specify the per-event fields.
    """
    audit.record(
        deps.db,
        business_id=deps.business_id,
        conversation_id=deps.conversation_id,
        customer_identifier=deps.customer_identifier,
        **kw,
    )


def _check_and_audit(
    deps: AgentDeps,
    tool_name: str,
    args: dict[str, Any],
    *,
    proposed_action: dict[str, Any] | None = None,
) -> ToolResult:
    engine, biz = _load_engine(deps.db, deps.business_id, deps.judge)
    state_obj = ConversationState.model_validate(deps.state)
    result = engine.check(tool_name, args, biz, state_obj, deps.current_time)

    # Persist audit rows for every fired rule, plus a top-level event row.
    if result.fired_rules:
        for fired in result.fired_rules:
            _audit(
                deps,
                event_type="tool_call",
                outcome="blocked" if fired.outcome == "block" else fired.outcome,
                tool_name=tool_name,
                fired_rule_id=fired.rule_id,
                fired_rule_type=fired.rule_type,
                fired_rule_name=fired.rule_name,
                tool_args=args,
                proposed_action=proposed_action,
                user_facing_message=fired.user_facing_message,
                internal_reason=fired.internal_reason,
                required_fields=fired.required_fields or None,
            )
            if fired.outcome == "block":
                deps.blocked_rule_ids.add(fired.rule_id)
    else:
        # Accepted path: write a `rule_considered` row for every applicable
        # rule that passed FIRST, then the headline tool_call row last —
        # the activity rail reads top-down chronologically, so this gives
        # the natural story:
        #   "we considered Standard hours → passed"
        #   "we considered Service area → passed"
        #   …
        #   "book_appointment ACCEPTED ✓"
        # Trade-off: ~5x audit row count on accepts; acceptable for the
        # observability + per-business demo scale.
        for rule in engine.rules:
            if not rule.applies(tool_name) or rule.rule_type == "output_constraint":
                continue
            _audit(
                deps,
                event_type="rule_considered",
                outcome="passed",
                tool_name=tool_name,
                fired_rule_id=rule.id,
                fired_rule_type=rule.rule_type,
                fired_rule_name=rule.name,
                tool_args=args,
            )
        _audit(
            deps,
            event_type="tool_call",
            outcome=result.outcome,
            tool_name=tool_name,
            tool_args=args,
            proposed_action=proposed_action,
        )

    if result.outcome == "accepted":
        deps.accepted_action = True
        return ToolResult(
            status="accepted",
            user_facing_message="OK — confirmed.",
            internal_reason="No rules blocked",
            proposed_action=proposed_action,
        )
    if result.outcome == "blocked":
        return ToolResult(
            status="blocked",
            user_facing_message=result.user_facing_message or "That isn't allowed by the current rules.",
            internal_reason=result.internal_reason,
            fired_rule_id=str(result.primary_rule_id) if result.primary_rule_id else None,
            fired_rule_type=result.primary_rule_type,
        )
    # needs_info
    return ToolResult(
        status="needs_info",
        user_facing_message=result.user_facing_message or "I need a bit more information.",
        required_fields=result.required_fields,
        fired_rule_id=str(result.primary_rule_id) if result.primary_rule_id else None,
        fired_rule_type=result.primary_rule_type,
    )


# --------------------------------------------------------------------------- #
# Action tools
# --------------------------------------------------------------------------- #


async def book_appointment(
    ctx: RunContext[AgentDeps],
    date: str,
    time: str,
    service_type: str,
    address_zip: str | int | None = None,
) -> ToolResult:
    """Book a service appointment for the customer.

    The rule engine validates this against business hours, service area,
    services offered, eligibility, and lead time before allowing it.

    Args:
        date: ISO date like "2026-06-01".
        time: 24-hour time like "10:00".
        service_type: e.g. "hvac", "plumbing", "electrical".
        address_zip: optional ZIP code as a string ("32801"). Pass as a
            string even if it looks numeric.
    """
    args: dict[str, Any] = {"date": date, "time": time, "service_type": service_type}
    if address_zip is not None:
        args["address_zip"] = str(address_zip)
    proposed = {"action": "book", **args}
    return _check_and_audit(ctx.deps, "book_appointment", args, proposed_action=proposed)


async def update_conversation_state(
    ctx: RunContext[AgentDeps], field: str, value: Any
) -> ToolResult:
    """Record a single fact about the customer (e.g., is_homeowner=true)."""
    if field not in STATE_FIELDS:
        return ToolResult(
            status="failed",
            user_facing_message="(internal) cannot record that field — not in the conversation state schema.",
            error_code="unknown_state_field",
        )
    # Idempotent: if the field is already set to this value, don't write a
    # duplicate audit row (LLMs sometimes re-emit the same tool call).
    if ctx.deps.state.get(field) == value:
        return ToolResult(
            status="accepted",
            user_facing_message=f"(already recorded {field} = {value})",
            internal_reason=f"state.{field} unchanged",
        )
    ctx.deps.state[field] = value
    ctx.deps.state_dirty = True
    _audit(
        ctx.deps,
        event_type="state_update",
        outcome="info",
        tool_name="update_conversation_state",
        tool_args={"field": field, "value": value},
    )
    return ToolResult(
        status="accepted",
        user_facing_message=f"Got it — recorded {field}.",
        internal_reason=f"state.{field} updated",
    )


async def lookup_service_area(
    ctx: RunContext[AgentDeps], address_zip: str | int
) -> ToolResult:
    """Check whether a ZIP code is inside the service area."""
    return _check_and_audit(ctx.deps, "lookup_service_area", {"address_zip": str(address_zip)})


async def check_availability(
    ctx: RunContext[AgentDeps], date: str, service_type: str | None = None
) -> ToolResult:
    """Read-only check of whether a date/service combo would be allowed."""
    args: dict[str, Any] = {"date": date}
    if service_type:
        args["service_type"] = service_type
    return _check_and_audit(ctx.deps, "check_availability", args)


async def escalate_to_human(
    ctx: RunContext[AgentDeps], reason: str, urgency: str = "normal"
) -> ToolResult:
    """Hand the conversation off to a human agent."""
    _audit(
        ctx.deps,
        event_type="tool_call",
        outcome="info",
        tool_name="escalate_to_human",
        tool_args={"reason": reason, "urgency": urgency},
        user_facing_message="Connecting you with a human dispatcher.",
    )
    return ToolResult(
        status="accepted",
        user_facing_message="Connecting you with a human dispatcher — they'll text you shortly.",
        internal_reason=f"Escalation: {reason} (urgency={urgency})",
    )


# --------------------------------------------------------------------------- #
# Introspection tools
# --------------------------------------------------------------------------- #


async def lookup_relevant_rules(ctx: RunContext[AgentDeps], tool_name: str) -> dict[str, Any]:
    """Return the names + descriptions of rules that would apply to a tool call."""
    engine, _ = _load_engine(ctx.deps.db, ctx.deps.business_id, ctx.deps.judge)
    relevant = [
        {
            "name": r.name,
            "rule_type": r.rule_type,
            "priority": r.priority,
        }
        for r in engine.rules
        if r.applies(tool_name)
    ]
    _audit(
        ctx.deps,
        event_type="lookup",
        outcome="info",
        tool_name="lookup_relevant_rules",
        tool_args={"tool_name": tool_name},
    )
    return {"tool_name": tool_name, "rules": relevant}


async def check_action(
    ctx: RunContext[AgentDeps], tool_name: str, args: dict[str, Any]
) -> ToolResult:
    """Dry-run a tool call. Records audit but does not commit a booking."""
    return _check_and_audit(ctx.deps, tool_name, args)


async def request_information(
    ctx: RunContext[AgentDeps], fields: list[str], context: str = ""
) -> dict[str, Any]:
    """Tell the user which state fields you still need."""
    _audit(
        ctx.deps,
        event_type="state_update",
        outcome="needs_info",
        tool_name="request_information",
        tool_args={"fields": fields, "context": context},
        required_fields=fields,
    )
    return {"fields": fields, "context": context}


# --------------------------------------------------------------------------- #
# Tool list (consumed by the agent factory)
# --------------------------------------------------------------------------- #


def all_tools() -> list[Tool]:
    return [
        Tool(book_appointment, takes_ctx=True),
        Tool(update_conversation_state, takes_ctx=True),
        Tool(lookup_service_area, takes_ctx=True),
        Tool(check_availability, takes_ctx=True),
        Tool(escalate_to_human, takes_ctx=True),
        Tool(lookup_relevant_rules, takes_ctx=True),
        Tool(check_action, takes_ctx=True),
        Tool(request_information, takes_ctx=True),
    ]
