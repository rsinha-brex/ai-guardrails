# Guardrail Evals Report
Generated: 2026-05-28T03:52:08.959374+00:00

## Headline

**✅ All green** — 1 cases registered.

| Total | PASS | CHARACTERIZED-PASS | FAIL |
| --- | --- | --- | --- |
| 1 | 1 | 0 | 0 |

## Spec compliance (take-home § 3)

| Spec requirement | Met? | Evidence |
| --- | --- | --- |
| Cover ≥3 distinct rule types | ❌ | 0 types exercised: (none) |
| Block + pass cases | ❌ | blocked seen: False; accepted seen: False |
| Single-command runnable | ✅ | `uv run pytest tests/eval -q` |
| Clear pass/fail output | ✅ | pytest summary + tables in this report |

## Strengths — what the eval demonstrates the system enforces

_(no strengths yet — no cases registered)_

## Gaps & limitations — what's not yet covered

- **Empty families:** **A** (pure typed rules (deterministic engine path)); **B** (group-scoped triggers via conditional_block); **C** (preconditioned rules (block-unless-state-X)); **D** (hybrid LLM-judge rules (deterministic via FakeJudgeClient)); **E** (output_constraint (system-prompt injection)); **F** (multi-rule aggregation + outcome precedence); **G** (state-machine rules (multi-turn gathering)); **H** (output-shaping (agent communication style)); **EX** (exotic-but-supported patterns (E1–E10)); **DIS** (architecture-disposition (E11/E17/E18/E19/E20 — explicit non-support)); **ADV** (adversarial input shapes (S10–S25)).
  _Reason_: these require the full agent harness (live LLM + DB + tool execution) and aren't yet wired in this lib. The 500-spec browser corpus at `tests/tier4_corpus/` covers these paths against the running app.

- **No agent-runner cases yet.** All cases are either pure-engine (`runner_kind=engine`, no LLM) or compile-only (`runner_kind=compile`, live LLM but mostly short-circuited by `_pre_check`). Live agent integration is the next layer.

- **Input shapes not yet exercised** (Doc 9 § 4 enumerates 25): S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13….
  _Reason_: many of these shapes (S4 piecemeal, S6 ambiguous time, S15 emoji, S19 code-switched) only matter once the live agent runs end-to-end.


## Architecture posture — explicit non-support

_(no disposition cases registered)_

## Compile pipeline (Group 9 — live LLM, end-to-end)

_(no Group 9 cases registered yet — register a case via `runner_kind="compile_and_probe"` to see live LLM compile results here)_

## Cases by family

### Family AGT — 

_1 / 1 passing._

| ID | Group | Shape | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| EV-AGT-001 | G7 | S1 | PASS | Scripted Sunday booking → engine blocks → audit captures | (no evidence) |


## Coverage matrix — Family × InputShape

| family ↓ / input_shape → | S1 |
| --- | --- |
| AGT | 1 |

## Coverage by Group (eval machinery exercised)

| Group | Description | Cases |
| --- | --- | --- |
| G1 | engine correctness (operators, evaluators) | · |
| G2 | expression composition (nested all_of/any_of/not, regex, contains) | · |
| G3 | state-machine integrity (needs_info, mutation) | · |
| G4 | multi-rule aggregation (priority, audit completeness) | · |
| G5 | compile-step structural correctness | · |
| G6 | LLM judge mechanism (composition, short-circuit) | · |
| G7 | agent rule-citation behavior | 1 |
| G8 | end-to-end multi-turn conversation | · |
| G9 | compile-step semantic accuracy | · |
| G10 | adversarial & edge cases | · |

## Coverage by runner kind

| Runner | Cases | Notes |
| --- | --- | --- |
| agent_unit | 1 |  |
