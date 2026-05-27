"""pytest config + auto-discovery for the eval lib.

Each `cases/*.py` module imports `register` from framework and calls it with
each EvalCase. We then use pytest_generate_tests to parametrize one test
function per family. Markers are applied by group (deterministic vs probabilistic).
"""
from __future__ import annotations

import importlib
import os
import pkgutil
from pathlib import Path

import pytest

from tests.eval import cases as cases_pkg
from tests.eval._results import all_results, record, reset
from tests.eval.framework import (
    Evidence,
    EvalCase,
    all_cases,
    evaluate_assertions,
    reset_registry,
    run_case,
)
from tests.eval.taxonomy import DETERMINISTIC_GROUPS, Family


def _load_env_for_eval() -> None:
    """Load OPENROUTER_API_KEY from the project .env if not already in environ.

    The shared `tests/conftest.py` defaults the var to "" so tier-1 tests
    don't accidentally hit the network. The eval lib's compile-runner cases
    *do* need real keys, so we explicitly read the .env and replace empty
    values. If the .env doesn't exist, compile cases still skip cleanly.
    """
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if not os.environ.get(k):  # treat empty/unset as needing a load
            os.environ[k] = v


_load_env_for_eval()


def pytest_configure(config):
    config.addinivalue_line("markers", "deterministic: case has no LLM dependency")
    config.addinivalue_line("markers", "probabilistic: case calls a real LLM")
    config.addinivalue_line("markers", "needs_llm: case requires OPENROUTER_API_KEY")
    # Force-import every case module so registration happens.
    reset_registry()
    reset()
    for mod in pkgutil.iter_modules(cases_pkg.__path__):
        importlib.import_module(f"tests.eval.cases.{mod.name}")


# Session-level result accumulator. The eval report is built from this.
_RESULTS = all_results  # function alias; report.py reads via this


def _record(case: EvalCase, ev: Evidence, ok: bool, asserts: list, sample_idx: int = 0):
    record(case, ev, ok, asserts, sample_idx=sample_idx)


def pytest_generate_tests(metafunc):
    """Parametrize family tests with their cases."""
    family_param = metafunc.fixturenames and "case" in metafunc.fixturenames
    if not family_param:
        return
    func_name = metafunc.function.__name__
    family = _family_from_func(func_name)
    if family is None:
        return
    cases = [c for c in all_cases() if c.family == family]
    if not cases:
        metafunc.parametrize(
            "case",
            [pytest.param(None, marks=pytest.mark.skip(reason=f"no cases registered for family {family.value}"))],
            ids=[f"empty-{family.value}"],
        )
        return
    metafunc.parametrize("case", cases, ids=[c.id for c in cases])


def _family_from_func(name: str) -> Family | None:
    if not name.startswith("test_family_"):
        return None
    suffix = name[len("test_family_") :].upper()
    try:
        return Family[suffix]
    except KeyError:
        return None


@pytest.fixture(scope="session", autouse=True)
def _emit_report_at_end():
    yield
    from tests.eval.report import write_report

    results = all_results()
    if results:
        write_report(results)


def run_and_record(case: EvalCase) -> bool:
    """Single-sample run, used by deterministic family tests."""
    ev = run_case(case)
    ok, results = evaluate_assertions(case, ev)
    _record(case, ev, ok, results)
    return ok


def run_and_record_sampled(case: EvalCase) -> tuple[bool, float]:
    """Multi-sample probabilistic run; passes if pass_rate >= threshold."""
    n = max(1, case.samples)
    pass_count = 0
    for i in range(n):
        ev = run_case(case, sample_index=i)
        ok, results = evaluate_assertions(case, ev)
        _record(case, ev, ok, results, sample_idx=i)
        if ok:
            pass_count += 1
    rate = pass_count / n
    return rate >= case.threshold, rate
