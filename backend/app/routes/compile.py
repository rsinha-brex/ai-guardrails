"""POST /api/businesses/{id}/rules/compile — compile-only endpoint."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.compile_agent import compile_rule
from app.auth import authenticate, get_business
from app.db import get_session
from app.models import Business
from app.schemas.rules import CompiledRule, CompileFailure

router = APIRouter(prefix="/api", tags=["rules"])


class CompilePromptIn(BaseModel):
    prompt: str


class CompileResultOut(BaseModel):
    kind: str  # "compiled" | "failure"
    rule: CompiledRule | None = None
    failure: CompileFailure | None = None


@router.post("/businesses/{business_id}/rules/compile", response_model=CompileResultOut)
async def compile_rule_endpoint(
    business_id: UUID,
    body: CompilePromptIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
    _biz: Annotated[Business, Depends(get_business)],
) -> CompileResultOut:
    out = await compile_rule(body.prompt)
    if isinstance(out, CompiledRule):
        return CompileResultOut(kind="compiled", rule=out)
    return CompileResultOut(kind="failure", failure=out)
