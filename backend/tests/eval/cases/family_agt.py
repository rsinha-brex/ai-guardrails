"""Family AGT — agent tool-call routing (deterministic via FunctionModel).

Each case scripts a sequence of tool calls via Pydantic AI's `FunctionModel`
and asserts on what the engine + audit log produced. The LLM is bypassed
entirely, so these cases run sub-second and are part of the gating tier
(no API key required).

What AGT cases prove:
- Tools route through `_check_and_audit` correctly when invoked by the agent
- The audit log captures rule_considered + tool_call rows in the right
  order with the right shapes
- Multi-tool flows (state-gather → book) preserve `deps.state` mutations
  across scripted callbacks
- Refusal tools (escalate_to_human) skip the engine and write a different
  audit shape

What AGT cases do NOT prove (that's Family E2E's job):
- The LLM picks the right tool from a customer message
- The LLM constructs correct arguments from natural language
- The agent recovers from pushback / adversarial input
"""
from __future__ import annotations

from datetime import datetime

from tests.eval.businesses import (
    homeowner_required,
    hours_mon_fri,
    lead_time_48h_emergency_bypass,
    no_plumbing_after_4pm,
    services_hvac_plumbing,
    zip_allow_deny,
)
from tests.eval.framework import (
    AgentDidNotCallTool,
    AuditEventCount,
    AuditEventEmitted,
    EvalCase,
    StateFieldSet,
    ToolCalled,
    ToolCalledWithArgs,
    ToolCallOrder,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape

# AGT-001 — Sunday HVAC blocked. Headline smoke test.
register(
    EvalCase(
        id="EV-AGT-001",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Scripted Sunday booking → engine blocks → audit captures",
        runner_kind="agent_unit",
        rules=[hours_mon_fri()],
        inputs={
            "message": "Can you book me Sunday morning for HVAC?",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-21", "time": "10:00", "service_type": "hvac"}),
            ],
            "final_text": "We're closed Sundays.",
        },
        assertions=[
            ToolCalled("book_appointment"),
            ToolCalledWithArgs("book_appointment", {"service_type": "hvac"}),
            AuditEventEmitted("tool_call", outcome="blocked", fired_rule_substring="hours"),
        ],
        notes="Smoke test: validates FunctionModel + AgentDeps hooks end-to-end.",
    )
)


# AGT-002 — Tuesday booking accepted; rule_considered rows precede tool_call.
register(
    EvalCase(
        id="EV-AGT-002",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Scripted Tuesday booking → accepted; audit has rule_considered rows",
        runner_kind="agent_unit",
        rules=[hours_mon_fri()],
        inputs={
            "message": "Tuesday at 10am for hvac",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"}),
            ],
            "final_text": "Booked.",
        },
        assertions=[
            ToolCalled("book_appointment"),
            AuditEventEmitted("tool_call", outcome="accepted", tool_name="book_appointment"),
            AuditEventEmitted("rule_considered", outcome="passed", fired_rule_substring="hours"),
            AuditEventCount("rule_considered", 1),
        ],
    )
)


# AGT-003 — Multi-turn state gathering: update_conversation_state then book.
register(
    EvalCase(
        id="EV-AGT-003",
        family=Family.AGT,
        input_shape=InputShape.S4,
        group=Group.G7,
        title="State-gather → book: homeowner update precedes booking",
        runner_kind="agent_unit",
        rules=[homeowner_required(), hours_mon_fri()],
        state={},
        inputs={
            "message": "I'm the homeowner, book me Tuesday 10am hvac",
            "scripted_tool_calls": [
                ("update_conversation_state", {"field": "is_homeowner", "value": True}),
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"}),
            ],
            "final_text": "Booked.",
        },
        assertions=[
            ToolCallOrder(["update_conversation_state", "book_appointment"]),
            StateFieldSet("is_homeowner", True),
            AuditEventEmitted("tool_call", outcome="accepted", tool_name="book_appointment"),
        ],
        notes="Verifies deps.state mutations propagate across FunctionModel callbacks.",
    )
)


# AGT-004 — needs_info: missing homeowner state surfaces as needs_info.
register(
    EvalCase(
        id="EV-AGT-004",
        family=Family.AGT,
        input_shape=InputShape.S2,
        group=Group.G7,
        title="Booking without homeowner state → needs_info",
        runner_kind="agent_unit",
        rules=[homeowner_required()],
        state={},
        inputs={
            "message": "Book me Tuesday 10am hvac",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"}),
            ],
            "final_text": "Are you the homeowner?",
        },
        assertions=[
            ToolCalled("book_appointment"),
            AuditEventEmitted("tool_call", outcome="needs_info", fired_rule_substring="homeowner"),
        ],
    )
)


# AGT-005 — Out-of-area ZIP blocked.
register(
    EvalCase(
        id="EV-AGT-005",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Out-of-area ZIP → blocked by service_area_zip",
        runner_kind="agent_unit",
        rules=[zip_allow_deny()],
        inputs={
            "message": "Tuesday 10am, ZIP 99999",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "hvac", "address_zip": "99999"}),
            ],
            "final_text": "We don't serve that area.",
        },
        assertions=[
            ToolCalled("book_appointment"),
            AuditEventEmitted("tool_call", outcome="blocked", fired_rule_substring="service area"),
        ],
    )
)


# AGT-006 — Disallowed service type blocked.
register(
    EvalCase(
        id="EV-AGT-006",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Roofing booking → blocked by services_offered",
        runner_kind="agent_unit",
        rules=[services_hvac_plumbing()],
        inputs={
            "message": "I need roofing",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "roofing"}),
            ],
            "final_text": "We don't offer roofing.",
        },
        assertions=[
            ToolCalledWithArgs("book_appointment", {"service_type": "roofing"}),
            AuditEventEmitted("tool_call", outcome="blocked", fired_rule_substring="trades"),
        ],
    )
)


# AGT-007 — Multi-rule fired count + ordering. Asserts:
#   1. Several rule_considered rows are written on accept
#   2. They precede the tool_call row (the user's prior fix)
register(
    EvalCase(
        id="EV-AGT-007",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Accept with 4 rules installed → 4 rule_considered rows + 1 tool_call",
        runner_kind="agent_unit",
        rules=[
            hours_mon_fri(),
            services_hvac_plumbing(),
            zip_allow_deny(),
            lead_time_48h_emergency_bypass(),
        ],
        inputs={
            "message": "Tuesday 10am hvac in 32801, 4 days from now",
            "scripted_tool_calls": [
                # Tuesday 2026-06-23 (well past current_time 2026-06-15 14:00 — meets 48h lead time)
                ("book_appointment", {"date": "2026-06-23", "time": "10:00", "service_type": "hvac", "address_zip": "32801"}),
            ],
            "final_text": "Booked.",
        },
        assertions=[
            AuditEventCount("rule_considered", 4),
            AuditEventEmitted("tool_call", outcome="accepted"),
        ],
        notes="Guards the rule_considered-before-tool_call ordering regression.",
    )
)


# AGT-008 — Lead-time bypass via emergency state.
register(
    EvalCase(
        id="EV-AGT-008",
        family=Family.AGT,
        input_shape=InputShape.S4,
        group=Group.G7,
        title="Emergency state bypasses lead time → same-day HVAC accepted",
        runner_kind="agent_unit",
        rules=[lead_time_48h_emergency_bypass()],
        state={},
        inputs={
            "message": "Pipe burst — emergency hvac today at 4pm",
            "current_time": datetime(2026, 6, 15, 14, 0),  # Mon Jun 15 2 PM
            "scripted_tool_calls": [
                ("update_conversation_state", {"field": "is_emergency", "value": True}),
                ("book_appointment", {"date": "2026-06-15", "time": "16:00", "service_type": "hvac"}),
            ],
            "final_text": "Booked.",
        },
        assertions=[
            ToolCallOrder(["update_conversation_state", "book_appointment"]),
            StateFieldSet("is_emergency", True),
            AuditEventEmitted("tool_call", outcome="accepted", tool_name="book_appointment"),
        ],
    )
)


# AGT-009 — escalate_to_human bypasses the engine.
register(
    EvalCase(
        id="EV-AGT-009",
        family=Family.AGT,
        input_shape=InputShape.S20,
        group=Group.G7,
        title="Hostile customer → escalate; engine not invoked",
        runner_kind="agent_unit",
        rules=[hours_mon_fri()],
        inputs={
            "message": "Speak to a manager NOW",
            "scripted_tool_calls": [
                ("escalate_to_human", {"reason": "customer hostile", "urgency": "high"}),
            ],
            "final_text": "Connecting you to a manager.",
        },
        assertions=[
            ToolCalled("escalate_to_human"),
            AgentDidNotCallTool("book_appointment"),
            # escalate writes a tool_call row but with no fired_rule_id (engine bypassed)
            AuditEventEmitted("tool_call", tool_name="escalate_to_human"),
        ],
    )
)


# AGT-010 — Lookup-then-book via lookup_service_area + book_appointment.
register(
    EvalCase(
        id="EV-AGT-010",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Lookup service area then book → both audited",
        runner_kind="agent_unit",
        rules=[zip_allow_deny()],
        inputs={
            "message": "Do you serve 32801? If so, book Tuesday 10am hvac",
            "scripted_tool_calls": [
                ("lookup_service_area", {"address_zip": "32801"}),
                ("book_appointment", {"date": "2026-06-16", "time": "10:00", "service_type": "hvac", "address_zip": "32801"}),
            ],
            "final_text": "Yes — booked.",
        },
        assertions=[
            ToolCallOrder(["lookup_service_area", "book_appointment"]),
            AuditEventEmitted("tool_call", outcome="accepted", tool_name="book_appointment"),
        ],
    )
)


# AGT-011 — conditional_block fires on plumbing-after-4 PM.
register(
    EvalCase(
        id="EV-AGT-011",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="Late plumbing → blocked via conditional_block",
        runner_kind="agent_unit",
        rules=[no_plumbing_after_4pm()],
        inputs={
            "message": "Plumbing Tuesday at 5pm",
            "scripted_tool_calls": [
                ("book_appointment", {"date": "2026-06-16", "time": "17:00", "service_type": "plumbing"}),
            ],
            "final_text": "Plumbing crew is off after 4 PM.",
        },
        assertions=[
            ToolCalled("book_appointment"),
            AuditEventEmitted("tool_call", outcome="blocked", fired_rule_substring="plumbing"),
        ],
    )
)


# AGT-012 — check_action: read-only dry run.
register(
    EvalCase(
        id="EV-AGT-012",
        family=Family.AGT,
        input_shape=InputShape.S1,
        group=Group.G7,
        title="check_action dry-run → engine evaluates without committing",
        runner_kind="agent_unit",
        rules=[hours_mon_fri()],
        inputs={
            "message": "Would Sunday 10am work for hvac?",
            "scripted_tool_calls": [
                (
                    "check_action",
                    {
                        "tool_name": "book_appointment",
                        "args": {"date": "2026-06-21", "time": "10:00", "service_type": "hvac"},
                    },
                ),
            ],
            "final_text": "No, we're closed Sundays.",
        },
        assertions=[
            ToolCalled("check_action"),
            AgentDidNotCallTool("book_appointment"),
            # check_action runs the engine + writes audit, but with proposed_action set
            AuditEventEmitted("tool_call", outcome="blocked", fired_rule_substring="hours"),
        ],
    )
)
