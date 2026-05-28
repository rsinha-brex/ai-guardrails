# Guardrail Evals Report
Generated: 2026-05-28T06:02:13.819907+00:00

## Headline

**⚠️  6 failure(s)** — 44 cases registered.

| Total | PASS | CHARACTERIZED-PASS | FAIL |
| --- | --- | --- | --- |
| 44 | 38 | 0 | 6 |

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

- **`required_precondition` semantics are correct** — the rule short-circuits to pass when the precondition is unmet (the rule simply doesn't apply), and evaluates the trigger when the precondition is met.
  _Supported by_: `EV-C-001, EV-C-002, EV-C-003`


## Gaps & limitations — what's not yet covered

- **Empty families:** **D** (hybrid LLM-judge rules (deterministic via FakeJudgeClient)); **E** (output_constraint (system-prompt injection)); **G** (state-machine rules (multi-turn gathering)); **H** (output-shaping (agent communication style)); **EX** (exotic-but-supported patterns (E1–E10)); **DIS** (architecture-disposition (E11/E17/E18/E19/E20 — explicit non-support)); **ADV** (adversarial input shapes (S10–S25)).
  _Reason_: these require the full agent harness (live LLM + DB + tool execution) and aren't yet wired in this lib. The 500-spec browser corpus at `tests/tier4_corpus/` covers these paths against the running app.

- **No agent-runner cases yet.** All cases are either pure-engine (`runner_kind=engine`, no LLM) or compile-only (`runner_kind=compile`, live LLM but mostly short-circuited by `_pre_check`). Live agent integration is the next layer.

- **Input shapes not yet exercised** (Doc 9 § 4 enumerates 25): S3, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15….
  _Reason_: many of these shapes (S4 piecemeal, S6 ambiguous time, S15 emoji, S19 code-switched) only matter once the live agent runs end-to-end.

- **Currently failing cases:**
  - `EV-G9-001` (Compile 'closed Sundays' → blocks Sun, allows Mon): ERROR: ModelAPIError: Connection error.
  - `EV-G9-002` (Compile 'only ZIPs 32801 32802' → blocks 99999, allows 32801): ERROR: ModelAPIError: Connection error.
  - `EV-G9-003` (Compile 'we do HVAC and plumbing' → blocks roofing, allows hvac): ERROR: ModelAPIError: Connection error.
  - `EV-G9-004` (Compile '48 hours notice' → blocks same-day, allows 3 days out): ERROR: ModelAPIError: Connection error.
  - `EV-G9-005` (Compile 'homeowners only' → blocks renter, allows homeowner): ERROR: ModelAPIError: Connection error.
  - `EV-G9-006` (Compile 'no plumbing after 4 PM' → blocks 5 PM plumbing, allows 10 AM): ERROR: ModelAPIError: Connection error.


## Architecture posture — explicit non-support

_(no disposition cases registered)_

## Compile pipeline (Group 9 — live LLM, end-to-end)

Each row below ran a real OpenRouter compile call against a NL prompt, installed the resulting `CompiledRule` on a fresh `RuleEngine`, and then ran the listed probes against it. This is the only section that validates the *agent's* NL→rule loop end-to-end (vs. families A–F which evaluate hand-written rule fixtures).

| Case | Status | Model | Compiled rule_type | Probes (✓/total) | Title |
| --- | --- | --- | --- | --- | --- |
| `EV-G9-001` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile 'closed Sundays' → blocks Sun, allows Mon |
| `EV-G9-002` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile 'only ZIPs 32801 32802' → blocks 99999, allows 32801 |
| `EV-G9-003` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile 'we do HVAC and plumbing' → blocks roofing, allows h |
| `EV-G9-004` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile '48 hours notice' → blocks same-day, allows 3 days o |
| `EV-G9-005` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile 'homeowners only' → blocks renter, allows homeowner |
| `EV-G9-006` | CHARACTERIZED-FAIL (0/2 samples) | `(default)` | — | 0/0 | Compile 'no plumbing after 4 PM' → blocks 5 PM plumbing, all |

## Cases by family

### Family A — pure typed rules (deterministic engine path)

_14 / 19 passing._

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
| EV-G9-001 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile 'closed Sundays' → blocks Sun, allows Mon | ERROR: ModelAPIError: Connection error. |
| EV-G9-002 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile 'only ZIPs 32801 32802' → blocks 99999, allows 32801 | ERROR: ModelAPIError: Connection error. |
| EV-G9-003 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile 'we do HVAC and plumbing' → blocks roofing, allows h | ERROR: ModelAPIError: Connection error. |
| EV-G9-004 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile '48 hours notice' → blocks same-day, allows 3 days o | ERROR: ModelAPIError: Connection error. |
| EV-G9-005 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile 'homeowners only' → blocks renter, allows homeowner | ERROR: ModelAPIError: Connection error. |

### Family AGT — 

_12 / 12 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-AGT-001 | G7 | S1 | PASS | Scripted Sunday booking → engine blocks → audit captures | (no evidence) |
| EV-AGT-002 | G7 | S1 | PASS | Scripted Tuesday booking → accepted; audit has rule_consider | (no evidence) |
| EV-AGT-003 | G7 | S4 | PASS | State-gather → book: homeowner update precedes booking | (no evidence) |
| EV-AGT-004 | G7 | S2 | PASS | Booking without homeowner state → needs_info | (no evidence) |
| EV-AGT-005 | G7 | S1 | PASS | Out-of-area ZIP → blocked by service_area_zip | (no evidence) |
| EV-AGT-006 | G7 | S1 | PASS | Roofing booking → blocked by services_offered | (no evidence) |
| EV-AGT-007 | G7 | S1 | PASS | Accept with 4 rules installed → 4 rule_considered rows + 1 t | (no evidence) |
| EV-AGT-008 | G7 | S4 | PASS | Emergency state bypasses lead time → same-day HVAC accepted | (no evidence) |
| EV-AGT-009 | G7 | S20 | PASS | Hostile customer → escalate; engine not invoked | (no evidence) |
| EV-AGT-010 | G7 | S1 | PASS | Lookup service area then book → both audited | (no evidence) |
| EV-AGT-011 | G7 | S1 | PASS | Late plumbing → blocked via conditional_block | (no evidence) |
| EV-AGT-012 | G7 | S1 | PASS | check_action dry-run → engine evaluates without committing | (no evidence) |

### Family B — group-scoped triggers via conditional_block

_5 / 6 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-B-001 | G2 | S1 | PASS | Plumbing at 5 PM → blocked by 'no plumbing after 4 PM' | outcome=blocked; primary='Late plumbing block'; fired=['Late plumbing block'] |
| EV-B-002 | G2 | S1 | PASS | HVAC at 5 PM (rule scoped to plumbing) → accepted | outcome=accepted |
| EV-B-003 | G2 | S1 | PASS | Plumbing at 10 AM (before cutoff) → accepted | outcome=accepted |
| EV-B-004 | G2 | S1 | PASS | Pre-1978 home → blocked | outcome=blocked; primary='Pre-1978 home block'; fired=['Pre-1978 home block'] |
| EV-B-005 | G2 | S1 | PASS | 2010-built home (post-1978) → accepted | outcome=accepted |
| EV-G9-006 | G9 | S1 | CHARACTERIZED-FAIL (0/2) | Compile 'no plumbing after 4 PM' → blocks 5 PM plumbing, all | ERROR: ModelAPIError: Connection error. |

### Family C — preconditioned rules (block-unless-state-X)

_3 / 3 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-C-001 | G3 | S1 | PASS | HOA-governed, is_homeowner=true → precondition met → accepte | outcome=accepted |
| EV-C-002 | G3 | S1 | PASS | HOA-governed, is_homeowner=false → precondition not met → bl | outcome=blocked; primary='HOA approval gate'; fired=['HOA approval gate'] |
| EV-C-003 | G3 | S1 | PASS | Not HOA-governed → trigger doesn't fire → accepted | outcome=accepted |

### Family F — multi-rule aggregation + outcome precedence

_4 / 4 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-F-001 | G4 | S1 | PASS | Sunday + out-of-area ZIP → both rules fire; hours wins (prio | outcome=blocked; primary='Standard hours'; fired=['Standard hours', 'Service area'] |
| EV-F-002 | G4 | S1 | PASS | Block+pass mix: out-of-area + valid trade → only zip rule fi | outcome=blocked; primary='Service area'; fired=['Service area'] |
| EV-F-003 | G4 | S1 | PASS | Two passes + one block (group rule) → block surfaces | outcome=blocked; primary='Late plumbing block'; fired=['Late plumbing block'] |
| EV-F-004 | G4 | S1 | PASS | All three rules pass → accepted | outcome=accepted |


## Coverage matrix — Family × InputShape

| family ↓ / input_shape → | S1 | S2 | S4 | S20 |
| --- | --- | --- | --- | --- |
| A | 17 | 2 | · | · |
| AGT | 8 | 1 | 2 | 1 |
| B | 6 | · | · | · |
| C | 3 | · | · | · |
| F | 4 | · | · | · |

## Coverage by Group (eval machinery exercised)

| Group | Description | Cases |
| --- | --- | --- |
| G1 | engine correctness (operators, evaluators) | 13 |
| G2 | expression composition (nested all_of/any_of/not, regex, contains) | 5 |
| G3 | state-machine integrity (needs_info, mutation) | 4 |
| G4 | multi-rule aggregation (priority, audit completeness) | 4 |
| G5 | compile-step structural correctness | · |
| G6 | LLM judge mechanism (composition, short-circuit) | · |
| G7 | agent rule-citation behavior | 12 |
| G8 | end-to-end multi-turn conversation | · |
| G9 | compile-step semantic accuracy | 6 |
| G10 | adversarial & edge cases | · |

## Coverage by runner kind

| Runner | Cases | Notes |
| --- | --- | --- |
| agent_unit | 12 |  |
| compile_and_probe | 6 |  |
| engine | 26 | pure deterministic — `RuleEngine.check()` directly, optional FakeJudgeClient |
