"""SQLAlchemy 2.0 typed models — six tables per § 2 of the engineering doc."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid_pk() -> Mapped[UUID]:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


def _now_col(*, on_update: bool = False) -> Mapped[datetime]:
    if on_update:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# --------------------------------------------------------------------------- #
# Business
# --------------------------------------------------------------------------- #


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="America/New_York")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = _now_col(on_update=True)

    rules: Mapped[list["Rule"]] = relationship(back_populates="business", cascade="all,delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="business")


# --------------------------------------------------------------------------- #
# Rule
# --------------------------------------------------------------------------- #


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[UUID] = _uuid_pk()
    business_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    applies_when_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    applies_to_tools: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    enforcement_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="block")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = _now_col(on_update=True)

    business: Mapped[Business] = relationship(back_populates="rules")
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="rule", cascade="all,delete-orphan"
    )

    __table_args__ = (
        Index("ix_rules_business_active_type", "business_id", "is_active", "rule_type"),
    )


# --------------------------------------------------------------------------- #
# Conversation + messages
# --------------------------------------------------------------------------- #


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = _uuid_pk()
    business_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    customer_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    had_accepted_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    had_blocked_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocked_rule_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=False, default=list
    )
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    system_prompt_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = _now_col(on_update=True)

    business: Mapped[Business] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all,delete-orphan"
    )

    __table_args__ = (
        Index("ix_conv_biz_lastmsg", "business_id", "last_message_at"),
        Index("ix_conv_biz_blocked", "business_id", "had_blocked_action"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = _uuid_pk()
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _now_col()

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conv_created", "conversation_id", "created_at"),)


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = _uuid_pk()
    business_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    fired_rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    fired_rule_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    fired_rule_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_args: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proposed_action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_facing_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_fields: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_audit_biz_fired", "business_id", "fired_at"),
        Index("ix_audit_biz_conv_fired", "business_id", "conversation_id", "fired_at"),
        Index("ix_audit_biz_rule", "business_id", "fired_rule_id"),
        Index("ix_audit_biz_outcome", "business_id", "outcome"),
        Index("ix_audit_biz_tool", "business_id", "tool_name"),
    )


# --------------------------------------------------------------------------- #
# Test cases
# --------------------------------------------------------------------------- #


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[UUID] = _uuid_pk()
    rule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_message: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    expected_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_result: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_run_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = _now_col(on_update=True)

    rule: Mapped[Rule] = relationship(back_populates="test_cases")


__all__ = [
    "AuditLog",
    "Business",
    "Conversation",
    "Message",
    "Rule",
    "TestCase",
]
