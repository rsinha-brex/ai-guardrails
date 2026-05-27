# Guardrail Evals Report
Generated: 2026-05-27T21:16:25.938790+00:00

## Headline

**✅ All green** — 52 cases registered.

| Total | PASS | CHARACTERIZED-PASS | FAIL |
| --- | --- | --- | --- |
| 52 | 36 | 16 | 0 |

## Spec compliance (take-home § 3)

| Spec requirement | Met? | Evidence |
| --- | --- | --- |
| Cover ≥3 distinct rule types | ✅ | 6 types exercised: business_hours, conditional_block, customer_eligibility, lead_time_minimum, service_area_zip, services_offered |
| Block + pass cases | ✅ | blocked seen: True; accepted seen: True |
| Single-command runnable | ✅ | `uv run pytest tests/eval -q` |
| Clear pass/fail output | ✅ | pytest summary + tables in this report |

## Strengths — what the eval demonstrates the system enforces

- **All five typed-rule evaluators behave correctly** at boundary, in-window, and missing-state conditions (open hours, ZIP allow/deny, services offered, homeowner gating with `needs_info` propagation, lead-time + emergency bypass).
  _Supported by_: `EV-A-001, EV-A-002, EV-A-003, EV-A-004, EV-A-005, EV-A-006`

- **Multi-rule aggregation has correct outcome precedence** — when multiple rules fire, the highest-priority `block` wins; `pass` is only emitted when every applicable rule passes; the audit captures every fired rule, not just the surfacing one.
  _Supported by_: `EV-F-001, EV-F-002, EV-F-003, EV-F-004`

- **LLM-judge composition routes correctly through `all_of` / `any_of` / `not` with deterministic short-circuit** — when an earlier deterministic clause fails, the judge is never queried (verified by passing a no-answer FakeJudgeClient that would otherwise fail-closed).
  _Supported by_: `EV-D-001, EV-D-002, EV-D-003, EV-D-004, EV-D-005`

- **Exotic patterns (E1–E10) are expressible inside the existing engine** — deeply nested `any_of`/`all_of`, regex on state, contains-substring address heuristics, negation rules ('except maintenance'), composed multi-judge triggers, and override-by-precondition all evaluate without engine extension.
  _Supported by_: `EV-EX-001, EV-EX-002, EV-EX-003, EV-EX-004, EV-EX-005, EV-EX-006`

- **Architecturally-rejected patterns are deterministically refused** — frequency throttling (E18), random sampling (E19), side-effects (E20), cross-conversation lookups (E11), and prompt-injection attempts are all caught by `_pre_check` before any LLM call. The engine's order-independence (E17) is verified by running the same args against rule-list variants.
  _Supported by_: `EV-DIS-001, EV-DIS-002, EV-DIS-003, EV-DIS-004, EV-DIS-005`

- **Adversarial inputs are handled** — PII targeting, protected-class wording, trivially-true rules, vague modifiers ('try to be helpful'), and prompt-injection phrasing all return `CompileFailure` deterministically through the pre-check, not through opaque LLM judgment.
  _Supported by_: `EV-ADV-001, EV-ADV-002, EV-ADV-003, EV-ADV-004, EV-ADV-005, EV-ADV-006`

- **`required_precondition` semantics are correct** — the rule short-circuits to pass when the precondition is unmet (the rule simply doesn't apply), and evaluates the trigger when the precondition is met.
  _Supported by_: `EV-C-001, EV-C-002, EV-C-003`


## Gaps & limitations — what's not yet covered

- **Empty families:** **E** (output_constraint (system-prompt injection)); **G** (state-machine rules (multi-turn gathering)); **H** (output-shaping (agent communication style)).
  _Reason_: these require the full agent harness (live LLM + DB + tool execution) and aren't yet wired in this lib. The 500-spec browser corpus at `tests/tier4_corpus/` covers these paths against the running app.

- **No agent-runner cases yet.** All cases are either pure-engine (`runner_kind=engine`, no LLM) or compile-only (`runner_kind=compile`, live LLM but mostly short-circuited by `_pre_check`). Live agent integration is the next layer.

- **Input shapes not yet exercised** (Doc 9 § 4 enumerates 25): S3, S4, S5, S6, S7, S8, S9, S10, S12, S13, S14, S15….
  _Reason_: many of these shapes (S4 piecemeal, S6 ambiguous time, S15 emoji, S19 code-switched) only matter once the live agent runs end-to-end.


## Architecture posture — explicit non-support

These cases are negative-space evidence: the system is honest about what it *can't* express, and that honesty is enforceable as tests.

| Case | Pattern | Disposition | Status |
| --- | --- | --- | --- |
| `EV-DIS-001` | E11 cross-conversation lookup → CompileFailure | Cross-conversation customer/booking history is not tracked — compile must refuse | CHARACTERIZED-PASS |
| `EV-DIS-002` | E17 rules evaluate independently — order-invariant under swap | Both rules fire independently; swapping rule list order must yield same result. | PASS |
| `EV-DIS-003` | E18 frequency throttle (4th booking in 24h) → CompileFailure | Frequency-based throttling needs cross-conversation history we don't track. | CHARACTERIZED-PASS |
| `EV-DIS-004` | E19 random sampling (block 20% of new-customer bookings) → CompileFailure | Guardrails must be deterministic from the customer's perspective. | CHARACTERIZED-PASS |
| `EV-DIS-005` | E20 side-effect (notify dispatcher) → CompileFailure | Rule enforcement is pure block/pass; side effects belong in tool bodies. | CHARACTERIZED-PASS |

## Cases by family

### Family A — pure typed rules (deterministic engine path)

_14 / 14 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-A-001 | G1 | S1 | PASS | Sunday plumbing → blocked by hours | outcome=blocked; primary='Standard hours'; fired=['Standard hours'] |
| EV-A-002 | G1 | S1 | PASS | Tuesday 10 AM plumbing → accepted | outcome=accepted |
| EV-A-003 | G1 | S1 | PASS | Tuesday 7 PM (after close) → blocked | outcome=blocked; primary='Standard hours'; fired=['Standard hours'] |
| EV-A-004 | G1 | S2 | PASS | No date provided → needs_info on `date` | outcome=needs_info; primary='Standard hours'; fired=['Standard hours']; needs=['date'] |
| EV-A-005 | G1 | S1 | PASS | In-area ZIP → accepted | outcome=accepted |
| EV-A-006 | G1 | S1 | PASS | Out-of-area ZIP → blocked | outcome=blocked; primary='Service area'; fired=['Service area'] |
| EV-A-007 | G1 | S1 | PASS | Explicitly-denied ZIP → blocked (deny-list precedence) | outcome=blocked; primary='Service area'; fired=['Service area'] |
| EV-A-008 | G1 | S1 | PASS | Allowed trade (hvac) → accepted | outcome=accepted |
| EV-A-009 | G1 | S1 | PASS | Disallowed trade (roofing) → blocked | outcome=blocked; primary='Allowed trades'; fired=['Allowed trades'] |
| EV-A-010 | G1 | S1 | PASS | Renter (homeowner_required=true) → blocked | outcome=blocked; primary='Homeowner required'; fired=['Homeowner required'] |
| EV-A-011 | G3 | S2 | PASS | is_homeowner unset → needs_info | outcome=needs_info; primary='Homeowner required'; fired=['Homeowner required']; needs=['is_homeowner'] |
| EV-A-012 | G1 | S1 | PASS | HVAC same-day → blocked by 48h lead time | outcome=blocked; primary='48h lead time'; fired=['48h lead time'] |
| EV-A-013 | G1 | S1 | PASS | HVAC same-day with is_emergency=true → bypassed → accepted | outcome=accepted |
| EV-A-014 | G1 | S1 | PASS | Plumbing same-day (lead-time scoped to hvac) → accepted | outcome=accepted |

### Family ADV — adversarial input shapes (S10–S25)

_6 / 6 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-ADV-001 | G2 | S20 | PASS | S20 profanity in reported issue → engine blocks via regex | outcome=blocked; primary='Profanity escalate'; fired=['Profanity escalate'] |
| EV-ADV-002 | G5 | S25 | CHARACTERIZED-PASS | S25 PII targeting → compile lint refuses | compile_kind=failure; reason='Source prompt targets a specific person / address (PII) — refused on policy.' |
| EV-ADV-003 | G5 | S25 | CHARACTERIZED-PASS | S25 protected-class targeting → compile lint refuses | compile_kind=failure; reason='Source prompt looked like protected-class targeting — refused on policy.' |
| EV-ADV-004 | G5 | S25 | CHARACTERIZED-PASS | S25 trivially-true ('always book any appointment') → lint re | compile_kind=failure; reason='Trivially-true / trivially-false rule has no enforcement value.' |
| EV-ADV-005 | G5 | S11 | CHARACTERIZED-PASS | S11 prompt-injection attempt → compile refuses (LLM-side) | compile_kind=failure; reason='Prompt-injection / role-override attempt — refused.' |
| EV-ADV-006 | G5 | S25 | CHARACTERIZED-PASS | S25 vague modifier ('try to be helpful') → compile refuses | compile_kind=failure; reason='Vague modifier without concrete intent — refuse on ambiguity.' |

### Family B — group-scoped triggers via conditional_block

_5 / 5 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-B-001 | G2 | S1 | PASS | Plumbing at 5 PM → blocked by 'no plumbing after 4 PM' | outcome=blocked; primary='Late plumbing block'; fired=['Late plumbing block'] |
| EV-B-002 | G2 | S1 | PASS | HVAC at 5 PM (rule scoped to plumbing) → accepted | outcome=accepted |
| EV-B-003 | G2 | S1 | PASS | Plumbing at 10 AM (before cutoff) → accepted | outcome=accepted |
| EV-B-004 | G2 | S1 | PASS | Pre-1978 home → blocked | outcome=blocked; primary='Pre-1978 home block'; fired=['Pre-1978 home block'] |
| EV-B-005 | G2 | S1 | PASS | 2010-built home (post-1978) → accepted | outcome=accepted |

### Family C — preconditioned rules (block-unless-state-X)

_3 / 3 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-C-001 | G3 | S1 | PASS | HOA-governed, is_homeowner=true → precondition met → accepte | outcome=accepted |
| EV-C-002 | G3 | S1 | PASS | HOA-governed, is_homeowner=false → precondition not met → bl | outcome=blocked; primary='HOA approval gate'; fired=['HOA approval gate'] |
| EV-C-003 | G3 | S1 | PASS | Not HOA-governed → trigger doesn't fire → accepted | outcome=accepted |

### Family D — hybrid LLM-judge rules (deterministic via FakeJudgeClient)

_5 / 5 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-D-001 | G6 | S1 | CHARACTERIZED-PASS | Late plumbing + judge=emergency → accepted | outcome=accepted |
| EV-D-002 | G6 | S1 | CHARACTERIZED-PASS | Late plumbing + judge=non-emergency → blocked | outcome=blocked; primary='Late-day emergency bypass'; fired=['Late-day emergency bypass'] |
| EV-D-003 | G6 | S1 | CHARACTERIZED-PASS | Early plumbing — judge never queried (short-circuit) | outcome=accepted |
| EV-D-004 | G6 | S1 | CHARACTERIZED-PASS | Judge classifies contractor language → block | outcome=blocked; primary='Contractor detection'; fired=['Contractor detection'] |
| EV-D-005 | G6 | S1 | CHARACTERIZED-PASS | Judge says not-contractor → accepted | outcome=accepted |

### Family DIS — architecture-disposition (E11/E17/E18/E19/E20 — explicit non-support)

_5 / 5 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-DIS-001 | G5 | S25 | CHARACTERIZED-PASS | E11 cross-conversation lookup → CompileFailure | compile_kind=failure; reason="Cross-conversation customer / booking history isn't part of the rule engine's sc" |
| EV-DIS-002 | G4 | S1 | PASS | E17 rules evaluate independently — order-invariant under swa | outcome=blocked; primary='Standard hours'; fired=['Standard hours'] |
| EV-DIS-003 | G5 | S25 | CHARACTERIZED-PASS | E18 frequency throttle (4th booking in 24h) → CompileFailure | compile_kind=failure; reason="Cross-conversation customer / booking history isn't part of the rule engine's sc" |
| EV-DIS-004 | G5 | S25 | CHARACTERIZED-PASS | E19 random sampling (block 20% of new-customer bookings) → C | compile_kind=failure; reason="Random / probabilistic sampling rules can't be expressed — guardrails must be de" |
| EV-DIS-005 | G5 | S25 | CHARACTERIZED-PASS | E20 side-effect (notify dispatcher) → CompileFailure | compile_kind=failure; reason='Rule enforcement is pure block / pass; side effects belong in tool bodies, not t' |

### Family EX — exotic-but-supported patterns (E1–E10)

_10 / 10 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-EX-001 | G2 | S1 | PASS | E1 too-far-out booking → blocked via gt(args.days_out, 90) | outcome=blocked; primary='Far-future block'; fired=['Far-future block'] |
| EV-EX-002 | G2 | S1 | PASS | E2 negation: weekend booking that ISN'T maintenance → blocke | outcome=blocked; primary='Weekend non-maintenance block'; fired=['Weekend non-maintenance block'] |
| EV-EX-003 | G2 | S1 | PASS | E2 negation: weekend MAINTENANCE → accepted (escape) | outcome=accepted |
| EV-EX-004 | G2 | S1 | PASS | E3 regex on reported_issue → block when profanity present | outcome=blocked; primary='Profanity escalate'; fired=['Profanity escalate'] |
| EV-EX-005 | G2 | S1 | PASS | E4 contains: address has 'Apt' substring → block (likely ren | outcome=blocked; primary='Apartment heuristic'; fired=['Apartment heuristic'] |
| EV-EX-006 | G2 | S1 | PASS | E5 nested any_of/all_of: HVAC at 3:30 PM → blocked | outcome=blocked; primary='Late-day nested'; fired=['Late-day nested'] |
| EV-EX-007 | G4 | S1 | PASS | E6 contradictory rule set ('only Mon' + 'only Wed' for hvac) | outcome=blocked; primary='Only-Wed HVAC'; fired=['Only-Mon HVAC', 'Only-Wed HVAC'] |
| EV-EX-008 | G6 | S1 | CHARACTERIZED-PASS | E7 judge-only rule: judge says 'offensive' → block | outcome=blocked; primary='Offensive escalate'; fired=['Offensive escalate'] |
| EV-EX-009 | G6 | S1 | CHARACTERIZED-PASS | E8 composed judges: any_of[offensive, threatening] → block o | outcome=blocked; primary='Composed judges'; fired=['Composed judges'] |
| EV-EX-010 | G3 | S1 | PASS | E9 override-by-precondition: large-job rule only fires when  | outcome=accepted |

### Family F — multi-rule aggregation + outcome precedence

_4 / 4 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-F-001 | G4 | S1 | PASS | Sunday + out-of-area ZIP → both rules fire; hours wins (prio | outcome=blocked; primary='Standard hours'; fired=['Standard hours', 'Service area'] |
| EV-F-002 | G4 | S1 | PASS | Block+pass mix: out-of-area + valid trade → only zip rule fi | outcome=blocked; primary='Service area'; fired=['Service area'] |
| EV-F-003 | G4 | S1 | PASS | Two passes + one block (group rule) → block surfaces | outcome=blocked; primary='Late plumbing block'; fired=['Late plumbing block'] |
| EV-F-004 | G4 | S1 | PASS | All three rules pass → accepted | outcome=accepted |


## Coverage matrix — Family × InputShape

| family ↓ / input_shape → | S1 | S2 | S11 | S20 | S25 |
| --- | --- | --- | --- | --- | --- |
| A | 12 | 2 | · | · | · |
| ADV | · | · | 1 | 1 | 4 |
| B | 5 | · | · | · | · |
| C | 3 | · | · | · | · |
| D | 5 | · | · | · | · |
| DIS | 1 | · | · | · | 4 |
| EX | 10 | · | · | · | · |
| F | 4 | · | · | · | · |

## Coverage by Group (eval machinery exercised)

| Group | Description | Cases |
| --- | --- | --- |
| G1 | engine correctness (operators, evaluators) | 13 |
| G2 | expression composition (nested all_of/any_of/not, regex, contains) | 12 |
| G3 | state-machine integrity (needs_info, mutation) | 5 |
| G4 | multi-rule aggregation (priority, audit completeness) | 6 |
| G5 | compile-step structural correctness | 9 |
| G6 | LLM judge mechanism (composition, short-circuit) | 7 |
| G7 | agent rule-citation behavior | · |
| G8 | end-to-end multi-turn conversation | · |
| G9 | compile-step semantic accuracy | · |
| G10 | adversarial & edge cases | · |

## Coverage by runner kind

| Runner | Cases | Notes |
| --- | --- | --- |
| compile | 9 | compile-step — most cases short-circuit through `_pre_check` (no LLM call) |
| engine | 43 | pure deterministic — `RuleEngine.check()` directly, optional FakeJudgeClient |
