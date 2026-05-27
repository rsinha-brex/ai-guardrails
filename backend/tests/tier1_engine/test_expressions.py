from __future__ import annotations

import pytest

from app.engine.expressions import EvalContext, FakeJudgeClient, evaluate
from pydantic import TypeAdapter

from app.engine.expressions import Expression


def _expr(payload: dict):
    return TypeAdapter(Expression).validate_python(payload)


# -------------------- comparison operators --------------------


@pytest.mark.parametrize(
    "op,field_value,target,expected",
    [
        ("eq", 5, 5, True),
        ("eq", "a", "b", False),
        ("neq", "a", "b", True),
        ("gt", 6, 5, True),
        ("gt", 5, 5, False),
        ("gte", 5, 5, True),
        ("lt", 4, 5, True),
        ("lte", 5, 5, True),
    ],
)
def test_comparison_operators(op, field_value, target, expected):
    expr = _expr({"op": op, "field": "args.x", "value": target})
    ctx = EvalContext(args={"x": field_value})
    assert evaluate(expr, ctx) is expected


def test_in_and_not_in():
    in_expr = _expr({"op": "in", "field": "args.t", "value": ["a", "b"]})
    not_in = _expr({"op": "not_in", "field": "args.t", "value": ["a", "b"]})
    ctx_a = EvalContext(args={"t": "a"})
    ctx_z = EvalContext(args={"t": "z"})
    assert evaluate(in_expr, ctx_a) is True
    assert evaluate(in_expr, ctx_z) is False
    assert evaluate(not_in, ctx_a) is False
    assert evaluate(not_in, ctx_z) is True


def test_contains_and_regex():
    contains = _expr({"op": "contains", "field": "state.note", "value": "leak"})
    regex = _expr({"op": "matches_regex", "field": "state.note", "value": r"\bemergency\b"})
    ctx_yes = EvalContext(state={"note": "small leak under sink — possible emergency tonight"})
    ctx_no = EvalContext(state={"note": "consultation"})
    assert evaluate(contains, ctx_yes) is True
    assert evaluate(contains, ctx_no) is False
    assert evaluate(regex, ctx_yes) is True
    assert evaluate(regex, ctx_no) is False


def test_time_string_comparison():
    after_4pm = _expr({"op": "gte", "field": "args.time", "value": "16:00"})
    assert evaluate(after_4pm, EvalContext(args={"time": "17:30"})) is True
    assert evaluate(after_4pm, EvalContext(args={"time": "08:00"})) is False


def test_missing_field_is_falsy():
    expr = _expr({"op": "eq", "field": "args.missing", "value": "x"})
    assert evaluate(expr, EvalContext(args={})) is False


# -------------------- combinators --------------------


def test_all_of_short_circuits():
    expr = _expr(
        {
            "op": "all_of",
            "children": [
                {"op": "eq", "field": "args.a", "value": 1},
                {"op": "eq", "field": "args.b", "value": 2},
            ],
        }
    )
    assert evaluate(expr, EvalContext(args={"a": 1, "b": 2})) is True
    assert evaluate(expr, EvalContext(args={"a": 1, "b": 9})) is False


def test_any_of_and_not():
    expr = _expr(
        {
            "op": "any_of",
            "children": [
                {"op": "eq", "field": "args.kind", "value": "x"},
                {"op": "not", "child": {"op": "eq", "field": "args.kind", "value": "y"}},
            ],
        }
    )
    assert evaluate(expr, EvalContext(args={"kind": "x"})) is True
    assert evaluate(expr, EvalContext(args={"kind": "y"})) is False
    assert evaluate(expr, EvalContext(args={"kind": "z"})) is True


# -------------------- llm_judge --------------------


def test_llm_judge_with_fake_client_caches():
    judge = FakeJudgeClient(answers={"emergency": True})
    expr = _expr(
        {"op": "llm_judge", "field": "state.note", "question": "Does this sound like an emergency?"}
    )
    ctx = EvalContext(state={"note": "leak"}, judge=judge)
    assert evaluate(expr, ctx) is True
    # Second eval should hit the cache (we can't observe directly, but verify no exception)
    assert evaluate(expr, ctx) is True
    assert ctx.judge_cache  # populated


def test_llm_judge_without_judge_returns_false():
    expr = _expr(
        {"op": "llm_judge", "field": "state.note", "question": "anything"}
    )
    ctx = EvalContext(state={"note": "leak"}, judge=None)
    assert evaluate(expr, ctx) is False
