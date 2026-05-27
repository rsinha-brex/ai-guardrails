"""conditional_block — uses the expression engine to evaluate a trigger."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.engine.expressions import BusinessLike, EvalContext, JudgeClient, evaluate
from app.schemas.rules import ConditionalBlockParameters, OutcomeBlock, OutcomePass, RuleOutcome


def evaluate_conditional_block(
    params: ConditionalBlockParameters,
    args: dict[str, Any],
    state: Any,
    business: BusinessLike,
    current_time: datetime,
    judge: JudgeClient | None = None,
) -> RuleOutcome:
    ctx = EvalContext(args=args, state=state, business=business, judge=judge)
    if params.required_precondition is not None:
        if not evaluate(params.required_precondition, ctx):
            return OutcomePass()
    if evaluate(params.trigger, ctx):
        return OutcomeBlock(
            block_message=params.block_message,
            internal_reason="Conditional trigger matched",
        )
    return OutcomePass()
