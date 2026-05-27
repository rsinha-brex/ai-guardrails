"""Session-level result accumulator — module-level so pytest-loaded conftest
and normally-imported test_eval share the same list.
"""
from __future__ import annotations

from tests.eval.framework import EvalCase, Evidence

_RESULTS: list[dict] = []


def record(case: EvalCase, ev: Evidence, ok: bool, asserts: list, sample_idx: int = 0) -> None:
    _RESULTS.append(
        {
            "id": case.id,
            "family": case.family.value,
            "input_shape": case.input_shape.value,
            "group": int(case.group),
            "title": case.title,
            "runner_kind": case.runner_kind,
            "sample_index": sample_idx,
            "ok": ok,
            "assertions": [{"ok": a.ok, "reason": a.reason} for a in asserts],
            "deterministic": case.deterministic,
            "evidence_summary": _summarize(ev),
            "notes": case.notes,
        }
    )


def all_results() -> list[dict]:
    return list(_RESULTS)


def reset() -> None:
    _RESULTS.clear()


def _summarize(ev: Evidence) -> str:
    parts: list[str] = []
    if ev.check_result:
        parts.append(f"outcome={ev.check_result.outcome}")
        if ev.check_result.primary_rule_name:
            parts.append(f"primary={ev.check_result.primary_rule_name!r}")
        if ev.check_result.fired_rules:
            parts.append(f"fired={[fr.rule_name for fr in ev.check_result.fired_rules]}")
        if ev.check_result.required_fields:
            parts.append(f"needs={ev.check_result.required_fields}")
    if ev.compile_kind:
        parts.append(f"compile_kind={ev.compile_kind}")
        if ev.compile_failure is not None:
            rat = getattr(ev.compile_failure, "rationale", "") or ""
            if rat:
                parts.append(f"reason={rat[:80]!r}")
    if ev.error:
        parts.append(f"ERROR: {ev.error}")
    return "; ".join(parts) or "(no evidence)"
