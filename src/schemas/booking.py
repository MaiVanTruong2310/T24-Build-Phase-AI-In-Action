"""Booking API request and response schemas."""

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

BookingStatus = Literal["pending_approval", "confirmed", "rejected", "cancelled"]
BookingHoldStatus = Literal["active", "released", "expired", "consumed"]
EncounterType = Literal["in_person", "telehealth"]


class BookingCreate(BaseModel):
    """Create a booking against a published schedule or request a time for staff review."""

    schedule_id: UUID | None = None
    hold_id: UUID | None = None
    doctor_id: UUID | None = None
    facility_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    service_id: UUID
    specialty_id: UUID
    encounter_type: EncounterType = "in_person"
    reason: str = Field(min_length=1, max_length=2000)
    patient_note: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only reasons before they reach persistence."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank")
        return normalized

    @field_validator("starts_at", "ends_at")
    @classmethod
    def normalize_datetime_to_utc(cls, value: datetime | None) -> datetime | None:
        """Require timezone-aware input and persist all requested times as UTC."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must include a timezone offset")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_slot_request(self) -> "BookingCreate":
        """Require either a real schedule or enough data for a requested time."""
        if self.schedule_id is None and not all((self.doctor_id, self.facility_id, self.starts_at, self.ends_at)):
            raise ValueError("schedule_id or doctor_id, facility_id, starts_at and ends_at is required")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.hold_id is not None and self.schedule_id is None:
            raise ValueError("hold_id requires schedule_id")
        return self


class BookingHoldCreate(BaseModel):
    """Request to reserve one available schedule for a short period."""

    schedule_id: UUID
    service_id: UUID
    specialty_id: UUID
    hold_seconds: int = Field(default=300, ge=300, le=600)


class BookingHoldResponse(BaseModel):
    """Temporary schedule reservation returned to the patient."""

    id: UUID
    user_id: UUID
    schedule_id: UUID
    service_id: UUID
    specialty_id: UUID
    status: BookingHoldStatus
    expires_at: datetime
    released_at: datetime | None
    created_at: datetime


class BookingCancelRequest(BaseModel):
    """Optional reason for cancelling an owned booking."""

    reason: str | None = Field(default=None, max_length=500)


class BookingRescheduleCreate(BaseModel):
    """Move an existing booking to a new held schedule for staff review."""

    schedule_id: UUID
    hold_id: UUID


class StaffBookingStatusUpdate(BaseModel):
    """Allowed staff decision for a booking awaiting review."""

    status: Literal["confirmed", "rejected"]
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Normalize optional staff notes and reject blank rejection notes."""
        return value.strip() if value else None


class BookingResponse(BaseModel):
    """Booking representation with schedule context for the client."""

    id: UUID
    user_id: UUID
    schedule_id: UUID | None
    hold_id: UUID | None = None
    service_id: UUID
    specialty_id: UUID
    doctor_id: UUID
    facility_id: UUID
    starts_at: datetime
    ends_at: datetime
    booking_mode: Literal["group", "doctor_visit"]
    encounter_type: EncounterType
    reason: str
    patient_note: str | None
    status: BookingStatus
    cancellation_reason: str | None
    staff_note: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StaffBookingResponse(BookingResponse):
    """Booking representation enriched for staff review queues."""

    patient_name: str | None
    patient_email: str | None
    patient_phone: str | None
    patient_date_of_birth: date | None
    patient_gender: str | None
    patient_citizen_id: str | None
    patient_health_insurance_code: str | None
    doctor_name: str | None
    doctor_title: str | None
    doctor_avatar: str | None
    specialty_name: str | None
    service_name: str | None
    facility_name: str | None
    facility_address: str | None
    room: str | None
