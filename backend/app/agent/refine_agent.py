"""Refine-rule agent — proposes a new natural-language prompt + explanation
when a test case fails. The compile step then re-compiles into a CompiledRule.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from app.agent.openrouter import compile_model


class RuleRefinement(BaseModel):
    updated_prompt: str
    explanation: str
    diff_summary: str = ""


SYSTEM_PROMPT = """\
You refine business rules for the AI Guardrails platform.

You will receive:
- The original rule (its source_prompt + description + JSON parameters).
- A failing test case (customer message + expected outcome + actual outcome).
- A short audit excerpt of what fired during the failing run.

Your job: propose a revised natural-language `source_prompt` that, when
re-compiled, would make the failing test pass without breaking the rule's
intent. Also write a one-paragraph explanation aimed at the business owner,
and a short diff_summary (≤ 80 chars) describing what changed.

Return JSON: {"updated_prompt": "...", "explanation": "...", "diff_summary": "..."}.
Only return the JSON, no preamble.
"""


async def refine_rule(
    *,
    source_prompt: str,
    rule_description: str,
    rule_params: dict[str, Any],
    customer_message: str,
    expected: str,
    actual: str,
    audit_excerpt: list[dict[str, Any]],
    agent_response: str,
) -> RuleRefinement:
    prompt = (
        f"# Original rule\nsource_prompt: {source_prompt or '(template-driven; no source)'}\n"
        f"description: {rule_description}\n"
        f"parameters: {json.dumps(rule_params, indent=2)}\n\n"
        f"# Failing test case\ncustomer_message: {customer_message!r}\n"
        f"expected: {expected}\n"
        f"actual: {actual}\n"
        f"agent_response: {agent_response!r}\n\n"
        f"# Audit excerpt\n{json.dumps(audit_excerpt, indent=2)}\n\n"
        f"Propose a revised source_prompt."
    )
    agent: Agent[None, str] = Agent(compile_model(), system_prompt=SYSTEM_PROMPT, output_type=str)
    result = await agent.run(prompt)
    raw = result.output.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return RuleRefinement(
            updated_prompt=source_prompt or "",
            explanation="(could not parse refinement output)",
        )
    return RuleRefinement(
        updated_prompt=payload.get("updated_prompt", source_prompt or ""),
        explanation=payload.get("explanation", ""),
        diff_summary=payload.get("diff_summary", ""),
    )
