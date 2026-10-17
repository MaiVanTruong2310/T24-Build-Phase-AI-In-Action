from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


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
        "emergency_dismiss",
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


class CaseBookingInput(BaseModel):
    version: int = Field(ge=1)
    schedule_id: UUID | None = None
    doctor_id: UUID | None = None
    facility_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    specialty_id: UUID
    service_id: UUID | None = None
    encounter_type: Literal["in_person", "telehealth"] = "in_person"
    reason: str = Field(min_length=1, max_length=2000)
    patient_note: str | None = Field(default=None, max_length=2000)
    patient_agreed: bool
    patient_name: str | None = Field(default=None, min_length=1, max_length=200)
    patient_email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    patient_phone: str | None = Field(default=None, pattern=r"^(?:0|\+84)[35789]\d{8}$")
    patient_date_of_birth: date | None = None
    patient_gender: str | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def validate_schedule_selection(self):
        free_period = (self.doctor_id, self.facility_id, self.starts_at, self.ends_at)
        if self.schedule_id is not None and any(value is not None for value in free_period):
            raise ValueError("Select either a published schedule or a free period")
        if self.schedule_id is None and (any(value is None for value in free_period) or self.ends_at <= self.starts_at):
            raise ValueError("A valid doctor free period is required")
        if self.schedule_id is None and (
            self.starts_at.tzinfo is None
            or self.ends_at.tzinfo is None
            or (self.ends_at - self.starts_at).total_seconds() < 300
            or (self.ends_at - self.starts_at).total_seconds() > 28800
        ):
            raise ValueError("Free periods require timezone-aware timestamps and a duration from 5 to 480 minutes")
        return self

    @field_validator("reason", "patient_name", "patient_email", "patient_phone")
    @classmethod
    def strip_optional_text(cls, value):
        normalized = value.strip() if value is not None else value
        if normalized == "":
            raise ValueError("Field must not be blank")
        return normalized

    @field_validator("patient_date_of_birth")
    @classmethod
    def birth_date_not_in_future(cls, value):
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value


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
