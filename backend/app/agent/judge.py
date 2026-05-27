"""LLM-backed judge for the `llm_judge` operator.

Pydantic-AI agent on the cheap/fast model (Haiku) that answers a single
yes/no question about a snippet. Used by the rule engine via
`EvalContext.judge`. Cached per `EvalContext` so repeated lookups in the same
turn don't re-call the LLM.
"""
from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from app.agent.openrouter import judge_model

_SYSTEM = """\
You answer yes/no questions about a piece of customer-supplied text.
Return ONLY "yes" or "no" (lowercase, no punctuation, no explanation).
"""


class LLMJudge:
    """Synchronous-by-design judge — the engine calls .judge(value, question)
    inside its evaluator loop, so we run the agent under a fresh event loop
    when we're not already inside one.
    """

    def __init__(self) -> None:
        self._agent: Agent[None, str] = Agent(
            judge_model(), system_prompt=_SYSTEM, output_type=str
        )

    def judge(self, field_value: Any, question: str) -> bool:
        prompt = (
            f"Question: {question}\n"
            f"Text:\n{field_value if field_value is not None else '(empty)'}\n\n"
            "Answer:"
        )
        try:
            import asyncio

            try:
                asyncio.get_running_loop()
                # We're inside a loop; fall through to the async path via run_sync helper.
                # pydantic-ai exposes run_sync for exactly this case.
                result = self._agent.run_sync(prompt)
            except RuntimeError:
                result = self._agent.run_sync(prompt)
        except Exception:
            return False
        out = (result.output or "").strip().lower()
        return out.startswith("y")
