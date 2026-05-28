"""Rules CRUD — list, create (compiled or prompt), update, delete."""
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.compile_agent import compile_rule
from app.auth import authenticate, get_business
from app.db import get_session
from app.models import Business, Rule, TestCase
from app.schemas.rules import (
    CompiledRule,
    CompileFailure,
    RuleSummary,
    parse_rule,
)

router = APIRouter(prefix="/api/businesses/{business_id}/rules", tags=["rules"])


# --------------------------------------------------------------------------- #
# Request shapes
# --------------------------------------------------------------------------- #


class CreateRuleIn(BaseModel):
    """Create a rule from either a compiled definition or a freeform prompt."""

    compiled: CompiledRule | None = None
    prompt: str | None = None


class UpdateRuleIn(BaseModel):
    name: str | None = None
    description: str | None = None
    applies_when_description: str | None = None
    parameters: dict[str, Any] | None = None
    applies_to_tools: list[str] | None = None
    enforcement_mode: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    source_prompt: str | None = None


class CreateRuleOut(BaseModel):
    rule: RuleSummary | None = None
    failure: CompileFailure | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #





def _validate_against_schema(rule_type: str, parameters: dict[str, Any]) -> None:
    """Run the per-rule-type Pydantic shape against parameters."""
    full = {
        "rule_type": rule_type,
        "name": "_validate",
        "description": "",
        "parameters": parameters,
    }
    try:
        parse_rule(full)
    except Exception as exc:  # ValidationError or value errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameters invalid for {rule_type}: {exc}",
        ) from exc


def _to_summary(rule: Rule, *, test_count: int = 0, passing: int = 0, failing: int = 0) -> RuleSummary:
    return RuleSummary(
        id=rule.id,
        business_id=rule.business_id,
        rule_type=rule.rule_type,
        name=rule.name,
        description=rule.description,
        applies_when_description=rule.applies_when_description,
        parameters=rule.parameters,
        applies_to_tools=list(rule.applies_to_tools or []),
        enforcement_mode=rule.enforcement_mode,
        priority=rule.priority,
        is_active=rule.is_active,
        source_prompt=rule.source_prompt,
        test_case_count=test_count,
        test_passing=passing,
        test_failing=failing,
    )


def _summaries_for_business(db: Session, business_id: UUID) -> list[RuleSummary]:
    rules = (
        db.execute(
            select(Rule)
            .where(Rule.business_id == business_id)
            .order_by(Rule.priority.desc(), Rule.created_at.asc())
        )
        .scalars()
        .all()
    )

    counts = {
        row[0]: (row[1], row[2], row[3])
        for row in db.execute(
            select(
                TestCase.rule_id,
                func.count(TestCase.id),
                func.count().filter(TestCase.last_run_result == "pass"),
                func.count().filter(TestCase.last_run_result == "fail"),
            )
            .where(TestCase.rule_id.in_([r.id for r in rules]))
            .group_by(TestCase.rule_id)
        ).all()
    }
    out: list[RuleSummary] = []
    for r in rules:
        c = counts.get(r.id, (0, 0, 0))
        out.append(_to_summary(r, test_count=c[0], passing=c[1], failing=c[2]))
    return out


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get("", response_model=list[RuleSummary])
def list_rules(
    business_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
    _biz: Annotated[Business, Depends(get_business)],
) -> list[RuleSummary]:
    return _summaries_for_business(db, business_id)


@router.post("", response_model=CreateRuleOut)
async def create_rule(
    business_id: UUID,
    body: CreateRuleIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
    _biz: Annotated[Business, Depends(get_business)],
) -> CreateRuleOut:
    compiled: CompiledRule | None = body.compiled
    if compiled is None and body.prompt:
        result = await compile_rule(body.prompt)
        if isinstance(result, CompileFailure):
            return CreateRuleOut(failure=result)
        compiled = result
    if compiled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either `compiled` or `prompt`.",
        )

    _validate_against_schema(compiled.rule_type, compiled.parameters)

    rule = Rule(
        business_id=business_id,
        rule_type=compiled.rule_type,
        name=compiled.name,
        description=compiled.description,
        applies_when_description=compiled.applies_when_description,
        parameters=compiled.parameters,
        applies_to_tools=compiled.applies_to_tools,
        enforcement_mode=compiled.enforcement_mode,
        priority=compiled.priority,
        is_active=True,
        source_prompt=compiled.source_prompt,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return CreateRuleOut(rule=_to_summary(rule))


@router.patch("/{rule_id}", response_model=RuleSummary)
def update_rule(
    business_id: UUID,
    rule_id: UUID,
    body: UpdateRuleIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> RuleSummary:
    rule = db.get(Rule, rule_id)
    if rule is None or rule.business_id != business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    patch = body.model_dump(exclude_none=True)
    if "parameters" in patch:
        _validate_against_schema(rule.rule_type, patch["parameters"])
    for k, v in patch.items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return _to_summary(rule)


@router.delete("/{rule_id}")
def delete_rule(
    business_id: UUID,
    rule_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    rule = db.get(Rule, rule_id)
    if rule is None or rule.business_id != business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"deleted": str(rule_id)}
