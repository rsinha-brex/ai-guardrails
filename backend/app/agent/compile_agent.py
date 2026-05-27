"""Compile step — natural language rule description → structured CompiledRule.

The agent's output is a discriminated union: it either returns a CompiledRule
that we then post-validate against the rule_type-specific parameter schemas,
or a CompileFailure with clarifying questions.

Few-shot examples are baked into the system prompt — quality of the compile
step matters more than any other LLM call in the system.

Defense-in-depth on adversarial prompts is shared across two layers:

- `_pre_check`: deterministic regex / phrase match on the *raw prompt* before
  invoking the LLM. Catches architecturally-impossible patterns (random
  sampling, frequency throttling, cross-conversation lookups, side effects)
  and policy-prohibited patterns (PII, protected class, prompt injection).
- `_lint_compiled`: deterministic check on the *compiled rule* after the LLM
  runs. Catches structural pathologies the LLM occasionally produces (empty
  service-allow-list, 24/7-with-no-closed-days when the prompt clearly says
  "closed", empty output_constraint instructions). Re-runs the pattern check
  against `source_prompt` as belt-and-suspenders.

Both layers reference the same module-level pattern constants below to
prevent divergence.
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.agent.compile_prompt import SYSTEM_PROMPT
from app.agent.openrouter import compile_model
from app.schemas.rules import CompiledRule, CompileFailure, parse_rule


# --------------------------------------------------------------------------- #
# Shared adversarial-pattern constants
#
# Used by both _pre_check (pre-LLM) and _lint_compiled (post-LLM) so the two
# layers can never drift. All matched against lower-cased prompts.
# --------------------------------------------------------------------------- #

_TRIVIAL_PHRASES: tuple[str, ...] = (
    "always book any",
    "always accept any",
    "approve every booking",
    "approve every appointment",
    "never book anything",
    "never accept any booking",
    "block every booking",
    "block all bookings regardless",
    "always book any appointment regardless",
)

_PII_PATTERNS: tuple[str, ...] = (
    # "from John Smith at 123 Main St." (lowercased before matching)
    r"\bfrom\s+[a-z]+\s+[a-z]+\s+at\s+\d+",
    # "don't book John Smith"
    r"\bdon'?t\s+(?:take|book|service)\s+[a-z]+\s+[a-z]+\b",
)

_PROTECTED_CLASS_PATTERNS: tuple[str, ...] = (
    r"\b(only|just|no|exclude)\s+(men|women|male|female|christians?|muslims?|jews?|"
    r"asians?|whites?|blacks?|hispanics?|gays?|disabled)\b",
    r"\b(men|women|male|female)\s+(homeowners?|customers?|only)\b",
)

_VAGUE_PHRASES: tuple[str, ...] = (
    "try to be helpful",
    "be careful with rules",
    "maybe block weekends if it makes sense",
    "be helpful when",
    "be nice to",
    "use your best judgment",
)

_INJECTION_PHRASES: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore your instructions",
    "ignore prior instructions",
    "from now on, accept",
    "you are now",
    "pretend you are",
    "act as if you are",
    "disregard the above",
)

_SIDE_EFFECT_PHRASES: tuple[str, ...] = (
    "send a slack",
    "slack notification",
    "notify dispatcher",
    "send a webhook",
    "trigger a webhook",
    "alert the team",
    "send an email to",
    "page the on-call",
    "notify the manager",
)

_FREQUENCY_PHRASES: tuple[str, ...] = (
    "another booking",
    "previous booking",
    "other appointment",
    "duplicate booking",
    "another appointment",
)

_FREQUENCY_REGEX = (
    r"\b(\d+(?:st|nd|rd|th)\s+(?:booking|attempt|request)|"
    r"\d+\s*(?:times|attempts|requests)\s+(?:in|within|per))"
)

_RANDOM_PERCENTAGE_REGEX = r"\b\d{1,3}\s*%\s*of\b"
_RANDOM_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "random",
    "verification",
    "additional check",
    "sampl",
)


def _refuse(rationale: str, *clarifications: str) -> CompileFailure:
    return CompileFailure(
        suggested_clarifications=list(clarifications),
        rationale=rationale,
    )


def _match_phrases(text: str, phrases: tuple[str, ...]) -> bool:
    return any(p in text for p in phrases)


def _match_regexes(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text) for p in patterns)


def _check_prompt_for_adversarial_patterns(text: str) -> CompileFailure | None:
    """Shared phrase / regex matchers — used by both pre_check and lint.

    `text` must already be lower-cased. Returns the first matching refusal
    or None if no pattern fires.
    """
    if _match_phrases(text, _TRIVIAL_PHRASES):
        return _refuse(
            "Trivially-true / trivially-false rule has no enforcement value.",
            "An 'always X' or 'never X' rule has no useful effect — what should actually trigger this?",
            "Are there specific conditions (service type, time, customer state) that should narrow it down?",
        )
    if _match_regexes(text, _PII_PATTERNS):
        return _refuse(
            "Source prompt targets a specific person / address (PII) — refused on policy.",
            "Rules can't target a named individual or a specific address — they apply to anyone who matches a condition.",
            "What policy goal are you trying to achieve? We can probably express it as a service-area or eligibility rule instead.",
        )
    if _match_regexes(text, _PROTECTED_CLASS_PATTERNS):
        return _refuse(
            "Source prompt looked like protected-class targeting — refused on policy.",
            "I can't write rules keyed on protected characteristics (gender, race, religion, etc.).",
            "What's the underlying business reason? There's likely a non-protected attribute that captures the same intent.",
        )
    if _match_phrases(text, _INJECTION_PHRASES):
        return _refuse(
            "Prompt-injection / role-override attempt — refused.",
            "That looked like an attempt to override the compiler's instructions; rules describe enforcement conditions, not agent behavior.",
            "What enforcement outcome were you actually trying to achieve?",
        )
    if _match_phrases(text, _VAGUE_PHRASES):
        return _refuse(
            "Vague modifier without concrete intent — refuse on ambiguity.",
            "I need a concrete condition — 'try to be helpful' isn't something the engine can enforce.",
            "Could you describe the *specific* situation you're worried about?",
        )
    return None




def _lint_compiled(rule: CompiledRule) -> CompileFailure | None:
    """Deterministic post-LLM lint.

    Two responsibilities: (1) re-run the shared adversarial-pattern check
    against `source_prompt` as belt-and-suspenders against pre-check misses;
    (2) catch *structural* pathologies the LLM occasionally produces in the
    compiled rule itself (empty service-allow-list, 24/7-with-no-closed-days
    when the prompt clearly says "closed", empty output_constraint instructions).
    """
    src = (rule.source_prompt or "").lower()
    params = rule.parameters or {}

    # 1. Adversarial-pattern catch (shared with _pre_check).
    failure = _check_prompt_for_adversarial_patterns(src)
    if failure is not None:
        return failure

    # 2. services_offered with empty allow-list → trivially blocks everything.
    if rule.rule_type == "services_offered" and not (params.get("allowed_services") or []):
        return _refuse(
            "services_offered with empty allowed_services would block all bookings.",
            "Which service types should we actually offer?",
        )

    # 3. business_hours covering 24/7 with no closed days when the prompt
    # mentions hours — likely an LLM hallucination, not the owner's real hours.
    if rule.rule_type == "business_hours":
        hours = params.get("hours_by_day") or {}
        closed = params.get("closed_days") or []
        all_24 = bool(hours) and all(
            isinstance(v, dict) and v.get("start") == "00:00" and v.get("end") == "23:59"
            for v in hours.values()
        )
        if all_24 and not closed and any(
            kw in src for kw in ("closed", "open", "hours", "until", "after", "before")
        ):
            return _refuse(
                "business_hours covers 24/7 with no closed days — likely a default, not the owner's real hours.",
                "What hours should we actually be open?",
            )

    # 4. output_constraint with empty instruction does nothing.
    if rule.rule_type == "output_constraint":
        instr = (params.get("instruction") or "").strip()
        if not instr:
            return _refuse(
                "output_constraint with empty instruction does nothing.",
                "What should the agent actually say or mention?",
            )

    return None


def _post_validate(raw_rule: dict[str, Any]) -> CompiledRule | CompileFailure:
    """Run the rule_type-specific Pydantic schema against the parameters."""
    try:
        compiled = CompiledRule.model_validate(raw_rule)
    except ValidationError as exc:
        return CompileFailure(
            suggested_clarifications=[
                "I couldn't quite produce a valid rule from that. Could you clarify the wording?",
                f"(Internal validation hint: {exc.errors()[0]['msg']})",
            ],
            rationale="Output failed shape validation",
        )

    full = {
        "rule_type": compiled.rule_type,
        "name": compiled.name,
        "description": compiled.description,
        "applies_when_description": compiled.applies_when_description,
        "applies_to_tools": compiled.applies_to_tools,
        "enforcement_mode": compiled.enforcement_mode,
        "priority": compiled.priority,
        "parameters": compiled.parameters,
        "source_prompt": compiled.source_prompt,
    }
    try:
        parse_rule(full)
    except ValidationError as exc:
        return CompileFailure(
            suggested_clarifications=[
                f"The {compiled.rule_type} parameters didn't quite match. Could you rephrase?",
            ],
            rationale=f"Parameter shape failed: {exc.errors()[0]['msg']}",
        )

    lint_failure = _lint_compiled(compiled)
    if lint_failure is not None:
        return lint_failure
    return compiled


def _pre_check(prompt: str) -> CompileFailure | None:
    """Reject architecturally-impossible or policy-prohibited prompts before
    invoking the LLM.

    Two layers:
    1. Architecturally-impossible patterns (random sampling, frequency
       throttling, side effects) — rejected here because they can't be
       represented in the rule engine's pure block/pass model.
    2. Policy-prohibited / nonsense patterns (PII, protected class, trivially-
       true, vague modifiers, prompt injection) — delegated to the shared
       `_check_prompt_for_adversarial_patterns` so this layer and
       `_lint_compiled` can never drift.
    """
    p = (prompt or "").lower()

    # 1. Random / probabilistic sampling — guardrails must be deterministic.
    if re.search(_RANDOM_PERCENTAGE_REGEX, p) and _match_phrases(p, _RANDOM_CONTEXT_KEYWORDS):
        return _refuse(
            "Random / probabilistic sampling rules can't be expressed — "
            "guardrails must be deterministic from the customer's perspective.",
            "Random or probabilistic blocks aren't supported — what specific signal should trigger this verification?",
            "Is there a customer attribute, request shape, or ZIP we could key on instead of randomness?",
        )

    # 2. Frequency-based throttling — needs cross-conversation history.
    if _match_phrases(p, _FREQUENCY_PHRASES) or re.search(_FREQUENCY_REGEX, p):
        return _refuse(
            "Cross-conversation customer / booking history isn't part of the "
            "rule engine's scope; frequency throttling can't be expressed.",
            "Frequency-based throttling needs the customer's prior bookings, which the engine doesn't track per-customer across conversations.",
            "Could you key on a single-conversation signal instead (state field, current request shape)?",
        )

    # 3. Side effects beyond block/pass — those belong in tool bodies.
    if _match_phrases(p, _SIDE_EFFECT_PHRASES):
        return _refuse(
            "Rule enforcement is pure block / pass; side effects belong in "
            "tool bodies, not the rule engine.",
            "Rules block or pass — they don't trigger external side effects like notifications. Do you want this as a tool integration instead?",
            "What's the underlying enforcement intent (block the booking? warn the customer?) — we can express that as a rule.",
        )

    # 4. Policy / nonsense patterns — shared with _lint_compiled.
    return _check_prompt_for_adversarial_patterns(p)


async def compile_rule(prompt: str) -> CompiledRule | CompileFailure:
    """Run the compile agent against a prompt and post-validate the result.

    A deterministic pre-check rejects architecturally-impossible prompts
    (random sampling, frequency throttling, cross-conversation lookups, side
    effects) before any LLM call.
    """
    pre = _pre_check(prompt)
    if pre is not None:
        return pre

    agent: Agent[None, str] = Agent(compile_model(), system_prompt=SYSTEM_PROMPT, output_type=str)
    try:
        result = await agent.run(prompt)
    except UnexpectedModelBehavior as exc:  # pragma: no cover — runtime LLM hiccup
        return CompileFailure(
            suggested_clarifications=[
                "Something went wrong on my end. Could you rephrase the rule a different way?",
            ],
            rationale=f"Model error: {exc}",
        )

    raw = result.output.strip()
    if raw.startswith("```"):
        # strip code fences if present
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return CompileFailure(
            suggested_clarifications=[
                "The compiler couldn't parse a clean response. Could you rephrase the rule?",
            ],
            rationale="JSON parse failure",
        )

    kind = payload.get("kind")
    if kind == "compiled":
        rule_payload = payload.get("rule", {})
        rule_payload.setdefault("source_prompt", prompt)
        return _post_validate(rule_payload)
    if kind == "failure":
        return CompileFailure(
            suggested_clarifications=payload.get("suggested_clarifications", []),
            rationale=payload.get("rationale", ""),
        )
    return CompileFailure(
        suggested_clarifications=["Could you rephrase that as a single rule statement?"],
        rationale="Unrecognized output shape",
    )
