"""Admin endpoints — gated by HTTP Basic Auth like everything else."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth import authenticate
from app.db import get_session
from app.models import AuditLog, Conversation, Message
from app.services.seed import force_reseed, wipe_all_and_reseed, wipe_rules_and_reseed

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-demo-data")
def reset_demo_data(
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    """Wipe conversations + audit + messages, keep businesses + rules."""
    msg_deleted = db.execute(delete(Message)).rowcount
    audit_deleted = db.execute(delete(AuditLog)).rowcount
    conv_deleted = db.execute(delete(Conversation)).rowcount
    db.commit()
    # Make sure seeds are still in place (idempotent).
    force_reseed()
    return {
        "deleted_messages": msg_deleted,
        "deleted_audit": audit_deleted,
        "deleted_conversations": conv_deleted,
    }


@router.post("/reseed-rules")
def reseed_rules(_user: Annotated[str, Depends(authenticate)]) -> dict:
    """Wipe and reinsert the canonical seed rules. Test cases cascade with
    their rules; conversations, messages, and audit log are preserved."""
    return wipe_rules_and_reseed()


@router.post("/wipe-all-and-reseed")
def wipe_all_and_reseed_route(_user: Annotated[str, Depends(authenticate)]) -> dict:
    """Hard reset — wipes businesses + rules + conversations + audit + messages,
    then reseeds the canonical 12-business state. Used by the corpus runner so
    every test run starts from deterministic state.
    """
    return wipe_all_and_reseed()
