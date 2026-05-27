"""Main agent factory — wires the tools and dynamic system prompt."""
from __future__ import annotations

from datetime import datetime
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


def system_prompt_for(deps: AgentDeps) -> str:
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
