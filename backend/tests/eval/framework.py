"""EvalCase, Assertion protocol, and runner harness.

Cases are dataclasses with assertions. Runners (engine / compile / agent) take
a case + dependencies and produce an `Evidence` record; assertions read the
evidence and return PASS / FAIL with a one-line reason.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable
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
    def passes(cls, msg: str = "") -> AssertionResult:
        return cls(True, msg)

    @classmethod
    def fails(cls, msg: str) -> AssertionResult:
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
# Agent-runner assertions — read from `ev.tool_calls`,
# `ev.extra["tool_call_args"]`, and `ev.audit_events` populated by the
# agent_unit / agent_e2e runners.
# --------------------------------------------------------------------------- #


@dataclass
class ToolCalledWithArgs:
    """Assert a tool was called with at least the specified args (subset match)."""

    name: str
    args_subset: dict[str, Any]

    def check(self, ev: Evidence) -> AssertionResult:
        pairs = (ev.extra or {}).get("tool_call_args") or []
        for p in pairs:
            if p.get("name") != self.name:
                continue
            actual = p.get("args") or {}
            if all(actual.get(k) == v for k, v in self.args_subset.items()):
                return AssertionResult.passes(
                    f"{self.name} called with {self.args_subset}"
                )
        return AssertionResult.fails(
            f"{self.name} not called with {self.args_subset}; saw {pairs}"
        )


@dataclass
class ToolCallOrder:
    """Assert `ev.tool_calls` contains the given subsequence in order.

    Doesn't require contiguity — `["a", "b"]` matches `[a, x, b]`.
    """

    sequence: list[str]

    def check(self, ev: Evidence) -> AssertionResult:
        i = 0
        for name in ev.tool_calls:
            if i < len(self.sequence) and name == self.sequence[i]:
                i += 1
        if i == len(self.sequence):
            return AssertionResult.passes(f"order {self.sequence} satisfied")
        return AssertionResult.fails(
            f"order {self.sequence} not satisfied; saw {ev.tool_calls}"
        )


@dataclass
class AuditEventEmitted:
    """Assert at least one audit event matches the given filters.

    Each filter is optional; only set ones must match. `fired_rule_substring`
    matches case-insensitively against the audit event's `fired_rule_name`.
    """

    event_type: str
    outcome: str | None = None
    tool_name: str | None = None
    fired_rule_substring: str | None = None

    def check(self, ev: Evidence) -> AssertionResult:
        for e in ev.audit_events:
            if e.get("event_type") != self.event_type:
                continue
            if self.outcome is not None and e.get("outcome") != self.outcome:
                continue
            if self.tool_name is not None and e.get("tool_name") != self.tool_name:
                continue
            if self.fired_rule_substring is not None:
                name = (e.get("fired_rule_name") or "").lower()
                if self.fired_rule_substring.lower() not in name:
                    continue
            return AssertionResult.passes(
                f"audit {self.event_type}/{self.outcome or '*'} matched"
            )
        summary = [
            f"{e.get('event_type')}/{e.get('outcome')}/{e.get('fired_rule_name')}"
            for e in ev.audit_events
        ]
        return AssertionResult.fails(
            f"no audit event matched event_type={self.event_type!r} "
            f"outcome={self.outcome!r} rule_substring={self.fired_rule_substring!r}; "
            f"saw {summary}"
        )


@dataclass
class AuditEventCount:
    """Assert the audit log contains exactly N events of the given type."""

    event_type: str
    expected: int

    def check(self, ev: Evidence) -> AssertionResult:
        n = sum(1 for e in ev.audit_events if e.get("event_type") == self.event_type)
        if n == self.expected:
            return AssertionResult.passes(f"{n} {self.event_type} events")
        return AssertionResult.fails(
            f"expected {self.expected} {self.event_type} events, got {n}"
        )


@dataclass
class FiredRuleNamesContains:
    """Assert each substring appears in at least one fired-rule name across audit events."""

    substrings: list[str]

    def __init__(self, *substrings: str):
        self.substrings = list(substrings)

    def check(self, ev: Evidence) -> AssertionResult:
        seen = [
            (e.get("fired_rule_name") or "")
            for e in ev.audit_events
            if e.get("fired_rule_name")
        ]
        seen_lower = [s.lower() for s in seen]
        missing = [
            s for s in self.substrings if not any(s.lower() in n for n in seen_lower)
        ]
        if not missing:
            return AssertionResult.passes(f"all substrings present in {seen}")
        return AssertionResult.fails(
            f"missing substrings {missing}; fired rule names: {seen}"
        )


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
    runner_kind: Literal[
        "engine",
        "compile",
        "compile_and_probe",
        "agent_unit",
        "agent_e2e",
    ]
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
    model = case.inputs.get("model")  # optional OpenRouter override

    try:
        result = await compile_rule(prompt, model=model)
    except Exception as exc:  # network blip / LLM hiccup
        return Evidence(
            case_id=case.id,
            runner_kind="compile_and_probe",
            sample_index=sample_index,
            error=f"{type(exc).__name__}: {exc}",
            extra={"model": model or "(default)"},
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
                "state": state,
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
        extra={"model": model or "(default — COMPILE_MODEL env)"},
    )


def run_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Dispatch to the right runner for the case kind."""
    if case.runner_kind == "engine":
        return run_engine_case(case, sample_index=sample_index)
    if case.runner_kind == "compile":
        return asyncio.run(run_compile_case(case, sample_index=sample_index))
    if case.runner_kind == "compile_and_probe":
        return asyncio.run(run_compile_and_probe_case(case, sample_index=sample_index))
    if case.runner_kind == "agent_unit":
        return asyncio.run(run_agent_unit_case(case, sample_index=sample_index))
    if case.runner_kind == "agent_e2e":
        return asyncio.run(run_agent_e2e_case(case, sample_index=sample_index))
    raise NotImplementedError(
        f"runner_kind={case.runner_kind!r} not yet wired in this lib"
    )


# --------------------------------------------------------------------------- #
# Agent runners — exercise the full agent path (tool routing, engine,
# audit roundtrip) against either a scripted FunctionModel (deterministic,
# `agent_unit`) or the live LLM (probabilistic, `agent_e2e`).
#
# Both bypass the DB via the `_test_engine` / `_test_business` /
# `_test_audit_sink` hooks on `AgentDeps`, so cases can install a
# `RuleEngine` directly from `RuleSnapshot` fixtures and inspect the audit
# trail without spinning up a database.
# --------------------------------------------------------------------------- #


def _extract_tool_calls(messages: list) -> tuple[list[str], list[dict[str, Any]]]:
    """Walk an `agent.run` message history and pull tool-call names + args.

    Pydantic AI stores tool calls as `ToolCallPart` instances inside
    `ModelResponse.parts`. `ToolCallPart.args` may be a dict or a JSON
    string depending on how the model emitted them — we normalize to dict.
    """
    import json as _json

    from pydantic_ai.messages import ModelResponse, ToolCallPart  # local import

    names: list[str] = []
    pairs: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, ModelResponse):
            continue
        for part in m.parts:
            if isinstance(part, ToolCallPart):
                args = part.args
                if isinstance(args, str):
                    try:
                        args = _json.loads(args)
                    except Exception:
                        args = {"_raw": args}
                names.append(part.tool_name)
                pairs.append({"name": part.tool_name, "args": args or {}})
    return names, pairs


async def run_agent_unit_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Deterministic agent runner — uses Pydantic AI's `FunctionModel` to
    emit a scripted sequence of `ToolCallPart`s, ending with a final
    `TextPart` once the script is exhausted.

    Expected `case.inputs`:
      {
        "message": str,                      # what the customer typed
        "scripted_tool_calls": [             # in order
          (tool_name, args_dict), ...
        ],
        "final_text": str | None,            # assistant reply after last tool
        "current_time": datetime | None,
        "judge": JudgeClient | None,
      }
    """

    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    from app.agent.agent import _system_prompt as _agent_system_prompt
    from app.agent.tools import AgentDeps, all_tools

    message = case.inputs.get("message", "")
    scripted: list[tuple[str, dict[str, Any]]] = list(
        case.inputs.get("scripted_tool_calls") or []
    )
    final_text = case.inputs.get("final_text", "OK.")

    business = case.inputs.get("business") or _DEFAULT_BUSINESS
    current_time = case.inputs.get("current_time") or _DEFAULT_TIME
    judge = case.inputs.get("judge") or FakeJudgeClient()
    engine = RuleEngine(case.rules, judge=judge)

    sink: list[dict[str, Any]] = []
    deps = AgentDeps(
        db=None,
        business_id=business.id,
        conversation_id=uuid4(),
        customer_identifier="eval-customer",
        current_time=current_time,
        judge=judge,
        state=dict(case.state),
        _test_engine=engine,
        _test_business=business,
        _test_audit_sink=sink,
    )

    step = {"i": 0}

    async def model_fn(messages, info: AgentInfo) -> ModelResponse:
        if step["i"] < len(scripted):
            name, args = scripted[step["i"]]
            step["i"] += 1
            return ModelResponse(parts=[ToolCallPart(tool_name=name, args=dict(args))])
        return ModelResponse(parts=[TextPart(content=final_text)])

    agent: Agent[AgentDeps, str] = Agent(
        FunctionModel(model_fn),
        deps_type=AgentDeps,
        tools=all_tools(),
        retries=0,  # see plan §5 risk #6 — auto-retry would skew the script counter
    )
    agent.system_prompt(_agent_system_prompt)

    try:
        result = await agent.run(message, deps=deps)
    except Exception as exc:
        return Evidence(
            case_id=case.id,
            runner_kind="agent_unit",
            sample_index=sample_index,
            error=f"{type(exc).__name__}: {exc}",
            audit_events=sink,
            state_after=dict(deps.state),
        )

    names, pairs = _extract_tool_calls(result.all_messages())
    return Evidence(
        case_id=case.id,
        runner_kind="agent_unit",
        sample_index=sample_index,
        response_text=str(result.output),
        tool_calls=names,
        audit_events=sink,
        state_after=dict(deps.state),
        extra={"tool_call_args": pairs},
    )


async def run_agent_e2e_case(case: EvalCase, *, sample_index: int = 0) -> Evidence:
    """Probabilistic agent runner — uses the real OpenRouter model at the
    case's configured temperature (default 0). Captures tool calls and the
    final response without scripting any model output.

    Expected `case.inputs`:
      {
        "message": str,                      # what the customer typed
        "model": str | None,                 # OpenRouter slug override
        "temperature": float | None,         # default 0
        "current_time": datetime | None,
        "judge": JudgeClient | None,
      }
    """
    import os

    if not os.environ.get("OPENROUTER_API_KEY"):
        # Mirrors compile_and_probe's behavior: skip cleanly if no key.
        return Evidence(
            case_id=case.id,
            runner_kind="agent_e2e",
            sample_index=sample_index,
            error="OPENROUTER_API_KEY unset — skipping live LLM",
        )

    from pydantic_ai import Agent

    from app.agent.agent import _system_prompt as _agent_system_prompt
    from app.agent.openrouter import main_model_for
    from app.agent.tools import AgentDeps, all_tools

    message = case.inputs.get("message", "")
    model_name = case.inputs.get("model")
    temperature = case.inputs.get("temperature", 0)

    business = case.inputs.get("business") or _DEFAULT_BUSINESS
    current_time = case.inputs.get("current_time") or _DEFAULT_TIME
    judge = case.inputs.get("judge") or FakeJudgeClient()
    engine = RuleEngine(case.rules, judge=judge)

    sink: list[dict[str, Any]] = []
    deps = AgentDeps(
        db=None,
        business_id=business.id,
        conversation_id=uuid4(),
        customer_identifier="eval-customer",
        current_time=current_time,
        judge=judge,
        state=dict(case.state),
        _test_engine=engine,
        _test_business=business,
        _test_audit_sink=sink,
    )

    agent: Agent[AgentDeps, str] = Agent(
        main_model_for(model_name, temperature=temperature),
        deps_type=AgentDeps,
        tools=all_tools(),
        retries=2,  # tolerate one transient hiccup; not enough to skew the test
    )
    agent.system_prompt(_agent_system_prompt)

    try:
        result = await agent.run(message, deps=deps)
    except Exception as exc:
        return Evidence(
            case_id=case.id,
            runner_kind="agent_e2e",
            sample_index=sample_index,
            error=f"{type(exc).__name__}: {exc}",
            audit_events=sink,
            state_after=dict(deps.state),
            extra={"model": model_name or "(default — MAIN_MODEL env)"},
        )

    names, pairs = _extract_tool_calls(result.all_messages())
    return Evidence(
        case_id=case.id,
        runner_kind="agent_e2e",
        sample_index=sample_index,
        response_text=str(result.output),
        tool_calls=names,
        audit_events=sink,
        state_after=dict(deps.state),
        extra={
            "tool_call_args": pairs,
            "model": model_name or "(default — MAIN_MODEL env)",
        },
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
