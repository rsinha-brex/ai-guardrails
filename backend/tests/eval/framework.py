"""EvalCase, Assertion protocol, and runner harness.

Cases are dataclasses with assertions. Runners (engine / compile / agent) take
a case + dependencies and produce an `Evidence` record; assertions read the
evidence and return PASS / FAIL with a one-line reason.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

from app.engine.engine import CheckResult, RuleEngine, RuleSnapshot
from app.engine.expressions import FakeJudgeClient
from app.schemas.conversation_state import ConversationState

from tests.eval.taxonomy import Family, Group, InputShape


# --------------------------------------------------------------------------- #
# Evidence — what the runner records, what assertions read
# --------------------------------------------------------------------------- #


@dataclass
class Evidence:
    case_id: str
    runner_kind: str
    sample_index: int = 0
    # Engine outcomes
    check_result: CheckResult | None = None
    # Compile outcomes
    compile_kind: str | None = None  # "compiled" | "compiled_draft" | "failure"
    compile_rule: Any = None
    compile_failure: Any = None
    # Agent outcomes
    response_text: str = ""
    audit_events: list[dict] = field(default_factory=list)
    state_after: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[str] = field(default_factory=list)
    # compile_and_probe runner: per-probe results
    probe_results: list[dict[str, Any]] = field(default_factory=list)
    # Anything else
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# --------------------------------------------------------------------------- #
# Assertion protocol + concrete assertions
# --------------------------------------------------------------------------- #


@dataclass
class AssertionResult:
    ok: bool
    reason: str

    @classmethod
    def passes(cls, msg: str = "") -> "AssertionResult":
        return cls(True, msg)

    @classmethod
    def fails(cls, msg: str) -> "AssertionResult":
        return cls(False, msg)


@runtime_checkable
class Assertion(Protocol):
    def check(self, ev: Evidence) -> AssertionResult: ...


def _outcome_or_none(ev: Evidence) -> str | None:
    return ev.check_result.outcome if ev.check_result else None


@dataclass
class OutcomeIs:
    value: Literal["accepted", "blocked", "needs_info"]

    def check(self, ev: Evidence) -> AssertionResult:
        got = _outcome_or_none(ev)
        if got == self.value:
            return AssertionResult.passes(f"outcome={got}")
        return AssertionResult.fails(f"expected outcome={self.value}, got {got!r}")


@dataclass
class StatusOneOf:
    values: tuple[str, ...]

    def check(self, ev: Evidence) -> AssertionResult:
        got = _outcome_or_none(ev)
        if got in self.values:
            return AssertionResult.passes(f"outcome={got} ∈ {list(self.values)}")
        return AssertionResult.fails(f"outcome={got!r} not in {list(self.values)}")


@dataclass
class BlockedByRule:
    name_substring: str

    def check(self, ev: Evidence) -> AssertionResult:
        if not ev.check_result or ev.check_result.outcome != "blocked":
            return AssertionResult.fails(f"not blocked (got {_outcome_or_none(ev)!r})")
        names = [fr.rule_name for fr in ev.check_result.fired_rules]
        target = self.name_substring.lower()
        if any(target in n.lower() for n in names):
            return AssertionResult.passes(f"blocked by rule containing {self.name_substring!r}")
        return AssertionResult.fails(
            f"no fired rule contained {self.name_substring!r}; got {names}"
        )


@dataclass
class PrimaryRuleIs:
    name_substring: str

    def check(self, ev: Evidence) -> AssertionResult:
        if not ev.check_result or not ev.check_result.primary_rule_name:
            return AssertionResult.fails("no primary rule")
        if self.name_substring.lower() in ev.check_result.primary_rule_name.lower():
            return AssertionResult.passes(f"primary={ev.check_result.primary_rule_name!r}")
        return AssertionResult.fails(
            f"primary={ev.check_result.primary_rule_name!r} doesn't contain {self.name_substring!r}"
        )


@dataclass
class NeedsInfoFields:
    fields: tuple[str, ...]

    def check(self, ev: Evidence) -> AssertionResult:
        if not ev.check_result or ev.check_result.outcome != "needs_info":
            return AssertionResult.fails(f"not needs_info (got {_outcome_or_none(ev)!r})")
        got = set(ev.check_result.required_fields)
        want = set(self.fields)
        if want.issubset(got):
            return AssertionResult.passes(f"required_fields={sorted(got)}")
        return AssertionResult.fails(
            f"missing fields {sorted(want - got)}; got {sorted(got)}"
        )


@dataclass
class FiredRuleCount:
    expected: int

    def check(self, ev: Evidence) -> AssertionResult:
        if not ev.check_result:
            return AssertionResult.fails("no check result")
        n = len(ev.check_result.fired_rules)
        if n == self.expected:
            return AssertionResult.passes(f"fired_count={n}")
        return AssertionResult.fails(f"expected {self.expected} fired rules, got {n}")


@dataclass
class ResponseContains:
    substring: str
    case_insensitive: bool = True

    def check(self, ev: Evidence) -> AssertionResult:
        text = ev.response_text or ""
        a, b = (text, self.substring)
        if self.case_insensitive:
            a, b = a.lower(), b.lower()
        if b in a:
            return AssertionResult.passes(f"response contained {self.substring!r}")
        return AssertionResult.fails(f"response did not contain {self.substring!r}")


@dataclass
class ResponseDoesNotContain:
    substring: str
    case_insensitive: bool = True

    def check(self, ev: Evidence) -> AssertionResult:
        text = ev.response_text or ""
        a, b = (text, self.substring)
        if self.case_insensitive:
            a, b = a.lower(), b.lower()
        if b not in a:
            return AssertionResult.passes(f"response did not contain {self.substring!r}")
        return AssertionResult.fails(f"response contained forbidden {self.substring!r}")


@dataclass
class ToolCalled:
    name: str

    def check(self, ev: Evidence) -> AssertionResult:
        if self.name in ev.tool_calls:
            return AssertionResult.passes(f"tool {self.name!r} called")
        return AssertionResult.fails(f"tool {self.name!r} not called; saw {ev.tool_calls}")


@dataclass
class AgentDidNotCallTool:
    name: str

    def check(self, ev: Evidence) -> AssertionResult:
        if self.name not in ev.tool_calls:
            return AssertionResult.passes(f"tool {self.name!r} not called (correct)")
        return AssertionResult.fails(f"tool {self.name!r} was called; expected refusal")


@dataclass
class CompileResultKind:
    kind: Literal["compiled", "compiled_draft", "failure"]

    def check(self, ev: Evidence) -> AssertionResult:
        if ev.compile_kind == self.kind:
            return AssertionResult.passes(f"compile_kind={ev.compile_kind}")
        return AssertionResult.fails(
            f"expected compile_kind={self.kind}, got {ev.compile_kind!r}"
        )


@dataclass
class CompileFailureRationaleContains:
    substring: str

    def check(self, ev: Evidence) -> AssertionResult:
        if ev.compile_failure is None:
            return AssertionResult.fails("no compile failure")
        rat = (getattr(ev.compile_failure, "rationale", "") or "").lower()
        if self.substring.lower() in rat:
            return AssertionResult.passes(f"rationale matched {self.substring!r}")
        return AssertionResult.fails(
            f"rationale {rat!r} did not contain {self.substring!r}"
        )


@dataclass
class CompileRuleType:
    """Assert the compiled rule's `rule_type` matches the expected type."""

    expected: str

    def check(self, ev: Evidence) -> AssertionResult:
        if ev.compile_rule is None:
            return AssertionResult.fails("no compile_rule on evidence")
        actual = getattr(ev.compile_rule, "rule_type", None)
        if actual == self.expected:
            return AssertionResult.passes(f"rule_type={actual}")
        return AssertionResult.fails(
            f"expected rule_type={self.expected}, got {actual!r}"
        )


@dataclass
class ProbesAllMatch:
    """For compile_and_probe runs: assert every probe's actual outcome
    matches the expected outcome the case spelled out."""

    def check(self, ev: Evidence) -> AssertionResult:
        if not ev.probe_results:
            return AssertionResult.fails("no probe_results recorded")
        misses = [p for p in ev.probe_results if not p["match"]]
        if not misses:
            return AssertionResult.passes(
                f"{len(ev.probe_results)}/{len(ev.probe_results)} probes matched"
            )
        first = misses[0]
        return AssertionResult.fails(
            f"{len(misses)}/{len(ev.probe_results)} probe(s) missed; "
            f"first miss: expected {first['expect']!r}, got {first['actual']!r} "
            f"(args={first['args']})"
        )


@dataclass
class StateFieldSet:
    field: str
    value: Any = None  # if None, just assert it's set; otherwise assert exact value

    def check(self, ev: Evidence) -> AssertionResult:
        v = ev.state_after.get(self.field)
        if self.value is None:
            return (
                AssertionResult.passes(f"{self.field}={v!r}")
                if v is not None
                else AssertionResult.fails(f"{self.field} not set")
            )
        if v == self.value:
            return AssertionResult.passes(f"{self.field}={v!r}")
        return AssertionResult.fails(f"{self.field}={v!r}, expected {self.value!r}")


# --------------------------------------------------------------------------- #
# EvalCase + registry
# --------------------------------------------------------------------------- #


@dataclass
class EvalCase:
    id: str
    family: Family
    input_shape: InputShape
    group: Group
    title: str
    runner_kind: Literal["engine", "compile", "agent_one_shot", "agent_multi_turn"]
    inputs: dict[str, Any] = field(default_factory=dict)
    rules: list[RuleSnapshot] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    assertions: list[Assertion] = field(default_factory=list)
    samples: int = 1
    threshold: float = 1.0
    notes: str = ""

    @property
    def deterministic(self) -> bool:
        from tests.eval.taxonomy import DETERMINISTIC_GROUPS

        return self.group in DETERMINISTIC_GROUPS


_REGISTRY: list[EvalCase] = []


def register(case: EvalCase) -> EvalCase:
    if any(c.id == case.id for c in _REGISTRY):
        raise ValueError(f"duplicate case id: {case.id}")
    _REGISTRY.append(case)
    return case


def all_cases() -> list[EvalCase]:
    return list(_REGISTRY)


def cases_by_family(family: Family) -> list[EvalCase]:
    return [c for c in _REGISTRY if c.family == family]


def reset_registry() -> None:
    """Test-only: clear the registry between explicit runs."""
    _REGISTRY.clear()


# --------------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------------- #


def run_engine_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Pure engine run — no LLM, deterministic.

    inputs is expected to have keys: tool_name, args, business (optional), current_time.
    state is the conversation state dict.

    If `inputs["swap_rules"]` is True (used by EV-DIS-002 to verify order-
    independence), the engine is run a second time with rules reversed and
    the second outcome is stored in `evidence.extra["swapped_outcome"]`.
    """
    inputs = case.inputs
    tool_name = inputs.get("tool_name", "book_appointment")
    args = inputs.get("args", {})
    business = inputs.get("business") or _DEFAULT_BUSINESS
    current_time = inputs.get("current_time") or _DEFAULT_TIME
    state_obj = ConversationState(**case.state) if case.state else ConversationState()

    judge = inputs.get("judge") or FakeJudgeClient()
    engine = RuleEngine(case.rules, judge=judge)
    result = engine.check(tool_name, args, business, state_obj, current_time)

    extra: dict[str, Any] = {}
    if inputs.get("swap_rules"):
        engine_swapped = RuleEngine(list(reversed(case.rules)), judge=judge)
        swapped = engine_swapped.check(tool_name, args, business, state_obj, current_time)
        extra["swapped_outcome"] = swapped.outcome

    return Evidence(
        case_id=case.id,
        runner_kind="engine",
        sample_index=sample_index,
        check_result=result,
        state_after={k: v for k, v in case.state.items()},
        extra=extra,
    )


async def run_compile_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Compile-step run — calls the real compile LLM."""
    from app.agent.compile_agent import compile_rule
    from app.schemas.rules import CompiledRule, CompileFailure

    prompt = case.inputs.get("prompt", "")
    try:
        result = await compile_rule(prompt)
    except Exception as exc:  # pragma: no cover
        return Evidence(
            case_id=case.id,
            runner_kind="compile",
            sample_index=sample_index,
            error=f"{type(exc).__name__}: {exc}",
        )

    if isinstance(result, CompiledRule):
        kind = "compiled_draft" if result.confidence == "draft" else "compiled"
        return Evidence(
            case_id=case.id,
            runner_kind="compile",
            sample_index=sample_index,
            compile_kind=kind,
            compile_rule=result,
        )
    if isinstance(result, CompileFailure):
        return Evidence(
            case_id=case.id,
            runner_kind="compile",
            sample_index=sample_index,
            compile_kind="failure",
            compile_failure=result,
        )
    return Evidence(
        case_id=case.id,
        runner_kind="compile",
        sample_index=sample_index,
        error=f"unexpected compile result type: {type(result).__name__}",
    )


async def run_compile_and_probe_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Full-pipeline runner: NL prompt → compile_rule (LLM) → install on fresh
    engine → probe with concrete (args, state) tuples → record outcomes.

    Tests the *agent's compile loop end-to-end*, not just the engine in
    isolation. The owner's plain-English description must (a) compile to a
    rule of the correct shape, and (b) actually behave as intended when the
    engine evaluates real bookings against it.

    Case `inputs` shape:
      {
        "prompt": "We're closed on Sundays.",
        "probes": [
          {"args": {...}, "state": {...}, "expect": "blocked" | "accepted" | "needs_info"},
          ...
        ],
      }

    Evidence captures `compile_kind`, `compile_rule`, and a list of probe
    results (one per probe) with the actual outcome and whether it matched.
    """
    from app.agent.compile_agent import compile_rule
    from app.schemas.rules import CompiledRule, CompileFailure, parse_rule

    prompt = case.inputs.get("prompt", "")
    probes = case.inputs.get("probes", []) or []

    try:
        result = await compile_rule(prompt)
    except Exception as exc:  # network blip / LLM hiccup
        return Evidence(
            case_id=case.id,
            runner_kind="compile_and_probe",
            sample_index=sample_index,
            error=f"{type(exc).__name__}: {exc}",
        )

    if isinstance(result, CompileFailure):
        return Evidence(
            case_id=case.id,
            runner_kind="compile_and_probe",
            sample_index=sample_index,
            compile_kind="failure",
            compile_failure=result,
        )
    if not isinstance(result, CompiledRule):
        return Evidence(
            case_id=case.id,
            runner_kind="compile_and_probe",
            sample_index=sample_index,
            error=f"unexpected result type: {type(result).__name__}",
        )

    compile_kind = "compiled_draft" if result.confidence == "draft" else "compiled"

    # Materialize a RuleSnapshot we can install on a fresh engine.
    full_rule_dict = {
        "rule_type": result.rule_type,
        "name": result.name,
        "description": result.description,
        "applies_when_description": result.applies_when_description,
        "applies_to_tools": result.applies_to_tools,
        "enforcement_mode": result.enforcement_mode,
        "priority": result.priority,
        "parameters": result.parameters,
        "source_prompt": result.source_prompt,
    }
    try:
        parsed = parse_rule(full_rule_dict)
    except Exception as exc:
        return Evidence(
            case_id=case.id,
            runner_kind="compile_and_probe",
            sample_index=sample_index,
            compile_kind=compile_kind,
            compile_rule=result,
            error=f"compiled rule failed schema validation: {exc}",
        )

    snapshot = RuleSnapshot(
        id=uuid4(),
        rule_type=parsed.rule_type,
        name=parsed.name,
        parameters=parsed.parameters.model_dump() if hasattr(parsed.parameters, "model_dump") else dict(parsed.parameters),
        applies_to_tools=list(parsed.applies_to_tools or []),
        enforcement_mode=parsed.enforcement_mode,
        priority=parsed.priority,
    )

    judge = case.inputs.get("judge") or FakeJudgeClient()
    engine = RuleEngine([snapshot], judge=judge)

    business = case.inputs.get("business") or _DEFAULT_BUSINESS
    current_time = case.inputs.get("current_time") or _DEFAULT_TIME

    probe_results: list[dict[str, Any]] = []
    for probe in probes:
        args = probe.get("args", {})
        state = probe.get("state", {}) or {}
        expected = probe.get("expect")
        tool_name = probe.get("tool_name", "book_appointment")
        state_obj = ConversationState(**state) if state else ConversationState()
        outcome = engine.check(tool_name, args, business, state_obj, current_time)
        probe_results.append(
            {
                "args": args,
                "expect": expected,
                "actual": outcome.outcome,
                "primary_rule": outcome.primary_rule_name,
                "match": expected is None or outcome.outcome == expected,
            }
        )

    return Evidence(
        case_id=case.id,
        runner_kind="compile_and_probe",
        sample_index=sample_index,
        compile_kind=compile_kind,
        compile_rule=result,
        probe_results=probe_results,
    )


def run_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Dispatch to the right runner for the case kind."""
    if case.runner_kind == "engine":
        return run_engine_case(case, sample_index=sample_index)
    if case.runner_kind == "compile":
        return asyncio.run(run_compile_case(case, sample_index=sample_index))
    if case.runner_kind == "compile_and_probe":
        return asyncio.run(run_compile_and_probe_case(case, sample_index=sample_index))
    raise NotImplementedError(
        f"runner_kind={case.runner_kind!r} not yet wired in this lib"
    )


def evaluate_assertions(case: EvalCase, ev: Evidence) -> tuple[bool, list[AssertionResult]]:
    """Run all assertions on the evidence; return (all_passed, per-assertion results)."""
    results = [a.check(ev) for a in case.assertions]
    return all(r.ok for r in results), results


# --------------------------------------------------------------------------- #
# Default fixtures (kept simple so engine cases don't need a DB)
# --------------------------------------------------------------------------- #


@dataclass
class _Biz:
    id: UUID
    name: str = "Test Biz"
    timezone: str = "America/New_York"
    description: str = ""


_DEFAULT_BUSINESS = _Biz(id=uuid4())
_DEFAULT_TIME = datetime(2026, 6, 15, 14, 0)  # Mon Jun 15 2026 2 PM
