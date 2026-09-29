"""Booking API request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

BookingStatus = Literal["confirmed", "cancelled"]
EncounterType = Literal["in_person", "telehealth"]


class BookingCreate(BaseModel):
    """Create a booking for one selected schedule."""

    schedule_id: UUID
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


class BookingCancelRequest(BaseModel):
    """Optional reason for cancelling an owned booking."""

    reason: str | None = Field(default=None, max_length=500)


class BookingResponse(BaseModel):
    """Booking representation with schedule context for the client."""

    id: UUID
    user_id: UUID
    schedule_id: UUID
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
    created_at: datetime
    updated_at: datetime
