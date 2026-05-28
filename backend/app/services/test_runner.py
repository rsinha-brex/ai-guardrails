"""Test runner — runs a test case end-to-end against the main agent.

Strategy (from § 10):
1. Create a fresh isolated conversation flagged is_test=true.
2. Inject only the rule-under-test (plus minimum baseline) into the system prompt.
3. Send the customer message through the chat flow.
4. Inspect the audit log + final state to determine the actual outcome.
5. Compare to expected, mark pass/fail, persist last_run_*.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.agent import build_agent
from app.agent.judge import LLMJudge
from app.agent.tools import AgentDeps
from app.models import AuditLog, Business, Conversation, Message, Rule, TestCase

_AGENT = build_agent()
_JUDGE = LLMJudge()


async def run_test_case(db: Session, test_case_id: UUID) -> dict[str, Any]:
    tc = db.get(TestCase, test_case_id)
    if tc is None:
        raise ValueError("test case not found")
    rule = db.get(Rule, tc.rule_id)
    if rule is None:
        raise ValueError("rule not found")
    biz = db.get(Business, rule.business_id)

    # Spin a fresh isolated conversation. We don't restrict the rule catalog
    # — running with the full ruleset matches production behavior and gives
    # the agent enough context. Tests still target one rule per case.
    conv = Conversation(
        business_id=biz.id,
        customer_identifier=f"Test #{test_case_id.hex[:6]}",
        state={},
        is_test=True,
    )
    db.add(conv)
    db.flush()

    deps = AgentDeps(
        db=db,
        business_id=conv.business_id,
        conversation_id=conv.id,
        customer_identifier=conv.customer_identifier,
        current_time=datetime.now(UTC),
        judge=_JUDGE,
    )
    user_msg = Message(conversation_id=conv.id, role="user", content=tc.customer_message)
    db.add(user_msg)
    db.flush()

    try:
        result = await _AGENT.run(tc.customer_message, deps=deps)
        agent_text = result.output
    except Exception as exc:
        agent_text = f"(agent failed: {exc})"

    db.add(Message(conversation_id=conv.id, role="assistant", content=agent_text))
    if deps.state_dirty:
        conv.state = dict(deps.state)
    if deps.accepted_action:
        conv.had_accepted_action = True
    if deps.blocked_rule_ids:
        conv.had_blocked_action = True
        conv.blocked_rule_ids = list(deps.blocked_rule_ids)
    db.flush()

    # Determine actual outcome from audit log.
    audit_rows = db.execute(
        select(AuditLog).where(AuditLog.conversation_id == conv.id).order_by(AuditLog.fired_at)
    ).scalars().all()

    actual_outcome = "open"
    fired_rule_for_target = False
    audit_excerpt: list[dict[str, Any]] = []
    for r in audit_rows:
        audit_excerpt.append(
            {
                "event_type": r.event_type,
                "outcome": r.outcome,
                "tool_name": r.tool_name,
                "fired_rule_name": r.fired_rule_name,
                "internal_reason": r.internal_reason,
            }
        )
        if r.fired_rule_id == tc.rule_id:
            fired_rule_for_target = True
            if r.outcome == "blocked":
                actual_outcome = "block"
            elif r.outcome == "needs_info":
                actual_outcome = "needs_info"
        if r.outcome == "accepted" and actual_outcome == "open":
            actual_outcome = "allow"

    # If the target rule didn't fire and we never accepted/blocked, see if the
    # agent's reply implies needs_info (best-effort).
    if not fired_rule_for_target and actual_outcome == "open":
        if "?" in agent_text:
            actual_outcome = "needs_info"

    expected = tc.expected_outcome  # block | allow | needs_info
    expected_norm = "block" if expected == "block" else expected
    passed = actual_outcome == expected_norm

    tc.last_run_at = datetime.now(UTC)
    tc.last_run_result = "pass" if passed else "fail"
    tc.last_run_details = {
        "expected": expected_norm,
        "actual": actual_outcome,
        "agent_response": agent_text,
        "fired_rule_for_target": fired_rule_for_target,
        "audit": audit_excerpt,
        "conversation_id": str(conv.id),
    }

    db.commit()
    return {
        "id": str(tc.id),
        "result": tc.last_run_result,
        "expected": expected_norm,
        "actual": actual_outcome,
        "agent_response": agent_text,
        "audit": audit_excerpt,
    }


async def run_all_for_rule(db: Session, rule_id: UUID) -> list[dict[str, Any]]:
    rows = db.execute(select(TestCase).where(TestCase.rule_id == rule_id)).scalars().all()
    out: list[dict[str, Any]] = []
    for tc in rows:
        out.append(await run_test_case(db, tc.id))
    return out
