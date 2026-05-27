"""GET /api/businesses — used by the frontend business switcher."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import authenticate
from app.db import get_session
from app.models import Business

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


class BusinessOut(BaseModel):
    id: UUID
    name: str
    timezone: str
    description: str


@router.get("", response_model=list[BusinessOut])
def list_businesses(
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> list[BusinessOut]:
    rows = db.execute(select(Business).order_by(Business.name)).scalars().all()
    return [
        BusinessOut(id=b.id, name=b.name, timezone=b.timezone, description=b.description) for b in rows
    ]
