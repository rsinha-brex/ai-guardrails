"""pytest config + auto-discovery for the eval lib.

Each `cases/*.py` module imports `register` from framework and calls it with
each EvalCase. We then use pytest_generate_tests to parametrize one test
function per family. Markers are applied by group (deterministic vs probabilistic).
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import sys
from pathlib import Path

import pytest

from tests.eval import cases as cases_pkg
from tests.eval._results import all_results, record, reset
from tests.eval.framework import (
    EvalCase,
    Evidence,
    all_cases,
    evaluate_assertions,
    reset_registry,
    run_case,
)
from tests.eval.taxonomy import Family


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
        return  # families with no registered cases simply don't parametrize
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


# --------------------------------------------------------------------------- #
# Per-case progress output
#
# Pytest's default `-q` mode hides per-test detail. The eval suite has 50+
# parametrized cases with mixed engine / live-LLM runners — visibility of
# what's currently running (and how long it takes) is way more useful than a
# stream of dots. The hook below prints one line per case at call-completion:
#
#   [ 12/ 58] EV-A-001  engine            PASS  0.01s  Sunday plumbing → blocked
#
# Activates automatically unless `-v` or `-s` are supplied (those have their
# own progress) or pytest is being captured by an outer harness (xdist, CI).
# --------------------------------------------------------------------------- #


_progress_state = {"total": 0, "done": 0, "by_id": {}}


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    eval_items = [it for it in items if "tests/eval/test_eval.py" in str(it.fspath)]
    _progress_state["total"] = len(eval_items)
    _progress_state["done"] = 0
    _progress_state["by_id"] = {it.nodeid: it for it in eval_items}


def pytest_report_teststatus(report, config):  # type: ignore[no-untyped-def]
    """Suppress pytest's default per-test status char for eval cases.

    Our `pytest_runtest_logreport` hook already prints a richer per-case line
    (id + title + runner + status + duration). The default `.` / `F` / `s`
    characters from pytest's terminal reporter just add noise on top of that,
    so we return empty short-form strings for any case nodeid we own. The
    long-form string still appears in the failure summary at the end.
    """
    if report.nodeid in _progress_state["by_id"]:
        if report.passed:
            return "passed", "", ""
        if report.skipped:
            return "skipped", "", ""
        if report.failed:
            return "failed", "", ""
    return None


def pytest_runtest_logreport(report):  # type: ignore[no-untyped-def]
    if report.when != "call":
        return
    if report.nodeid not in _progress_state["by_id"]:
        return

    item = _progress_state["by_id"][report.nodeid]
    case = item.callspec.params.get("case") if hasattr(item, "callspec") else None
    if case is None:
        return

    _progress_state["done"] += 1
    idx = _progress_state["done"]
    total = _progress_state["total"]

    if report.passed:
        status = "\033[32mPASS\033[0m"
    elif report.skipped:
        status = "\033[33mSKIP\033[0m"
    else:
        status = "\033[31mFAIL\033[0m"

    runner = case.runner_kind.ljust(18)
    title = case.title[:60]
    duration = f"{report.duration:5.2f}s"

    line = (
        f"[{idx:>3}/{total:>3}] {case.id.ljust(12)} {runner} "
        f"{status}  {duration}  {title}\n"
    )
    sys.stderr.write(line)
    sys.stderr.flush()


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
