"""Admin endpoints — gated by HTTP Basic Auth like everything else."""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


# --------------------------------------------------------------------------- #
# Screenshot capture for the README walkthrough.
#
# The browser-side `html-to-image` library renders the live page to a PNG
# data URL. This endpoint accepts that URL + a filename and writes the
# decoded bytes into the repo's `screenshots/` folder. Used by the GTM
# browser walkthrough — production never calls this. Auth-gated like every
# other admin route.
# --------------------------------------------------------------------------- #


_SCREENSHOTS_DIR = Path(__file__).resolve().parents[3] / "screenshots"
_SAFE_NAME = re.compile(r"^[a-z0-9_-]+$")


class _SaveScreenshotPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    data_url: str  # data:image/png;base64,...


@router.post("/save-screenshot")
def save_screenshot(
    payload: _SaveScreenshotPayload,
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    if not _SAFE_NAME.fullmatch(payload.name):
        raise HTTPException(400, "name must be lowercase a-z, 0-9, '_', '-'")
    if not payload.data_url.startswith("data:image/png;base64,"):
        raise HTTPException(400, "data_url must be a base64-encoded PNG")
    raw = base64.b64decode(payload.data_url.split(",", 1)[1])
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = _SCREENSHOTS_DIR / f"{payload.name}.png"
    out.write_bytes(raw)
    return {"path": str(out.relative_to(_SCREENSHOTS_DIR.parent)), "bytes": len(raw)}
