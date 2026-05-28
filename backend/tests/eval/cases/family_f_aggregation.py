"""Family F — multi-rule aggregation."""
from __future__ import annotations

from tests.eval.businesses import (
    hours_mon_fri,
    no_plumbing_after_4pm,
    services_hvac_plumbing,
    zip_allow_deny,
)
from tests.eval.framework import (
    BlockedByRule,
    EvalCase,
    FiredRuleCount,
    OutcomeIs,
    PrimaryRuleIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape

register(
    EvalCase(
        id="EV-F-001",
        family=Family.F,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="Sunday + out-of-area ZIP → both rules fire; hours wins (priority 200 > 180)",
        runner_kind="engine",
        rules=[hours_mon_fri(), zip_allow_deny()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-21",  # Sunday
                "time": "10:00",
                "service_type": "plumbing",
                "address_zip": "99999",  # not in allow list
            },
        },
        assertions=[
            OutcomeIs("blocked"),
            FiredRuleCount(2),
            PrimaryRuleIs("Standard hours"),  # higher priority
        ],
    )
)

register(
    EvalCase(
        id="EV-F-002",
        family=Family.F,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="Block+pass mix: out-of-area + valid trade → only zip rule fires",
        runner_kind="engine",
        rules=[zip_allow_deny(), services_hvac_plumbing()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "10:00",
                "service_type": "hvac",
                "address_zip": "99999",
            },
        },
        assertions=[
            OutcomeIs("blocked"),
            FiredRuleCount(1),
            BlockedByRule("Service area"),
        ],
    )
)

register(
    EvalCase(
        id="EV-F-003",
        family=Family.F,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="Two passes + one block (group rule) → block surfaces",
        runner_kind="engine",
        rules=[zip_allow_deny(), services_hvac_plumbing(), no_plumbing_after_4pm()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "17:30",
                "service_type": "plumbing",
                "address_zip": "32801",
            },
        },
        assertions=[
            OutcomeIs("blocked"),
            BlockedByRule("plumbing"),
            FiredRuleCount(1),
        ],
    )
)

register(
    EvalCase(
        id="EV-F-004",
        family=Family.F,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="All three rules pass → accepted",
        runner_kind="engine",
        rules=[zip_allow_deny(), services_hvac_plumbing(), no_plumbing_after_4pm()],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "10:00",
                "service_type": "plumbing",
                "address_zip": "32801",
            },
        },
        assertions=[OutcomeIs("accepted"), FiredRuleCount(0)],
    )
)
