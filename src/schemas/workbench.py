from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class CaseAction(BaseModel):
    version: int = Field(ge=1)
    action: Literal[
        "claim",
        "handover",
        "takeover",
        "resume",
        "contact",
        "follow_up",
        "emergency_ack",
        "emergency_transfer",
        "complete",
        "cancel",
        "decline",
        "reopen",
        "refund_request",
        "refund_confirm",
    ]
    note: str = Field(default="", max_length=4000)
    assigned_to: UUID | None = None
    follow_up_at: datetime | None = None
    reference: str | None = Field(default=None, max_length=200)


class BulkCaseAction(BaseModel):
    case_ids: list[UUID] = Field(min_length=1, max_length=100)
    action: Literal["claim", "decline"]
    note: str = Field(default="", max_length=4000)


class PlanInput(BaseModel):
    version: int = Field(ge=1)
    specialty_id: UUID
    service_id: UUID
    schedule_id: UUID
    reason: str = Field(min_length=2, max_length=2000)
    patient_agreed: bool


class DepositInput(BaseModel):
    version: int = Field(ge=1)
    amount: int = Field(gt=0, le=2000000000)


class VerifyInput(BaseModel):
    version: int = Field(ge=1)
    reference: str = Field(min_length=2, max_length=200)
    evidence: str = Field(min_length=2, max_length=2000)

    @field_validator("reference", "evidence")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Không được để trống.")
        return value.strip()


class VersionInput(BaseModel):
    version: int = Field(ge=1)


class ShiftHandoverInput(BaseModel):
    assigned_to: UUID
    note: str = Field(min_length=2, max_length=4000)


class MessageInput(BaseModel):
    client_id: UUID = Field(default_factory=uuid4)
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Tin nhắn không được để trống.")
        return value.strip()


class PolicyInput(BaseModel):
    hold_minutes: int = Field(ge=5, le=1440)
    response_minutes: int = Field(ge=1, le=10080)
    emergency_response_minutes: int = Field(ge=1, le=60)
    payment_instructions: str = Field(min_length=10, max_length=4000)
    refund_policy: str = Field(min_length=10, max_length=4000)

    @field_validator("payment_instructions", "refund_policy")
    @classmethod
    def nonblank(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("Nhập đầy đủ điều khoản thực tế.")
        return value.strip()


class MemberInput(BaseModel):
    user_id: UUID
    enabled: bool = True
    is_admin: bool = False
    facility_ids: list[UUID] = Field(default_factory=list, max_length=100)
    clinical_qualification: str = Field(min_length=2, max_length=200)
