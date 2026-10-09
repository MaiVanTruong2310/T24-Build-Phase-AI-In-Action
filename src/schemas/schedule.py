"""Doctor schedule request and response schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.catalog_types import MutableScheduleStatus


class DoctorScheduleCreate(BaseModel):
    """Create an availability slot."""

    doctor_id: UUID
    facility_id: UUID
    service_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=0)
    status: MutableScheduleStatus = "available"
    busy_reason: Literal["consultation", "other_commitment"] | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleCreate":
        """Reject a slot whose end is not after its start."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.status == "available" and (self.service_id is None or self.capacity < 1):
            raise ValueError("Available schedules require a service and positive capacity")
        if self.status == "blocked":
            if self.busy_reason is None:
                raise ValueError("Blocked schedules require a busy reason")
            if self.busy_reason == "consultation" and self.service_id is None:
                raise ValueError("Consultation blocks require a service")
            if self.capacity != 0:
                raise ValueError("Blocked schedules must have zero capacity")
        elif self.busy_reason is not None:
            raise ValueError("busy_reason is only valid for blocked schedules")
        if self.note is not None:
            self.note = self.note.strip() or None
        return self


class DoctorScheduleUpdate(BaseModel):
    """Replace a slot's mutable fields using optimistic-lock versioning."""

    starts_at: datetime
    ends_at: datetime
    service_id: UUID | None = None
    capacity: int = Field(ge=0)
    status: MutableScheduleStatus
    busy_reason: Literal["consultation", "other_commitment"] | None = None
    note: str | None = Field(default=None, max_length=500)
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleUpdate":
        """Validate the complete replacement time range."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.status == "available" and (self.service_id is None or self.capacity < 1):
            raise ValueError("Available schedules require a service and positive capacity")
        if self.status == "blocked":
            if self.busy_reason is None:
                raise ValueError("Blocked schedules require a busy reason")
            if self.busy_reason == "consultation" and self.service_id is None:
                raise ValueError("Consultation blocks require a service")
            if self.capacity != 0:
                raise ValueError("Blocked schedules must have zero capacity")
        elif self.busy_reason is not None:
            raise ValueError("busy_reason is only valid for blocked schedules")
        if self.note is not None:
            self.note = self.note.strip() or None
        return self


class DoctorScheduleResponse(BaseModel):
    """Availability slot representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doctor_id: UUID
    facility_id: UUID
    service_id: UUID | None
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: str
    busy_reason: str | None
    note: str | None
    version: int
    source_system: str | None
    external_schedule_id: str | None
    created_by: UUID | None
    updated_by: UUID | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleImportRecord(BaseModel):
    """One idempotent schedule import record."""

    doctor_id: UUID
    facility_id: UUID
    service_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=0)
    status: MutableScheduleStatus = "available"
    source_system: str = Field(min_length=1, max_length=64)
    external_schedule_id: str = Field(min_length=1, max_length=128)
    expected_version: int | None = Field(default=None, ge=1)
    busy_reason: Literal["consultation", "other_commitment"] | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleImportRecord":
        """Reject malformed imported time intervals without breaking legacy payloads."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


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
