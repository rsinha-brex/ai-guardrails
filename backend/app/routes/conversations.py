"""Conversation routes — create, post message (SSE), reset, list."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.agent import build_agent, system_prompt_for
from app.agent.judge import LLMJudge
from app.agent.tools import AgentDeps
from app.auth import authenticate
from app.db import get_session
from app.models import Business, Conversation, Message
from app.schemas.conversation_state import ConversationState
from app.services import audit

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["conversations"])
_AGENT = build_agent()
_JUDGE = LLMJudge()


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


class CreateConversationIn(BaseModel):
    business_id: UUID
    customer_identifier: str | None = None
    is_test: bool = False


class ConversationOut(BaseModel):
    id: UUID
    business_id: UUID
    customer_identifier: str
    state: dict[str, Any]
    started_at: datetime
    last_message_at: datetime
    message_count: int
    had_blocked_action: bool
    had_accepted_action: bool
    blocked_rule_ids: list[UUID]
    is_test: bool


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime


class PostMessageIn(BaseModel):
    content: str


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _to_conv_out(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        business_id=conv.business_id,
        customer_identifier=conv.customer_identifier,
        state=conv.state or {},
        started_at=conv.started_at,
        last_message_at=conv.last_message_at,
        message_count=conv.message_count,
        had_blocked_action=conv.had_blocked_action,
        had_accepted_action=conv.had_accepted_action,
        blocked_rule_ids=list(conv.blocked_rule_ids or []),
        is_test=conv.is_test,
    )


def _new_customer_id() -> str:
    return f"Customer #{secrets.token_hex(2)}"


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(
    body: CreateConversationIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> ConversationOut:
    biz = db.get(Business, body.business_id)
    if biz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    conv = Conversation(
        business_id=body.business_id,
        customer_identifier=body.customer_identifier or _new_customer_id(),
        state={},
        is_test=body.is_test,
    )
    db.add(conv)
    db.flush()
    # Snapshot the system prompt at conversation start.
    deps_for_snapshot = AgentDeps(
        db=db,
        business_id=conv.business_id,
        conversation_id=conv.id,
        customer_identifier=conv.customer_identifier,
        current_time=datetime.now(timezone.utc),
    )
    conv.system_prompt_snapshot = system_prompt_for(deps_for_snapshot)
    db.commit()
    db.refresh(conv)
    return _to_conv_out(conv)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> ConversationOut:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _to_conv_out(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> list[MessageOut]:
    rows = db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).scalars().all()
    return [
        MessageOut(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in rows
    ]


@router.delete("/conversations/{conversation_id}")
def reset_conversation(
    conversation_id: UUID,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
) -> dict:
    """Clear messages + state + audit events for this conversation.

    The conversation row itself is preserved so the localStorage pointer
    stays valid; everything inside it is wiped so the Live activity rail
    starts empty after a reset.
    """
    from app.models import AuditLog
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.query(AuditLog).filter(AuditLog.conversation_id == conversation_id).delete()
    conv.state = {}
    conv.message_count = 0
    conv.had_accepted_action = False
    conv.had_blocked_action = False
    conv.blocked_rule_ids = []
    db.commit()
    return {"reset": str(conversation_id)}


@router.post("/conversations/{conversation_id}/messages")
async def post_message(
    conversation_id: UUID,
    body: PostMessageIn,
    db: Annotated[Session, Depends(get_session)],
    _user: Annotated[str, Depends(authenticate)],
):
    """Stream agent response over SSE."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Persist user message immediately.
    user_msg = Message(conversation_id=conv.id, role="user", content=body.content)
    db.add(user_msg)
    conv.message_count += 1
    conv.last_message_at = datetime.now(timezone.utc)
    db.flush()

    # Load prior message history for the agent.
    history_msgs = db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.id != user_msg.id)
        .order_by(Message.created_at)
    ).scalars().all()

    deps = AgentDeps(
        db=db,
        business_id=conv.business_id,
        conversation_id=conv.id,
        customer_identifier=conv.customer_identifier,
        current_time=datetime.now(timezone.utc),
        state=dict(conv.state or {}),
        judge=_JUDGE,
    )

    async def event_stream():
        # Open SSE
        try:
            async with _AGENT.run_stream(
                body.content,
                deps=deps,
                message_history=_history_to_messages(history_msgs),
            ) as result:
                full_text = ""
                async for chunk in result.stream_text(delta=True):
                    full_text += chunk
                    yield _sse("message_chunk", {"text": chunk})
                final = await result.get_output()
                if isinstance(final, str) and final and final != full_text:
                    # If the model returned more after the stream, send the remainder.
                    rest = final[len(full_text):]
                    if rest:
                        yield _sse("message_chunk", {"text": rest})
                    full_text = final

            # Persist assistant message + finalize conversation row.
            assistant = Message(conversation_id=conv.id, role="assistant", content=full_text)
            db.add(assistant)
            conv.message_count += 1
            conv.last_message_at = datetime.now(timezone.utc)
            if deps.state_dirty:
                conv.state = dict(deps.state)
            if deps.accepted_action:
                conv.had_accepted_action = True
            if deps.blocked_rule_ids:
                conv.had_blocked_action = True
                merged = list({*conv.blocked_rule_ids, *deps.blocked_rule_ids})
                conv.blocked_rule_ids = merged
            db.commit()
            yield _sse("done", {"text": full_text})
        except Exception as exc:  # surface errors as a final SSE event
            log.exception("agent run failed")
            audit.record(
                db,
                business_id=conv.business_id,
                conversation_id=conv.id,
                customer_identifier=conv.customer_identifier,
                event_type="error",
                outcome="failed",
                error_code="agent_run",
                user_facing_message=str(exc),
            )
            db.commit()
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _history_to_messages(messages):
    """Convert SQLA Message rows to Pydantic AI message dicts."""
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        TextPart,
        UserPromptPart,
    )

    out = []
    for m in messages:
        if m.role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
        else:
            out.append(ModelResponse(parts=[TextPart(content=m.content)]))
    return out
