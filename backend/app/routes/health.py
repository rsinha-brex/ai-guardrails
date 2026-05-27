from __future__ import annotations

from fastapi import APIRouter

from app import db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    try:
        ok = db.ping()
        return {"status": "ok", "database": "connected" if ok else "down"}
    except Exception as exc:
        return {"status": "ok", "database": "down", "error": str(exc)}
