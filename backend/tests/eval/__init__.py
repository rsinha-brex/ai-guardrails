"""Guardrail Evals — the deliverable eval library.

A focused, pytest-runnable, live-LLM eval suite organized around the rule-pattern
taxonomy in `docs/exotic_rules_and_eval_catalog.md` (8 families, 25 input shapes,
10 eval groups). Each case is a typed `EvalCase` with concrete `Assertion`
predicates; the conftest auto-discovers cases from `cases/*.py` and parametrizes
one pytest function per family.

Run:
  uv run pytest tests/eval -q                        # all cases
  uv run pytest tests/eval -m deterministic -q       # gating subset (~1 sec)
"""
