"""Aggregating rule engine. Algorithm in § 7 of the engineering doc.

Aggregation order: needs_info > block > pass. Highest-priority rule wins for
the user-facing block message; all fired rules are reported for audit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.engine.conditional import evaluate_conditional_block
from app.engine.expressions import BusinessLike, JudgeClient
from app.engine.typed_rules import (
    evaluate_typed,
    has_typed_evaluator,
    required_state_fields_for,
)
from app.schemas.rules import (
    ConditionalBlockParameters,
    OutcomeBlock,
    OutcomeNeedsInfo,
    OutcomePass,
)


@dataclass
class RuleSnapshot:
    """Lightweight in-memory rule used by the engine.

    Built from a SQLAlchemy `Rule` row or constructed in tests.
    """

    id: UUID
    rule_type: str
    name: str
    parameters: dict[str, Any]
    applies_to_tools: list[str]
    enforcement_mode: str = "block"
    priority: int = 100
    block_message: str | None = None  # convenience for output_constraint reporting

    def applies(self, tool_name: str) -> bool:
        if not self.applies_to_tools:
            return True
        return tool_name in self.applies_to_tools


@dataclass
class FiredRule:
    rule_id: UUID
    rule_type: str
    rule_name: str
    outcome: str  # block | needs_info
    user_facing_message: str = ""
    internal_reason: str = ""
    required_fields: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    outcome: str  # accepted | blocked | needs_info
    primary_rule_id: UUID | None = None
    primary_rule_type: str | None = None
    primary_rule_name: str | None = None
    user_facing_message: str = ""
    internal_reason: str = ""
    fired_rules: list[FiredRule] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.outcome == "blocked"


class RuleEngine:
    def __init__(self, rules: list[RuleSnapshot], *, judge: JudgeClient | None = None):
        self.rules = rules
        self.judge = judge

    @classmethod
    def for_business(cls, db_rules: list[Any], *, judge: JudgeClient | None = None) -> RuleEngine:
        snapshots = [
            RuleSnapshot(
                id=r.id,
                rule_type=r.rule_type,
                name=r.name,
                parameters=r.parameters,
                applies_to_tools=list(r.applies_to_tools or []),
                enforcement_mode=r.enforcement_mode,
                priority=r.priority,
            )
            for r in db_rules
            if r.is_active
        ]
        return cls(snapshots, judge=judge)

    def check(
        self,
        tool_name: str,
        args: dict[str, Any],
        business: BusinessLike,
        state: Any,
        current_time: datetime,
    ) -> CheckResult:
        blockers: list[tuple[RuleSnapshot, OutcomeBlock]] = []
        needs_info: list[tuple[RuleSnapshot, OutcomeNeedsInfo]] = []

        for rule in self.rules:
            if not rule.applies(tool_name):
                continue
            if rule.rule_type == "output_constraint":
                continue
            outcome = self._evaluate_one(rule, args, state, business, current_time)
            if isinstance(outcome, OutcomeBlock):
                blockers.append((rule, outcome))
            elif isinstance(outcome, OutcomeNeedsInfo):
                needs_info.append((rule, outcome))

        if needs_info:
            all_required: list[str] = []
            seen: set[str] = set()
            for _, n in needs_info:
                for f in n.required_fields:
                    if f not in seen:
                        seen.add(f)
                        all_required.append(f)
            primary_rule, primary_n = max(needs_info, key=lambda b: b[0].priority)
            return CheckResult(
                outcome="needs_info",
                primary_rule_id=primary_rule.id,
                primary_rule_type=primary_rule.rule_type,
                primary_rule_name=primary_rule.name,
                user_facing_message=primary_n.user_facing_message,
                required_fields=all_required,
                fired_rules=[
                    FiredRule(
                        rule_id=r.id,
                        rule_type=r.rule_type,
                        rule_name=r.name,
                        outcome="needs_info",
                        user_facing_message=n.user_facing_message,
                        required_fields=list(n.required_fields),
                    )
                    for r, n in needs_info
                ],
            )

        if blockers:
            primary_rule, primary_b = max(blockers, key=lambda b: b[0].priority)
            return CheckResult(
                outcome="blocked",
                primary_rule_id=primary_rule.id,
                primary_rule_type=primary_rule.rule_type,
                primary_rule_name=primary_rule.name,
                user_facing_message=primary_b.block_message,
                internal_reason=primary_b.internal_reason,
                fired_rules=[
                    FiredRule(
                        rule_id=r.id,
                        rule_type=r.rule_type,
                        rule_name=r.name,
                        outcome="block",
                        user_facing_message=b.block_message,
                        internal_reason=b.internal_reason,
                    )
                    for r, b in blockers
                ],
            )

        return CheckResult(outcome="accepted")

    def required_state_fields(self, tool_name: str) -> list[str]:
        out: list[str] = []
        for rule in self.rules:
            if not rule.applies(tool_name):
                continue
            for f in required_state_fields_for(rule.rule_type, rule.parameters):
                if f not in out:
                    out.append(f)
        return out

    # ----------------------------- internals ---------------------------------

    def _evaluate_one(
        self,
        rule: RuleSnapshot,
        args: dict[str, Any],
        state: Any,
        business: BusinessLike,
        current_time: datetime,
    ):
        if rule.rule_type == "conditional_block":
            params = ConditionalBlockParameters.model_validate(rule.parameters)
            return evaluate_conditional_block(
                params, args, state, business, current_time, judge=self.judge
            )
        if has_typed_evaluator(rule.rule_type):
            return evaluate_typed(rule.rule_type, rule.parameters, args, state, current_time)
        return OutcomePass()
