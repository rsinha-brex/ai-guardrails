"""Bounded expression language used by conditional_block rules.

Recursive Pydantic discriminated union plus a small evaluator. Operators:
- comparisons: eq / neq / gt / gte / lt / lte / in / not_in / contains / matches_regex
- combinators: all_of / any_of / not
- llm_judge — escape hatch that asks an LLM a yes/no question, cached per conversation
"""
from __future__ import annotations

import operator
import re
from datetime import time
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Field-reference resolver
# --------------------------------------------------------------------------- #

FieldRef = str  # "args.x" / "state.x" / "business.x"


def resolve_field(ref: FieldRef, ctx: EvalContext) -> Any:
    if "." not in ref:
        raise ValueError(f"Bad field ref {ref!r}; expected '<scope>.<name>'")
    scope, _, name = ref.partition(".")
    bag: Any
    if scope == "args":
        bag = ctx.args
    elif scope == "state":
        bag = ctx.state
    elif scope == "business":
        bag = ctx.business
    else:
        raise ValueError(f"Unknown scope {scope!r}")
    if isinstance(bag, dict):
        return bag.get(name)
    return getattr(bag, name, None)


# --------------------------------------------------------------------------- #
# Eval context + LLM-judge protocol
# --------------------------------------------------------------------------- #


class JudgeClient(Protocol):
    def judge(self, field_value: Any, question: str) -> bool: ...


class BusinessLike(Protocol):
    """Structural type for the `business` slot in EvalContext.

    The engine only reads identity-shaped fields off of `business`; in
    production it's a SQLAlchemy `Business` row, in tier-1 tests it's a
    bare dataclass. Both satisfy this Protocol.
    """

    @property
    def name(self) -> str: ...
    @property
    def timezone(self) -> str: ...


class FakeJudgeClient:
    """Deterministic judge for tier-1 tests.

    Configured with a dict of (question_substring → bool) so tests can spell out
    behavior without standing up an LLM.
    """

    def __init__(self, answers: dict[str, bool] | None = None):
        self.answers = answers or {}

    def judge(self, field_value: Any, question: str) -> bool:
        for needle, verdict in self.answers.items():
            if needle.lower() in question.lower():
                return verdict
        return False


class EvalContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    args: dict[str, Any] = Field(default_factory=dict)
    # `state` and `business` are genuinely polymorphic at this layer:
    # state is a Pydantic ConversationState in prod and a dict in tests;
    # business is a SQLAlchemy row in prod and a dataclass in tests. The
    # resolver in `resolve_field` handles both via `isinstance(bag, dict)`
    # / getattr fallback, so we leave Any here rather than over-constrain.
    state: Any = None
    business: Any = None
    # Pydantic v2 doesn't accept Protocol classes as field annotations, so
    # we keep Any here and rely on the function-signature annotations
    # below (and on JudgeClient as documentation of the contract).
    judge: Any = None
    judge_cache: dict[tuple[str, str], bool] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Expression nodes — discriminated union by `op`
# --------------------------------------------------------------------------- #


class _OpBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CmpEq(_OpBase):
    op: Literal["eq"] = "eq"
    field: FieldRef
    value: Any


class CmpNeq(_OpBase):
    op: Literal["neq"] = "neq"
    field: FieldRef
    value: Any


class CmpGt(_OpBase):
    op: Literal["gt"] = "gt"
    field: FieldRef
    value: Any


class CmpGte(_OpBase):
    op: Literal["gte"] = "gte"
    field: FieldRef
    value: Any


class CmpLt(_OpBase):
    op: Literal["lt"] = "lt"
    field: FieldRef
    value: Any


class CmpLte(_OpBase):
    op: Literal["lte"] = "lte"
    field: FieldRef
    value: Any


class CmpIn(_OpBase):
    op: Literal["in"] = "in"
    field: FieldRef
    value: list[Any]


class CmpNotIn(_OpBase):
    op: Literal["not_in"] = "not_in"
    field: FieldRef
    value: list[Any]


class CmpContains(_OpBase):
    op: Literal["contains"] = "contains"
    field: FieldRef
    value: str


class CmpRegex(_OpBase):
    op: Literal["matches_regex"] = "matches_regex"
    field: FieldRef
    value: str


class AllOf(_OpBase):
    op: Literal["all_of"] = "all_of"
    children: list[Expression]


class AnyOf(_OpBase):
    op: Literal["any_of"] = "any_of"
    children: list[Expression]


class NotExpr(_OpBase):
    op: Literal["not"] = "not"
    child: Expression


class LLMJudge(_OpBase):
    op: Literal["llm_judge"] = "llm_judge"
    field: FieldRef
    question: str


Expression = Annotated[
    CmpEq | CmpNeq | CmpGt | CmpGte | CmpLt | CmpLte | CmpIn | CmpNotIn | CmpContains | CmpRegex | AllOf | AnyOf | NotExpr | LLMJudge,
    Field(discriminator="op"),
]

# Resolve forward refs
AllOf.model_rebuild()
AnyOf.model_rebuild()
NotExpr.model_rebuild()


# --------------------------------------------------------------------------- #
# Evaluator
# --------------------------------------------------------------------------- #

_CMP = {
    "eq": operator.eq,
    "neq": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


def _coerce_pair(left: Any, right: Any) -> tuple[Any, Any]:
    """Make string-style HH:MM comparisons work alongside ints/floats."""
    if isinstance(left, str) and isinstance(right, str) and ":" in left and ":" in right:
        try:
            return time.fromisoformat(left), time.fromisoformat(right)
        except ValueError:
            pass
    return left, right


def evaluate(expr: Any, ctx: EvalContext) -> bool:
    op = expr.op
    if op in _CMP:
        left = resolve_field(expr.field, ctx)
        if left is None:
            return False
        l, r = _coerce_pair(left, expr.value)
        try:
            return bool(_CMP[op](l, r))
        except TypeError:
            return False
    if op == "in":
        return resolve_field(expr.field, ctx) in expr.value
    if op == "not_in":
        return resolve_field(expr.field, ctx) not in expr.value
    if op == "contains":
        v = resolve_field(expr.field, ctx)
        return isinstance(v, str) and expr.value in v
    if op == "matches_regex":
        v = resolve_field(expr.field, ctx)
        return isinstance(v, str) and re.search(expr.value, v) is not None
    if op == "all_of":
        return all(evaluate(c, ctx) for c in expr.children)
    if op == "any_of":
        return any(evaluate(c, ctx) for c in expr.children)
    if op == "not":
        return not evaluate(expr.child, ctx)
    if op == "llm_judge":
        if ctx.judge is None:
            return False
        v = resolve_field(expr.field, ctx)
        cache_key = (expr.field, expr.question)
        if cache_key not in ctx.judge_cache:
            ctx.judge_cache[cache_key] = bool(ctx.judge.judge(v, expr.question))
        return ctx.judge_cache[cache_key]
    raise ValueError(f"Unknown op {op!r}")


__all__ = [
    "BusinessLike",
    "EvalContext",
    "Expression",
    "FakeJudgeClient",
    "JudgeClient",
    "evaluate",
    "resolve_field",
]
