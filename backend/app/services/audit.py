"""Audit log writer."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    business_id: UUID,
    conversation_id: UUID,
    customer_identifier: str | None,
    event_type: str,
    outcome: str,
    tool_name: str | None = None,
    fired_rule_id: UUID | None = None,
    fired_rule_type: str | None = None,
    fired_rule_name: str | None = None,
    tool_args: dict[str, Any] | None = None,
    proposed_action: dict[str, Any] | None = None,
    user_facing_message: str | None = None,
    internal_reason: str | None = None,
    required_fields: list[str] | None = None,
    error_code: str | None = None,
    message_id: UUID | None = None,
) -> AuditLog:
    row = AuditLog(
        business_id=business_id,
        conversation_id=conversation_id,
        customer_identifier=customer_identifier,
        event_type=event_type,
        outcome=outcome,
        tool_name=tool_name,
        fired_rule_id=fired_rule_id,
        fired_rule_type=fired_rule_type,
        fired_rule_name=fired_rule_name,
        tool_args=tool_args,
        proposed_action=proposed_action,
        user_facing_message=user_facing_message,
        internal_reason=internal_reason,
        required_fields=required_fields,
        error_code=error_code,
        message_id=message_id,
    )
    db.add(row)
    db.flush()
    return row
