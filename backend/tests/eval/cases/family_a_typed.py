"""Family A — pure typed rules.

Each case installs one or more typed rules and exercises the engine against
a single tool call. Deterministic, no LLM, gating.
"""
from __future__ import annotations

from datetime import datetime

from tests.eval.businesses import (
    homeowner_required,
    hours_mon_fri,
    lead_time_48h_emergency_bypass,
    services_hvac_plumbing,
    zip_allow_deny,
)
from tests.eval.framework import (
    BlockedByRule,
    EvalCase,
    NeedsInfoFields,
    OutcomeIs,
    PrimaryRuleIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape


# ---- business_hours --------------------------------------------------------

register(
    EvalCase(
        id="EV-A-001",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Sunday plumbing → blocked by hours",
        runner_kind="engine",
        rules=[hours_mon_fri()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-21", "time": "10:00", "service_type": "plumbing"},
        },
        assertions=[
            OutcomeIs("blocked"),
            BlockedByRule("Standard hours"),
        ],
    )
)

register(
    EvalCase(
        id="EV-A-002",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Tuesday 10 AM plumbing → accepted",
        runner_kind="engine",
        rules=[hours_mon_fri()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-A-003",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Tuesday 7 PM (after close) → blocked",
        runner_kind="engine",
        rules=[hours_mon_fri()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "19:30", "service_type": "plumbing"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("hours")],
    )
)

register(
    EvalCase(
        id="EV-A-004",
        family=Family.A,
        input_shape=InputShape.S2,
        group=Group.G1,
        title="No date provided → needs_info on `date`",
        runner_kind="engine",
        rules=[hours_mon_fri()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"service_type": "plumbing"},
        },
        assertions=[OutcomeIs("needs_info"), NeedsInfoFields(("date",))],
    )
)

# ---- service_area_zip ------------------------------------------------------

register(
    EvalCase(
        id="EV-A-005",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="In-area ZIP → accepted",
        runner_kind="engine",
        rules=[zip_allow_deny()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"address_zip": "32801", "date": "2026-06-16", "time": "10:00"},
        },
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-A-006",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Out-of-area ZIP → blocked",
        runner_kind="engine",
        rules=[zip_allow_deny()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"address_zip": "99999", "date": "2026-06-16", "time": "10:00"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("Service area")],
    )
)

register(
    EvalCase(
        id="EV-A-007",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Explicitly-denied ZIP → blocked (deny-list precedence)",
        runner_kind="engine",
        rules=[zip_allow_deny()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"address_zip": "32804", "date": "2026-06-16", "time": "10:00"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("Service area")],
    )
)

# ---- services_offered ------------------------------------------------------

register(
    EvalCase(
        id="EV-A-008",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Allowed trade (hvac) → accepted",
        runner_kind="engine",
        rules=[services_hvac_plumbing()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"service_type": "hvac", "date": "2026-06-16", "time": "10:00"},
        },
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-A-009",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Disallowed trade (roofing) → blocked",
        runner_kind="engine",
        rules=[services_hvac_plumbing()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"service_type": "roofing", "date": "2026-06-16", "time": "10:00"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("trades")],
    )
)

# ---- customer_eligibility --------------------------------------------------

register(
    EvalCase(
        id="EV-A-010",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Renter (homeowner_required=true) → blocked",
        runner_kind="engine",
        rules=[homeowner_required()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
        },
        state={"is_homeowner": False},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Homeowner")],
    )
)

register(
    EvalCase(
        id="EV-A-011",
        family=Family.A,
        input_shape=InputShape.S2,
        group=Group.G3,
        title="is_homeowner unset → needs_info",
        runner_kind="engine",
        rules=[homeowner_required()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
        },
        state={},
        assertions=[OutcomeIs("needs_info"), NeedsInfoFields(("is_homeowner",))],
    )
)

# ---- lead_time_minimum -----------------------------------------------------

register(
    EvalCase(
        id="EV-A-012",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="HVAC same-day → blocked by 48h lead time",
        runner_kind="engine",
        rules=[lead_time_48h_emergency_bypass()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-15", "time": "16:00", "service_type": "hvac"},
            "current_time": datetime(2026, 6, 15, 14, 0),
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("lead time")],
    )
)

register(
    EvalCase(
        id="EV-A-013",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="HVAC same-day with is_emergency=true → bypassed → accepted",
        runner_kind="engine",
        rules=[lead_time_48h_emergency_bypass()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-15", "time": "16:00", "service_type": "hvac"},
            "current_time": datetime(2026, 6, 15, 14, 0),
        },
        state={"is_emergency": True},
        assertions=[OutcomeIs("accepted")],
    )
)

register(
    EvalCase(
        id="EV-A-014",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="Plumbing same-day (lead-time scoped to hvac) → accepted",
        runner_kind="engine",
        rules=[lead_time_48h_emergency_bypass()],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-15", "time": "16:00", "service_type": "plumbing"},
            "current_time": datetime(2026, 6, 15, 14, 0),
        },
        assertions=[OutcomeIs("accepted")],
    )
)
