"""Family G9 — full-pipeline compile + engine probe cases.

The deliverable test pass for spec § 3 isn't just "does the engine evaluate
a synthetic rule fixture correctly" (which families A-F cover) — it's "does
the *agent's compile loop* turn a business owner's plain-English description
into a rule that actually behaves the way they meant?" That's what these
cases verify, end-to-end:

    NL prompt
       │
       │  → app.agent.compile_agent.compile_rule(prompt)   [LIVE LLM]
       │
    CompiledRule
       │
       │  → install on a fresh in-memory RuleEngine
       │
    Engine
       │
       │  → engine.check(probe) for each probe
       │
    Outcome  → assert matches the case's expected outcome

Each case names the prompt, the expected rule_type, and 2-4 probes covering
both the "block path" (a request that should hit the rule) and the "accept
path" (a request that should pass through). Marked probabilistic because
the LLM isn't deterministic; threshold=0.5 over samples=2 keeps the API
spend bounded while still catching genuine compile regressions.
"""
from __future__ import annotations

from tests.eval.framework import (
    CompileResultKind,
    CompileRuleType,
    EvalCase,
    ProbesAllMatch,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape

# 1. business_hours — the simplest typed rule
register(
    EvalCase(
        id="EV-G9-001",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile 'closed Sundays' → blocks Sun, allows Mon",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "We're closed on Sundays. Open Monday through Saturday 8 AM to 6 PM.",
            "probes": [
                # 2026-06-21 is Sunday → block
                {
                    "args": {"date": "2026-06-21", "time": "10:00", "service_type": "plumbing"},
                    "state": {},
                    "expect": "blocked",
                },
                # 2026-06-22 is Monday → accept
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "plumbing"},
                    "state": {},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("business_hours"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
        notes="Tests the headline NL→rule path: closed-day phrasing must produce a business_hours rule whose closed_days actually blocks the right weekday.",
    )
)


# 2. service_area_zip — list parsing + allow/deny semantics
register(
    EvalCase(
        id="EV-G9-002",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile 'only ZIPs 32801 32802' → blocks 99999, allows 32801",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "We only book in ZIP codes 32801, 32802, and 32803. Anywhere else is out of area.",
            "probes": [
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "plumbing", "address_zip": "99999"},
                    "state": {},
                    "expect": "blocked",
                },
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "plumbing", "address_zip": "32801"},
                    "state": {},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("service_area_zip"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
    )
)


# 3. services_offered — vocabulary mapping
register(
    EvalCase(
        id="EV-G9-003",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile 'we do HVAC and plumbing' → blocks roofing, allows hvac",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "We only offer HVAC and plumbing services.",
            "probes": [
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "roofing"},
                    "state": {},
                    "expect": "blocked",
                },
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "hvac"},
                    "state": {},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("services_offered"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
    )
)


# 4. lead_time_minimum — date-arithmetic semantics
register(
    EvalCase(
        id="EV-G9-004",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile '48 hours notice' → blocks same-day, allows 3 days out",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "All bookings need at least 48 hours of notice.",
            "probes": [
                # current_time defaults to Mon Jun 15 2026 14:00; same-day at 16:00 = ~2h notice → block
                {
                    "args": {"date": "2026-06-15", "time": "16:00", "service_type": "hvac"},
                    "state": {},
                    "expect": "blocked",
                },
                # 3 days out = ~70h → accept
                {
                    "args": {"date": "2026-06-18", "time": "10:00", "service_type": "hvac"},
                    "state": {},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("lead_time_minimum"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
    )
)


# 5. customer_eligibility — homeowner gate with state propagation
register(
    EvalCase(
        id="EV-G9-005",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile 'homeowners only' → blocks renter, allows homeowner",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "We only book with the homeowner. We don't work with renters.",
            "probes": [
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "hvac"},
                    "state": {"is_homeowner": False},
                    "expect": "blocked",
                },
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "hvac"},
                    "state": {"is_homeowner": True},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("customer_eligibility"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
    )
)


# 6. conditional_block — escape-hatch DSL with combined conditions
register(
    EvalCase(
        id="EV-G9-006",
        family=Family.B,
        input_shape=InputShape.S1,
        group=Group.G9,
        title="Compile 'no plumbing after 4 PM' → blocks 5 PM plumbing, allows 10 AM",
        runner_kind="compile_and_probe",
        inputs={
            "prompt": "Don't book plumbing after 4 PM. We close the plumbing crew at 4.",
            "probes": [
                {
                    "args": {"date": "2026-06-22", "time": "17:00", "service_type": "plumbing"},
                    "state": {},
                    "expect": "blocked",
                },
                {
                    "args": {"date": "2026-06-22", "time": "10:00", "service_type": "plumbing"},
                    "state": {},
                    "expect": "accepted",
                },
            ],
        },
        assertions=[
            CompileResultKind("compiled"),
            CompileRuleType("conditional_block"),
            ProbesAllMatch(),
        ],
        samples=2,
        threshold=0.5,
        notes="Service-type-scoped time constraint should compile to conditional_block (not business_hours, since it's not the whole-business hours).",
    )
)
