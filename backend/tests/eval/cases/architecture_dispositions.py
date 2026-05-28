"""Architecture-disposition cases — patterns the system explicitly does NOT support.

These exercise the negative-space portion of the rule taxonomy:
- E11 cross-conversation lookups
- E17 inter-rule chaining (rules evaluate independently)
- E18 frequency-based throttling
- E19 random / probabilistic sampling
- E20 side-effects beyond block/pass

Most run through the compile agent and assert `compile_kind == "failure"`;
the engine-only case (EV-DIS-002) verifies that two rules' evaluations are
order-independent.
"""
from __future__ import annotations

from tests.eval.businesses import hours_mon_fri, zip_allow_deny
from tests.eval.framework import (
    CompileResultKind,
    EvalCase,
    OutcomeIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape

# E11 — cross-conversation lookup (compile must refuse)
register(
    EvalCase(
        id="EV-DIS-001",
        family=Family.DIS,
        input_shape=InputShape.S25,
        group=Group.G5,
        title="E11 cross-conversation lookup → CompileFailure",
        runner_kind="compile",
        inputs={
            "prompt": "Block any new appointment at an address that already has another booking within 24 hours."
        },
        assertions=[CompileResultKind("failure")],
        notes="Cross-conversation customer/booking history is not tracked — compile must refuse.",
    )
)

# E17 — engine: rules evaluate independently of each other
class _InertAssertion:
    """Custom assertion: the same args/state evaluate to the same outcome
    regardless of the order rules are passed to the engine."""

    def __init__(self, second_outcome: str):
        self.second_outcome = second_outcome

    def check(self, ev):  # type: ignore[no-untyped-def]
        from tests.eval.framework import AssertionResult

        first = ev.check_result.outcome if ev.check_result else None
        second = ev.extra.get("swapped_outcome")
        if first == second == self.second_outcome:
            return AssertionResult.passes(
                f"both orderings produced outcome={first}"
            )
        return AssertionResult.fails(
            f"order-dependent: first={first}, swapped={second}"
        )


def _ev_dis_002_setup() -> EvalCase:
    """Custom: install two rules, run engine, then re-run with reversed list, assert match."""
    rules = [hours_mon_fri(), zip_allow_deny()]

    case = EvalCase(
        id="EV-DIS-002",
        family=Family.DIS,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="E17 rules evaluate independently — order-invariant under swap",
        runner_kind="engine",
        rules=rules,
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-21",  # Sunday → blocked by hours
                "time": "10:00",
                "service_type": "plumbing",
                "address_zip": "32801",  # in-area
            },
            "swap_rules": True,
        },
        notes="Both rules fire independently; swapping rule list order must yield same result.",
    )
    case.assertions = [OutcomeIs("blocked"), _InertAssertion("blocked")]

    # Wrap run_engine_case-style execution: we'll monkey-patch by making the
    # case's "extra" computation happen inside a custom runner via inputs.
    # Simpler path: do the second-pass evaluation in a custom assertion that
    # re-runs the engine. To keep the framework simple, we attach a callback
    # via the inputs dict that runs after the first pass and stores the
    # outcome in evidence.extra. Implemented via a lightweight wrapper below.
    return case


register(_ev_dis_002_setup())


# Patch run_engine_case to honor the second-pass swap when the case's
# inputs contains "swap_rules": True. (Done in framework via an extra hook.)


# E18 — frequency-based throttling
register(
    EvalCase(
        id="EV-DIS-003",
        family=Family.DIS,
        input_shape=InputShape.S25,
        group=Group.G5,
        title="E18 frequency throttle (4th booking in 24h) → CompileFailure",
        runner_kind="compile",
        inputs={
            "prompt": "Block the 4th booking attempt from the same customer within 24 hours."
        },
        assertions=[CompileResultKind("failure")],
        notes="Frequency-based throttling needs cross-conversation history we don't track.",
    )
)

# E19 — random sampling
register(
    EvalCase(
        id="EV-DIS-004",
        family=Family.DIS,
        input_shape=InputShape.S25,
        group=Group.G5,
        title="E19 random sampling (block 20% of new-customer bookings) → CompileFailure",
        runner_kind="compile",
        inputs={
            "prompt": "Block 20% of new-customer bookings for additional verification, picked randomly."
        },
        assertions=[CompileResultKind("failure")],
        notes="Guardrails must be deterministic from the customer's perspective.",
    )
)

# E20 — side-effects
register(
    EvalCase(
        id="EV-DIS-005",
        family=Family.DIS,
        input_shape=InputShape.S25,
        group=Group.G5,
        title="E20 side-effect (notify dispatcher) → CompileFailure",
        runner_kind="compile",
        inputs={
            "prompt": "When a customer tries to book outside hours, send a Slack notification to the dispatcher."
        },
        assertions=[CompileResultKind("failure")],
        notes="Rule enforcement is pure block/pass; side effects belong in tool bodies.",
    )
)
