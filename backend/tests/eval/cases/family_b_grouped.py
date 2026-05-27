"""Family B — group-scoped triggers (typed-rule semantics via conditional_block)."""
from __future__ import annotations

from tests.eval.businesses import no_plumbing_after_4pm, pre_1978_block
from tests.eval.framework import (
    BlockedByRule,
    EvalCase,
    OutcomeIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape


register(
    EvalCase(
        id="EV-B-001",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="Plumbing at 5 PM → blocked by 'no plumbing after 4 PM'",
        runner_kind="engine",
        rules=[no_plumbing_after_4pm()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "17:00", "service_type": "plumbing"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("plumbing")],
    )
)

register(
    EvalCase(
        id="EV-B-002",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="HVAC at 5 PM (rule scoped to plumbing) → accepted",
        runner_kind="engine",
        rules=[no_plumbing_after_4pm()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "17:00", "service_type": "hvac"},
        },
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-B-003",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="Plumbing at 10 AM (before cutoff) → accepted",
        runner_kind="engine",
        rules=[no_plumbing_after_4pm()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-B-004",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="Pre-1978 home → blocked",
        runner_kind="engine",
        rules=[pre_1978_block()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"property_year_built": 1965},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Pre-1978")],
    )
)

register(
    EvalCase(
        id="EV-B-005",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="2010-built home (post-1978) → accepted",
        runner_kind="engine",
        rules=[pre_1978_block()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"property_year_built": 2010},
        assertions=[OutcomeIs("accepted")],
    )
)
