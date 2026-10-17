"""Contracts for the staff-only read assistant."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StaffAgentChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class StaffAgentToolState(BaseModel):
    tool: str
    status: str


class StaffAgentChatResponse(BaseModel):
    conversation_id: UUID
    assistant_text: str
    tool_states: list[StaffAgentToolState] = Field(default_factory=list)
    pending_action: dict | None = None


class StaffAgentActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    pending_action_id: UUID
    patient_agreed: bool = False


class StaffAgentActionResponse(BaseModel):
    conversation_id: UUID
    assistant_text: str


class StaffAgentPendingAction(BaseModel):
    id: UUID
    booking_id: UUID
    decision: str
    reason: str | None = None
    booking_summary: dict
    expires_at: datetime
