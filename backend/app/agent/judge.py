"""LLM-backed judge for the `llm_judge` operator.

Pydantic-AI agent on the cheap/fast model (Haiku) that answers a single
yes/no question about a snippet. Used by the rule engine via
`EvalContext.judge`. Cached per `EvalContext` so repeated lookups in the same
turn don't re-call the LLM.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from pydantic_ai import Agent

from app.agent.openrouter import judge_model

log = logging.getLogger(__name__)

_SYSTEM = """\
You answer yes/no questions about a piece of customer-supplied text.
Return ONLY "yes" or "no" (lowercase, no punctuation, no explanation).
"""


class LLMJudge:
    """Synchronous-by-design judge — the engine calls .judge(value, question)
    inside its evaluator loop.

    The engine is sync but is invoked from an async FastAPI handler, which
    means the calling thread already has a running asyncio event loop.
    Pydantic-AI's `Agent.run_sync()` internally calls `asyncio.run()`, which
    raises if you're already inside a loop. We sidestep this by running
    the agent on a fresh thread that gets its own loop, and blocking the
    caller on the thread's result. Bounded by `_TIMEOUT_S` so a hung
    upstream model can't stall the engine forever.
    """

    _TIMEOUT_S: float = 20.0

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

        result_holder: dict[str, Any] = {}

        def _run() -> None:
            try:
                result_holder["result"] = self._agent.run_sync(prompt)
            except Exception as exc:  # network blip / model hiccup
                result_holder["error"] = exc

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=self._TIMEOUT_S)

        if "error" in result_holder:
            log.warning(
                "judge: model error on question=%r — defaulting to no",
                question[:60],
                exc_info=result_holder["error"],
            )
            return False
        if "result" not in result_holder:
            log.warning(
                "judge: timeout after %ss on question=%r — defaulting to no",
                self._TIMEOUT_S,
                question[:60],
            )
            return False

        out = (result_holder["result"].output or "").strip().lower()
        return out.startswith("y")
