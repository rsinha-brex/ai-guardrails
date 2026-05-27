# Guardrail Evals (`tests/eval/`)

The deliverable eval library for the AI Guardrails take-home (spec § 3).
Single-command, pytest-runnable, organized around the rule-pattern taxonomy
in `docs/exotic_rules_and_eval_catalog.md` (eight families, 25 input shapes,
ten eval groups).

## Run

```bash
cd backend
uv run pytest tests/eval -q                        # full run
uv run pytest tests/eval -m deterministic -q       # gating subset (no LLM)
```

Output:

- pytest's terminal summary (PASS/FAIL per case).
- A markdown report at `tests/eval/results/latest.md` with the spec-compliance
  table, per-family case tables, the (Family × InputShape) coverage matrix,
  and (when probabilistic cases ran) a characterization appendix.
- A JSONL of every recorded result alongside the markdown.

## How cases are organized

Each `cases/*.py` module is a small file that imports the `register` /
`EvalCase` / `Assertion` primitives and registers one case per pattern:

```
cases/
  family_a_typed.py            # pure typed rules (Group 1, deterministic)
  family_b_grouped.py          # group-scoped triggers via conditional_block
  family_c_preconditioned.py   # rules gated by required_precondition
  family_d_judge.py            # llm_judge in trigger expressions (deterministic via FakeJudgeClient)
  family_f_aggregation.py      # multi-rule outcome precedence
  exotic_supported.py          # E1–E10 supported exotic patterns
  adversarial.py               # S10–S25 adversarial input shapes
  architecture_dispositions.py # E11/E17/E18/E19/E20 — patterns the system rejects
```

Empty case modules for Families E (output_constraint), G (state machine),
and H (output-shaping) are kept as placeholders — those exercise multi-turn
agent behavior and live in a future expansion of the lib.

## Adding a case

1. Pick the right family module under `cases/`.
2. Compose your `EvalCase` — give it an ID prefix matching the family
   (`EV-A-`, `EV-B-`, etc.), tag it with `Family`/`Group`/`InputShape`,
   pick a `runner_kind`, set its inputs, and list its assertions.
3. Wrap it in `register(...)` so the conftest auto-discovers it at
   collection time.

```python
register(
    EvalCase(
        id="EV-A-099",
        family=Family.A,
        input_shape=InputShape.S1,
        group=Group.G1,
        title="My new rule scenario",
        runner_kind="engine",
        rules=[my_rule_factory()],
        inputs={"tool_name": "book_appointment", "args": {...}},
        state={"is_homeowner": True},
        assertions=[OutcomeIs("accepted")],
    )
)
```

## Runner kinds

| `runner_kind` | What runs | Network | Cost |
|---|---|---|---|
| `engine` | `RuleEngine.check(...)` directly. Optional `FakeJudgeClient` for `llm_judge` ops. | None | None |
| `compile` | `compile_rule(prompt)` — passes the deterministic `_pre_check` filter, then the LLM, then `_post_validate` lint. Most disposition / adversarial cases bottom-out in `_pre_check` so they're deterministic too. | Sometimes (only if `_pre_check` passes the prompt to the LLM) | Cents per LLM call |
| `agent_one_shot` | Reserved for the agent harness (Family E/G/H). Not yet wired in this lib. | Live LLM | Cents per turn |
| `agent_multi_turn` | Reserved for state-machine flows. Not yet wired in this lib. | Live LLM | Cents per turn |

## Assertions

`framework.py` exports composable assertion dataclasses; combine multiple per
case to make them strict. The most common ones:

| Assertion | Use |
|---|---|
| `OutcomeIs("accepted" \| "blocked" \| "needs_info")` | Strict match on the engine's outcome. |
| `BlockedByRule("substring")` | A fired rule's name contains the substring. |
| `PrimaryRuleIs("substring")` | The user-facing primary rule's name matches. |
| `FiredRuleCount(n)` | Exactly `n` rules fired. |
| `NeedsInfoFields(("is_homeowner",))` | The aggregated needs_info includes these field names. |
| `CompileResultKind("compiled" \| "compiled_draft" \| "failure")` | Compile returned this kind. |
| `CompileFailureRationaleContains("substring")` | Refusal rationale matched. |
| `ResponseContains` / `ResponseDoesNotContain` | For agent-runner cases. |

## Markers

- `@pytest.mark.deterministic` — case has no LLM dependency. Used by
  `pytest -m deterministic` for the gating subset.
- `@pytest.mark.probabilistic` — case calls a real LLM. Skipped automatically
  when `OPENROUTER_API_KEY` is unset and the deterministic `_pre_check` doesn't
  short-circuit the case.

## Architecture-disposition cases

`cases/architecture_dispositions.py` turns Doc 9's negative-space patterns
into real, executable assertions:

- E11 cross-conversation lookups → `compile_rule` returns `CompileFailure`.
- E17 inter-rule chaining → engine produces the same outcome with rules in
  reversed order (verified by the swap-rules path in `framework.run_engine_case`).
- E18 frequency throttling → `_pre_check` rejects the prompt deterministically.
- E19 random sampling → `_pre_check` rejects.
- E20 side-effects → `_pre_check` rejects.

These all run without network access. The deterministic compile-step pre-check
is in `app/agent/compile_agent.py::_pre_check`; the post-LLM lint stays in
`_lint_compiled` as a defense-in-depth net.

## Reading the report

`tests/eval/results/latest.md` is regenerated on every run. The most useful
sections:

- **Summary** — totals and pass/fail counts.
- **Spec compliance** — explicit table mapping the spec's three bullets
  (≥3 rule types, block+pass cases, single-command runnable) to the
  evidence supporting each.
- **Cases by family** — per-case status with one-line evidence quotes.
- **Coverage matrix** — Family × InputShape grid with case counts per cell.

## Implementation notes

- The lib runs against an in-memory engine — no DB, no Supabase, no FastAPI
  app boot. This keeps the eval portable; tier-1 patterns establish the
  same pattern in `tests/tier1_engine/`.
- The 500-spec browser corpus at `tests/tier4_corpus/` is a separate
  *characterization* corpus and is not part of this deliverable.
- Skipped families (`empty-D`, `empty-E`, etc.) appear when no cases register
  for a family — they're informational, not failures.
