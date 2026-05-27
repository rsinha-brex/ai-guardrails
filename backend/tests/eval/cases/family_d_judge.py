"""Family D — hybrid deterministic + LLM judge rules.

Uses FakeJudgeClient with deterministic answers to exercise the judge-routing
machinery (caching, AND/OR composition, fail-closed semantics) without
calling a real LLM. Real-LLM judge accuracy is a separate Group G9 concern.
"""
from __future__ import annotations

from app.engine.expressions import FakeJudgeClient
from tests.eval.businesses import _snap
from tests.eval.framework import (
    BlockedByRule,
    EvalCase,
    OutcomeIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape


def _emergency_bypass_rule():
    """No plumbing after 4 PM unless judge says it's an emergency."""
    return _snap(
        "conditional_block",
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
                            "question": "Is this a plumbing emergency requiring immediate attention?",
                        },
                    },
                ],
            },
            "block_message": "Plumbing after 4 PM is emergency-only.",
        },
        name="Late-day emergency bypass",
        priority=150,
    )


# Judge says emergency=true → bypassed → accepted
register(
    EvalCase(
        id="EV-D-001",
        family=Family.D,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="Late plumbing + judge=emergency → accepted",
        runner_kind="engine",
        rules=[_emergency_bypass_rule()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "17:30",
                "service_type": "plumbing",
            },
            "judge": FakeJudgeClient(answers={"emergency": True}),
        },
        state={"reported_issue": "Pipe burst, water everywhere"},
        assertions=[OutcomeIs("accepted")],
    )
)

# Judge says emergency=false → blocked
register(
    EvalCase(
        id="EV-D-002",
        family=Family.D,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="Late plumbing + judge=non-emergency → blocked",
        runner_kind="engine",
        rules=[_emergency_bypass_rule()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "17:30",
                "service_type": "plumbing",
            },
            "judge": FakeJudgeClient(answers={"emergency": False}),
        },
        state={"reported_issue": "Slow drain, no rush"},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Late-day")],
    )
)

# Judge irrelevant — early plumbing always passes (deterministic clauses fail first)
register(
    EvalCase(
        id="EV-D-003",
        family=Family.D,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="Early plumbing — judge never queried (short-circuit)",
        runner_kind="engine",
        rules=[_emergency_bypass_rule()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "10:00",
                "service_type": "plumbing",
            },
            "judge": FakeJudgeClient(),  # no answers — would fail-closed if asked
        },
        state={"reported_issue": "regular maintenance"},
        assertions=[OutcomeIs("accepted")],
    )
)


# Tone-sensitive trigger: contractor detection
def _contractor_block_rule():
    return _snap(
        "conditional_block",
        {
            "trigger": {
                "op": "llm_judge",
                "field": "state.reported_issue",
                "question": "Does this message indicate the customer is a contractor (rather than a homeowner)?",
            },
            "block_message": "Contractors aren't booked at residential rates.",
        },
        name="Contractor detection",
        priority=130,
    )


register(
    EvalCase(
        id="EV-D-004",
        family=Family.D,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="Judge classifies contractor language → block",
        runner_kind="engine",
        rules=[_contractor_block_rule()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
            "judge": FakeJudgeClient(answers={"contractor": True}),
        },
        state={"reported_issue": "Need it for a flip we're working on, 4 units"},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Contractor")],
    )
)

register(
    EvalCase(
        id="EV-D-005",
        family=Family.D,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="Judge says not-contractor → accepted",
        runner_kind="engine",
        rules=[_contractor_block_rule()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
            "judge": FakeJudgeClient(answers={"contractor": False}),
        },
        state={"reported_issue": "AC stopped working at our house"},
        assertions=[OutcomeIs("accepted")],
    )
)
