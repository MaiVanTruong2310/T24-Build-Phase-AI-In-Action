"""Doctor schedule request and response schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.catalog_types import MutableScheduleStatus


class GuestPatientCreate(BaseModel):
    """Contact data used when staff books a patient without an account."""

    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(min_length=7, max_length=32)

    @model_validator(mode="after")
    def normalize_contact(self) -> "GuestPatientCreate":
        self.full_name = self.full_name.strip()
        self.email = self.email.strip().lower()
        self.phone = self.phone.strip()
        if not self.full_name or not self.email or not self.phone:
            raise ValueError("Guest patient name, email and phone are required")
        return self


class DoctorScheduleCreate(BaseModel):
    """Create an availability slot."""

    doctor_id: UUID
    facility_id: UUID
    service_id: UUID | None = None
    specialty_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=0)
    status: MutableScheduleStatus = "available"
    source_system: str | None = Field(default=None, max_length=64)
    external_schedule_id: str | None = Field(default=None, max_length=128)
    patient_id: UUID | None = None
    guest_patient: GuestPatientCreate | None = None
    encounter_type: Literal["in_person", "telehealth"] = "in_person"
    reason: str = Field(default="Staff-created appointment", min_length=1, max_length=2000)
    patient_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleCreate":
        """Reject a slot whose end is not after its start."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.patient_id and self.guest_patient:
            raise ValueError("patient_id and guest_patient are mutually exclusive")
        self.reason = self.reason.strip()
        return self


class StaffScheduleCreate(DoctorScheduleCreate):
    """Manual staff schedule creation, always scoped to one service."""

    service_id: UUID


class DoctorScheduleUpdate(BaseModel):
    """Replace a slot's mutable fields using optimistic-lock versioning."""

    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=0)
    status: MutableScheduleStatus
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleUpdate":
        """Validate the complete replacement time range."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class DoctorScheduleResponse(BaseModel):
    """Availability slot representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    facility_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int
    remaining_capacity: int | None = None
    status: str
    version: int
    source_system: str | None
    external_schedule_id: str | None
    created_by: UUID | None
    updated_by: UUID | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class StaffScheduleCreateResponse(BaseModel):
    """Created schedule and optional direct-confirmed booking reference."""

    schedule: DoctorScheduleResponse
    booking_id: UUID | None = None
    booking_status: Literal["confirmed"] | None = None


class ScheduleImportRecord(DoctorScheduleCreate):
    """One idempotent schedule import record."""

    source_system: str = Field(min_length=1, max_length=64)
    external_schedule_id: str = Field(min_length=1, max_length=128)
    expected_version: int | None = Field(default=None, ge=1)


class BulkScheduleImportRequest(BaseModel):
    """JSON batch payload with per-record validation in the service layer."""

    records: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class ScheduleCancellationRequest(BaseModel):
    """Reason required when a schedule is cancelled."""

    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_reason(self) -> "ScheduleCancellationRequest":
        """Reject whitespace-only cancellation reasons."""
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("reason must not be blank")
        return self


class BulkImportItemResult(BaseModel):
    """Result for one imported schedule record."""

    external_schedule_id: str
    schedule: DoctorScheduleResponse | None = None
    error: str | None = None


class BulkImportResponse(BaseModel):
    """Partial-success response for a schedule import batch."""

    created: int
    updated: int
    failed: int
    items: list[BulkImportItemResult]
