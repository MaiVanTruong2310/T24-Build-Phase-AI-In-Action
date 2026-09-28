"""Doctor request, assignment, and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.catalog_types import CatalogStatus, ReviewStatus


class DoctorFacilityAssignment(BaseModel):
    """Assign one facility to a doctor."""

    facility_id: UUID
    department: str | None = Field(default=None, max_length=160)
    room: str | None = Field(default=None, max_length=64)
    active_from: date | None = None
    active_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> DoctorFacilityAssignment:
        """Reject an assignment whose end predates its start."""
        if self.active_from and self.active_to and self.active_to < self.active_from:
            raise ValueError("active_to must be on or after active_from")
        return self


class DoctorCreate(BaseModel):
    """Create a doctor and optional catalog assignments."""

    code: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    license_number: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    bio: str | None = None
    status: CatalogStatus = "active"
    review_status: ReviewStatus = "approved"
    booking_enabled: bool = True
    avatar_url: str | None = Field(default=None, max_length=500)
    gender: str | None = Field(default=None, max_length=16)
    title: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    specialty_ids: list[UUID] = Field(default_factory=list)
    facilities: list[DoctorFacilityAssignment] = Field(default_factory=list)
    facility_ids: list[UUID] | None = None
    service_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_facility_ids(self) -> DoctorCreate:
        """Accept facility_ids and normalize it internally."""
        if self.facility_ids is not None:
            if self.facilities:
                raise ValueError("Provide either facility_ids or facilities, not both")
            self.facilities = [DoctorFacilityAssignment(facility_id=facility_id) for facility_id in self.facility_ids]
        return self


class DoctorUpdate(BaseModel):
    """Partially update a doctor profile."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    license_number: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    bio: str | None = None
    status: CatalogStatus | None = None
    review_status: ReviewStatus | None = None
    booking_enabled: bool | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    gender: str | None = Field(default=None, max_length=16)
    title: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    specialty_ids: list[UUID] | None = None
    facilities: list[DoctorFacilityAssignment] | None = None
    facility_ids: list[UUID] | None = None
    service_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def normalize_facility_ids(self) -> DoctorUpdate:
        """Accept facility_ids and normalize it internally."""
        if self.facility_ids is not None:
            if self.facilities:
                raise ValueError("Provide either facility_ids or facilities, not both")
            self.facilities = [DoctorFacilityAssignment(facility_id=facility_id) for facility_id in self.facility_ids]
        return self


class DoctorReviewRequest(BaseModel):
    """Set the publication review state of a doctor."""

    review_status: ReviewStatus


class DoctorFacilityResponse(BaseModel):
    """Facility assignment representation for a doctor."""

    model_config = ConfigDict(from_attributes=True)

    facility_id: UUID
    department: str | None
    room: str | None
    active_from: date | None
    active_to: date | None


class DoctorResponse(BaseModel):
    """Doctor representation with assignment identifiers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    full_name: str
    license_number: str | None
    email: str | None
    phone: str | None
    bio: str | None
    status: str
    review_status: str
    booking_enabled: bool
    avatar_url: str | None
    gender: str | None
    title: str | None
    date_of_birth: date | None
    specialty_ids: list[UUID] = Field(default_factory=list)
    facilities: list[DoctorFacilityResponse] = Field(default_factory=list)
    facility_ids: list[UUID] = Field(default_factory=list)
    service_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DoctorFacilityUpdate(BaseModel):
    """Update a doctor's facility assignment."""

    department: str | None = Field(default=None, max_length=160)
    room: str | None = Field(default=None, max_length=64)
    active_from: date | None = None
    active_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> DoctorFacilityUpdate:
        """Reject an assignment whose end predates its start."""
        if self.active_from and self.active_to and self.active_to < self.active_from:
            raise ValueError("active_to must be on or after active_from")
        return self


class DoctorSpecialtyAssignment(BaseModel):
    """Assign one specialty to a doctor."""

    specialty_id: UUID
    is_primary: bool = False


class DoctorServiceAssignment(BaseModel):
    """Assign one service to a doctor."""

    service_id: UUID
