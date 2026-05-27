from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import Business

_security = HTTPBasic()


def authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> str:
    s = get_settings()
    user_ok = secrets.compare_digest(credentials.username, s.basic_auth_user)
    pass_ok = secrets.compare_digest(credentials.password, s.basic_auth_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_business(
    business_id: UUID,
    db: Annotated[Session, Depends(get_session)],
) -> Business:
    """FastAPI dependency: load a Business by id from a query/path param.

    Raises 404 if not found. Use as `biz: Annotated[Business, Depends(get_business)]`
    in any route whose business_id comes from the URL (query or path).
    Routes that take business_id from a request body should fetch inline
    instead — this dep can't see body params.
    """
    biz = db.get(Business, business_id)
    if biz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    return biz
