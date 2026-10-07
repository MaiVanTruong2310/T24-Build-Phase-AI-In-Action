"""Schemas for human-in-the-loop chat takeover APIs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TakeoverStatus = Literal["queued", "taken_over", "released", "resolved"]
TakeoverPriority = Literal["critical", "high", "normal"]
TakeoverAuthor = Literal["patient", "assistant", "staff", "system"]


class ChatTakeoverMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    client_message_id: str | None = Field(default=None, min_length=1, max_length=128)


class ChatTakeoverMessageResponse(BaseModel):
    id: UUID | str
    case_id: UUID | None = None
    author_type: TakeoverAuthor
    author_user_id: UUID | None = None
    content: str
    client_message_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class ChatTakeoverCaseResponse(BaseModel):
    id: UUID
    patient_user_id: UUID
    session_id: str
    status: TakeoverStatus
    priority: TakeoverPriority
    workflow_status: str
    summary: dict = Field(default_factory=dict)
    assigned_staff_id: UUID | None = None
    claimed_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatTakeoverCaseDetail(BaseModel):
    case: ChatTakeoverCaseResponse
    messages: list[ChatTakeoverMessageResponse]
