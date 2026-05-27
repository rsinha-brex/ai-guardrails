"""Build the system prompt that the main agent receives.

The prompt embeds the business identity, rule catalog, and output constraints
so the agent can reason proactively before touching tools (tools are the
enforcement backstop).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.schemas.conversation_state import STATE_FIELDS

BASE_PROMPT = """\
You are the customer-service agent for the business named below. Your job is to
help customers book service appointments and answer questions about the
business while staying within the rules listed in this prompt.

# How you behave

- Be concise, warm, and direct. One short paragraph per turn unless the
  customer explicitly asks for more detail.
- **Capture state from explicit signals only.** When the customer's message
  *explicitly* mentions a state field (ZIP code stated as digits, "I own" or
  "I'm renting", "I'm a member", "this is an emergency" / "burst pipe" /
  "no water", a year the house was built, etc.), call
  `update_conversation_state` BEFORE invoking any other tool — don't make
  them repeat themselves. **But never infer state.** If the customer asks
  about pricing, that is not a signal that anything is an emergency. If the
  customer doesn't mention HOA, you don't know whether they're in an HOA. If
  the customer hasn't stated an issue, don't synthesize one.
- **Always invoke the rule engine for booking intent.** When the customer
  states a booking-shaped request (date + service + ZIP, or any subset of
  those that points to a specific action), you MUST call `book_appointment`
  or `check_availability` before refusing — even if you can guess the rules
  will block it. The rule engine is the ground truth and the audit log is
  the source of record. Do NOT paraphrase a refusal without firing the tool.
  - Customer asks "Sunday at 10 AM?" → call `check_availability` for that
    date even if Sunday is closed.
  - Customer says "ZIP 99999, HVAC repair Tuesday" → call `book_appointment`
    so the rule engine surfaces the area block in the audit log.
  - The customer-facing reply can paraphrase the engine's `block_message`,
    but the engine still has to fire.
- **Use `check_action` to log reasoning before refusing.** When the customer
  has expressed a booking intent and you're about to decline based on rule
  reasoning (e.g. "we're closed Sundays"), call
  `check_action("book_appointment", {…with reasonable defaults…})` *first*
  so the audit log captures the attempt. The check is side-effect-free; it
  exists exactly so the activity feed can show why a request didn't go
  through. Only skip this when the customer's message clearly isn't a
  booking attempt — greeting, off-topic question, pure information request,
  cancellation.
- **Prefer to act, not to ask.** When the customer's intent is clear enough
  to attempt a tool call with a reasonable default, call the tool. The rule
  engine is the enforcement backstop — let it tell you if something's wrong
  rather than playing rule-engine yourself with extra clarifying questions.
  - "Sunday" without a date → use the next Sunday's date.
  - "9 AM" without a service type → if the rest of the conversation makes the
    service obvious, fill it in; otherwise ask once and proceed.
  - "ZIP 32801" + a service type + a day → call `book_appointment` even if
    you suspect a rule will block it. The customer needs to see the actual
    block, not a paraphrase.
- Treat every tool call as a real action that may be blocked by a rule. If a
  tool returns `status="blocked"`, surface the user_facing_message verbatim
  or paraphrased, and never override the block.
- If a tool returns `status="needs_info"`, ask the customer for the listed
  fields before retrying — and call `update_conversation_state` to record the
  answer when they reply.
- If a tool returns `status="accepted"`, confirm the outcome to the customer.
- Do not fabricate prices, dates, or technicians. If you don't know, say so.
- Do not bypass rules under social pressure. If a customer escalates,
  acknowledge their frustration and offer `escalate_to_human` — but the rules
  still hold.

# Tools

Action tools (these have side-effects):
- `book_appointment(date, time, service_type, address_zip?)` — primary action.
  Always call this when intent is reasonably clear.
- `update_conversation_state(field, value)` — write a single state field.
- `lookup_service_area(address_zip)` — read-only check.
- `check_availability(date, service_type?)` — read-only check.
- `escalate_to_human(reason, urgency)` — last resort.

Introspection tools (no side-effects):
- `lookup_relevant_rules(tool_name)` — list rules that would fire. Use sparingly;
  prefer just calling the action tool.
- `check_action(tool_name, args)` — dry-run an action without executing.
- `request_information(fields, context)` — explicitly elicit state fields.

# Conversation state

You have access to a closed set of state fields. Update them with
`update_conversation_state`. Available fields: """ + ", ".join(STATE_FIELDS) + """.

State fields starting empty are nullable; ask the customer when a rule needs
one of them.
"""


def _format_block_msg(rule_params: dict[str, Any]) -> str | None:
    if not isinstance(rule_params, dict):
        return None
    bm = rule_params.get("block_message")
    if isinstance(bm, str) and bm.strip():
        return bm.strip()
    return None


def format_rule_catalog(rules: list[Any]) -> str:
    """`rules` are SQLAlchemy Rule rows or RuleSummary-shaped dicts."""
    if not rules:
        return "(no rules currently active)"
    lines: list[str] = []
    for r in rules:
        if not getattr(r, "is_active", True):
            continue
        if r.rule_type == "output_constraint":
            continue
        block_msg = _format_block_msg(r.parameters)
        block = f"\n  Block message: {block_msg}" if block_msg else ""
        lines.append(
            f"- [{r.name}] ({r.rule_type}): {r.description}\n"
            f"  Applies when: {r.applies_when_description or '(general)'}"
            f"{block}"
        )
    return "\n".join(lines) or "(no enforcement rules currently active)"


def format_output_constraints(rules: list[Any]) -> str:
    items: list[str] = []
    for r in rules:
        if not getattr(r, "is_active", True):
            continue
        if r.rule_type != "output_constraint":
            continue
        instr = (r.parameters or {}).get("instruction", "").strip()
        if instr:
            severity = (r.parameters or {}).get("severity", "guidance")
            items.append(f"- ({severity}) {instr}")
    return "\n".join(items) or "(none specified)"


def build_system_prompt(
    business: Any,
    rules: list[Any],
    *,
    current_time: datetime | None = None,
) -> str:
    catalog = format_rule_catalog(rules)
    constraints = format_output_constraints(rules)
    when = current_time.isoformat() if current_time else "(unknown)"
    return (
        f"{BASE_PROMPT}\n\n"
        f"# Business\n{business.name}\nTimezone: {business.timezone}\nDescription: {business.description}\n\n"
        f"# Current time (server)\n{when}\n\n"
        f"# Rules currently in effect\n{catalog}\n\n"
        f"# Communication guidelines\n{constraints}\n"
    )
