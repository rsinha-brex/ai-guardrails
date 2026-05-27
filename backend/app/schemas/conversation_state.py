"""Closed conversation-state schema.

Eight nullable fields, no extras allowed. Rules can only reference these.
Extending the schema requires a code change — by design, per § 6 of the
engineering doc.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class ConversationState(BaseModel):
    # `extra="forbid"` keeps the schema closed; the LLM occasionally tries to
    # invent fields and we'd rather see the failure than silently store them.
    # The string fields use lax coercion because the LLM sometimes serializes
    # ZIPs / addresses / years as numbers.
    model_config = ConfigDict(extra="forbid")

    address_zip: str | None = None
    address: str | None = None
    property_year_built: int | None = None
    hoa_governed: bool | None = None
    is_homeowner: bool | None = None
    is_existing_customer: bool | None = None
    reported_issue: str | None = None
    is_emergency: bool | None = None

    @field_validator("address_zip", "address", "reported_issue", mode="before")
    @classmethod
    def _coerce_to_str(cls, v):
        if v is None or isinstance(v, str):
            return v
        return str(v)


STATE_FIELDS: tuple[str, ...] = tuple(ConversationState.model_fields.keys())
