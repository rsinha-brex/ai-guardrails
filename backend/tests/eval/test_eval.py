"""Pytest entry points — one test function per family.

The conftest auto-parametrizes each function with its registered cases. The
`run_and_record` helper executes the case and asserts on the outcome; failed
assertions fail the test with a clear reason that points at the EvalCase id.
"""
from __future__ import annotations

import os

import pytest

from tests.eval.framework import EvalCase, evaluate_assertions, run_case
from tests.eval.taxonomy import DETERMINISTIC_GROUPS

from tests.eval._results import record as _record


def _execute(case: EvalCase) -> None:
    deterministic = case.group in DETERMINISTIC_GROUPS
    # Disposition + some exotic cases are short-circuit-rejected by
    # compile_agent._pre_check before any LLM call, so they run deterministically
    # even when OPENROUTER_API_KEY is unset. For the genuinely live cases, we
    # skip cleanly when there's no key so a quick `pytest tests/eval` still
    # produces clean output without network access.
    if case.runner_kind == "engine":
        ev = run_case(case)
        ok, results = evaluate_assertions(case, ev)
        _record(case, ev, ok, results)
        if not ok:
            failures = [r.reason for r in results if not r.ok]
            pytest.fail(
                f"{case.id} ({case.title}) failed:\n  - " + "\n  - ".join(failures),
                pytrace=False,
            )
        return

    # compile / agent cases — run with samples and threshold-gating.
    n = max(1, case.samples)
    pass_count = 0
    last_failures: list[str] = []
    for i in range(n):
        try:
            ev = run_case(case, sample_index=i)
        except Exception as exc:  # network failure / LLM hiccup
            if not os.environ.get("OPENROUTER_API_KEY"):
                pytest.skip(f"{case.id}: no OPENROUTER_API_KEY and live LLM unreachable")
            raise
        ok, results = evaluate_assertions(case, ev)
        _record(case, ev, ok, results, sample_idx=i)
        if ok:
            pass_count += 1
        else:
            last_failures = [r.reason for r in results if not r.ok]
            # If the failure was an unhelpful error from a missing-key path,
            # skip rather than fail the whole suite.
            if ev.error and "Connection error" in (ev.error or "") and not os.environ.get("OPENROUTER_API_KEY"):
                pytest.skip(f"{case.id}: live LLM unreachable and no API key")
    rate = pass_count / n
    if rate < case.threshold:
        pytest.fail(
            f"{case.id} ({case.title}) characterization-fail: "
            f"{pass_count}/{n} samples passed (threshold {case.threshold}).\n"
            f"  last failures: " + "; ".join(last_failures),
            pytrace=False,
        )


# One test function per family — conftest.pytest_generate_tests parametrizes them.

@pytest.mark.deterministic
def test_family_a(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.deterministic
def test_family_b(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.deterministic
def test_family_c(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.probabilistic
def test_family_d(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.probabilistic
def test_family_e(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.deterministic
def test_family_f(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.probabilistic
def test_family_g(case: EvalCase) -> None:
    _execute(case)


@pytest.mark.probabilistic
def test_family_h(case: EvalCase) -> None:
    _execute(case)


def test_family_ex(case: EvalCase) -> None:
    _execute(case)


def test_family_dis(case: EvalCase) -> None:
    _execute(case)


def test_family_adv(case: EvalCase) -> None:
    _execute(case)
