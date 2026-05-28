"""Family C — preconditioned rules (block-unless-state-X)."""
from __future__ import annotations

from tests.eval.businesses import hoa_approval_required
from tests.eval.framework import BlockedByRule, EvalCase, OutcomeIs, register
from tests.eval.taxonomy import Family, Group, InputShape

register(
    EvalCase(
        id="EV-C-001",
        family=Family.C,
        input_shape=InputShape.S1,
        group=Group.G3,
        title="HOA-governed, is_homeowner=true → precondition met → accepted",
        runner_kind="engine",
        rules=[hoa_approval_required()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"hoa_governed": True, "is_homeowner": True},
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-C-002",
        family=Family.C,
        input_shape=InputShape.S1,
        group=Group.G3,
        title="HOA-governed, is_homeowner=false → precondition not met → blocked",
        runner_kind="engine",
        rules=[hoa_approval_required()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"hoa_governed": True, "is_homeowner": False},
        assertions=[OutcomeIs("blocked"), BlockedByRule("HOA")],
    )
)

register(
    EvalCase(
        id="EV-C-003",
        family=Family.C,
        input_shape=InputShape.S1,
        group=Group.G3,
        title="Not HOA-governed → trigger doesn't fire → accepted",
        runner_kind="engine",
        rules=[hoa_approval_required()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"hoa_governed": False, "is_homeowner": False},
        assertions=[OutcomeIs("accepted")],
    )
)
