"""Test cases — CRUD + run + refine."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.compile_agent import compile_rule
from app.agent.refine_agent import RuleRefinement, refine_rule
from app.auth import authenticate
from app.db import get_session
from app.models import Rule, TestCase
from app.schemas.rules import CompiledRule, CompileFailure
from app.services import test_runner

router = APIRouter(prefix="/api", tags=["test_cases"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class TestCaseIn(BaseModel):
    customer_message: str
    expected_outcome: str  # block | allow | needs_info
    expected_notes: str | None = None


class TestCaseOut(BaseModel):
    id: UUID
    rule_id: UUID
    customer_message: str
    expected_outcome: str
    expected_notes: str | None
    last_run_at: datetime | None
    last_run_result: str | None
    last_run_details: dict[str, Any] | None


class RefineIn(BaseModel):
    test_case_id: UUID


class RefineOut(BaseModel):
    refinement: RuleRefinement
    recompiled: CompiledRule | None = None
    failure: CompileFailure | None = None


def _to_out(tc: TestCase) -> TestCaseOut:
    return TestCaseOut(
        id=tc.id,
        rule_id=tc.rule_id,
        customer_message=tc.customer_message,
        expected_outcome=tc.expected_outcome,
        expected_notes=tc.expected_notes,
        last_run_at=tc.last_run_at,
        last_run_result=tc.last_run_result,
        last_run_details=tc.last_run_details,
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get("/rules/{rule_id}/test-cases", response_model=list[TestCaseOut])
def list_cases(
    rule_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> list[TestCaseOut]:
    rows = db.execute(
        select(TestCase).where(TestCase.rule_id == rule_id).order_by(TestCase.created_at)
    ).scalars().all()
    return [_to_out(t) for t in rows]


@router.post("/rules/{rule_id}/test-cases", response_model=TestCaseOut)
def create_case(
    rule_id: UUID,
    body: TestCaseIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> TestCaseOut:
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if body.expected_outcome not in {"block", "allow", "needs_info"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expected_outcome must be one of block, allow, needs_info",
        )
    tc = TestCase(
        rule_id=rule_id,
        customer_message=body.customer_message,
        expected_outcome=body.expected_outcome,
        expected_notes=body.expected_notes,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return _to_out(tc)


@router.delete("/rules/{rule_id}/test-cases/{test_case_id}")
def delete_case(
    rule_id: UUID,
    test_case_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    tc = db.get(TestCase, test_case_id)
    if tc is None or tc.rule_id != rule_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
    db.delete(tc)
    db.commit()
    return {"deleted": str(test_case_id)}


@router.post("/rules/{rule_id}/test-cases/{test_case_id}/run", response_model=TestCaseOut)
async def run_one(
    rule_id: UUID,
    test_case_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> TestCaseOut:
    tc = db.get(TestCase, test_case_id)
    if tc is None or tc.rule_id != rule_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
    await test_runner.run_test_case(db, test_case_id)
    db.refresh(tc)
    return _to_out(tc)


@router.post("/rules/{rule_id}/test-cases/run", response_model=list[TestCaseOut])
async def run_all(
    rule_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> list[TestCaseOut]:
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await test_runner.run_all_for_rule(db, rule_id)
    rows = db.execute(
        select(TestCase).where(TestCase.rule_id == rule_id).order_by(TestCase.created_at)
    ).scalars().all()
    return [_to_out(t) for t in rows]


@router.post("/rules/{rule_id}/refine", response_model=RefineOut)
async def refine(
    rule_id: UUID,
    body: RefineIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> RefineOut:
    rule = db.get(Rule, rule_id)
    tc = db.get(TestCase, body.test_case_id)
    if rule is None or tc is None or tc.rule_id != rule.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule or test case not found")
    if not tc.last_run_details or tc.last_run_result != "fail":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test case has not failed; run it first.",
        )
    details = tc.last_run_details
    refinement = await refine_rule(
        source_prompt=rule.source_prompt or "",
        rule_description=rule.description,
        rule_params=rule.parameters,
        customer_message=tc.customer_message,
        expected=details.get("expected", tc.expected_outcome),
        actual=details.get("actual", "?"),
        audit_excerpt=details.get("audit", []),
        agent_response=details.get("agent_response", ""),
    )
    # Re-compile the new prompt.
    out: RefineOut = RefineOut(refinement=refinement)
    if refinement.updated_prompt.strip():
        compiled = await compile_rule(refinement.updated_prompt)
        if isinstance(compiled, CompiledRule):
            out.recompiled = compiled
        else:
            out.failure = compiled
    return out
