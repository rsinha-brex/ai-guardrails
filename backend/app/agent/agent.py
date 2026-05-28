"""Main agent factory — wires the tools and dynamic system prompt."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from sqlalchemy import select

from app.agent.openrouter import main_model
from app.agent.prompt import build_system_prompt
from app.agent.tools import AgentDeps, all_tools
from app.models import Business, Rule


def _system_prompt(ctx: RunContext[AgentDeps]) -> str:
    return system_prompt_for(ctx.deps)


def build_agent() -> Agent[AgentDeps, str]:
    agent: Agent[AgentDeps, str] = Agent(
        main_model(),
        deps_type=AgentDeps,
        tools=all_tools(),
        retries=4,
    )
    agent.system_prompt(_system_prompt)
    return agent


@dataclass
class _SnapshotRuleAdapter:
    """Wraps a `RuleSnapshot` so `format_rule_catalog` (which expects ORM
    `Rule` row attributes) can render it without crashing under the eval
    lib's test path. Snapshots don't carry `description` /
    `applies_when_description` / `is_active`; we provide safe defaults.
    """

    rule_type: str
    name: str
    parameters: dict[str, Any]
    description: str = ""
    applies_when_description: str = ""
    is_active: bool = True


def system_prompt_for(deps: AgentDeps) -> str:
    # Eval lib path: reuse the engine + business injected on `deps`. No DB
    # access. Snapshots are wrapped so `format_rule_catalog` doesn't crash
    # on missing ORM fields.
    if deps._test_engine is not None:
        rules = [
            _SnapshotRuleAdapter(
                rule_type=r.rule_type,
                name=r.name,
                parameters=r.parameters,
            )
            for r in deps._test_engine.rules
        ]
        return build_system_prompt(
            deps._test_business, rules, current_time=deps.current_time
        )

    business = deps.db.get(Business, deps.business_id)
    rules = (
        deps.db.execute(
            select(Rule)
            .where(Rule.business_id == deps.business_id, Rule.is_active.is_(True))
            .order_by(Rule.priority.desc())
        )
        .scalars()
        .all()
    )
    return build_system_prompt(business, rules, current_time=deps.current_time)
