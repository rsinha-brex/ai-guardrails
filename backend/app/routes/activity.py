"""Activity routes — conversation list, drill-in events, system-prompt snapshot."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth import authenticate, get_business
from app.db import get_session
from app.models import AuditLog, Business, Conversation, Message

router = APIRouter(prefix="/api", tags=["activity"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class ConversationSummary(BaseModel):
    id: UUID
    business_id: UUID
    customer_identifier: str
    started_at: datetime
    last_message_at: datetime
    message_count: int
    had_blocked_action: bool
    had_accepted_action: bool
    blocked_rule_ids: list[UUID]
    is_test: bool
    outcome: str  # blocked | accepted | open

    @classmethod
    def from_row(cls, c: Conversation) -> ConversationSummary:
        outcome = "open"
        if c.had_blocked_action:
            outcome = "blocked"
        elif c.had_accepted_action:
            outcome = "accepted"
        return cls(
            id=c.id,
            business_id=c.business_id,
            customer_identifier=c.customer_identifier,
            started_at=c.started_at,
            last_message_at=c.last_message_at,
            message_count=c.message_count,
            had_blocked_action=c.had_blocked_action,
            had_accepted_action=c.had_accepted_action,
            blocked_rule_ids=list(c.blocked_rule_ids or []),
            is_test=c.is_test,
            outcome=outcome,
        )


class EventOut(BaseModel):
    id: UUID
    event_type: str
    outcome: str
    tool_name: str | None
    fired_rule_id: UUID | None
    fired_rule_type: str | None
    fired_rule_name: str | None
    tool_args: dict[str, Any] | None
    proposed_action: dict[str, Any] | None
    user_facing_message: str | None
    internal_reason: str | None
    required_fields: list[str] | None
    fired_at: datetime


class TimelineMessage(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime


class DrillInOut(BaseModel):
    conversation: ConversationSummary
    events: list[EventOut]
    messages: list[TimelineMessage]
    system_prompt: str


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get(
    "/businesses/{business_id}/conversations",
    response_model=list[ConversationSummary],
)
def list_conversations(
    business_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
    _biz: Annotated[Business, Depends(get_business)],
    outcome: str | None = Query(None),
    rule_id: UUID | None = Query(None),
    customer: str | None = Query(None),
    is_test: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[ConversationSummary]:
    stmt = (
        select(Conversation)
        .where(Conversation.business_id == business_id)
        .order_by(desc(Conversation.last_message_at))
        .limit(limit)
    )
    if outcome == "blocked":
        stmt = stmt.where(Conversation.had_blocked_action.is_(True))
    elif outcome == "accepted":
        stmt = stmt.where(Conversation.had_accepted_action.is_(True))
    elif outcome == "open":
        stmt = stmt.where(
            Conversation.had_blocked_action.is_(False),
            Conversation.had_accepted_action.is_(False),
        )
    if rule_id is not None:
        stmt = stmt.where(Conversation.blocked_rule_ids.any(rule_id))  # type: ignore[attr-defined]
    if customer:
        stmt = stmt.where(Conversation.customer_identifier.ilike(f"%{customer}%"))
    if is_test is not None:
        stmt = stmt.where(Conversation.is_test.is_(is_test))

    rows = db.execute(stmt).scalars().all()
    return [ConversationSummary.from_row(c) for c in rows]


@router.get("/conversations/{conversation_id}/events", response_model=list[EventOut])
def conversation_events(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> list[EventOut]:
    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.conversation_id == conversation_id)
        .order_by(AuditLog.fired_at)
    ).scalars().all()
    return [
        EventOut(
            id=r.id,
            event_type=r.event_type,
            outcome=r.outcome,
            tool_name=r.tool_name,
            fired_rule_id=r.fired_rule_id,
            fired_rule_type=r.fired_rule_type,
            fired_rule_name=r.fired_rule_name,
            tool_args=r.tool_args,
            proposed_action=r.proposed_action,
            user_facing_message=r.user_facing_message,
            internal_reason=r.internal_reason,
            required_fields=list(r.required_fields) if r.required_fields else None,
            fired_at=r.fired_at,
        )
        for r in rows
    ]


@router.get("/conversations/{conversation_id}/drill", response_model=DrillInOut)
def drill_in(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> DrillInOut:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    events = conversation_events(conversation_id, db, "")  # auth already enforced
    msgs = db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).scalars().all()
    return DrillInOut(
        conversation=ConversationSummary.from_row(conv),
        events=events,
        messages=[
            TimelineMessage(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in msgs
        ],
        system_prompt=conv.system_prompt_snapshot or "",
    )


@router.get("/conversations/{conversation_id}/system-prompt")
def system_prompt_snapshot(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"system_prompt": conv.system_prompt_snapshot or ""}
