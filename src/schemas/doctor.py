"""Doctor request, assignment, and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.catalog_types import CatalogStatus, ReviewStatus
from src.schemas.facility import FacilityResponse
from src.schemas.service import ServiceResponse
from src.schemas.specialty import SpecialtyResponse


class DoctorFacilityAssignment(BaseModel):
    """Assign one facility to a doctor."""

    facility_id: UUID
    department: str | None = Field(default=None, max_length=160)
    room: str | None = Field(default=None, max_length=64)
    active_from: date | None = None
    active_to: date | None = None
    position: str | None = Field(default=None, max_length=160)
    is_primary: bool = False

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
    bio: str | None = None
    status: CatalogStatus = "active"
    review_status: ReviewStatus = "approved"
    booking_enabled: bool = True
    avatar_url: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=64)
    professional_role: str = Field(default="Bác sĩ", max_length=40)
    honors: list[str] = Field(default_factory=list)
    academic_ranks: list[str] = Field(default_factory=list)
    degrees: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    position: str | None = Field(default=None, max_length=160)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    education: list[str] = Field(default_factory=list)
    work_history: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
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
        if sum(item.is_primary for item in self.facilities) > 1:
            raise ValueError("Only one primary facility is allowed")
        return self

    @field_validator("honors", "academic_ranks", "degrees", "languages", "education", "work_history", "awards")
    @classmethod
    def clean_lists(cls, values: list[str], info) -> list[str]:
        clean = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        max_length = 80 if info.field_name in {"honors", "academic_ranks", "degrees", "languages"} else 500
        if len(clean) > 40 or any(len(value) > max_length for value in clean):
            raise ValueError("Too many or overly long profile entries")
        return clean


class DoctorUpdate(BaseModel):
    """Partially update a doctor profile."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    bio: str | None = None
    status: CatalogStatus | None = None
    review_status: ReviewStatus | None = None
    booking_enabled: bool | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=64)
    professional_role: str | None = Field(default=None, max_length=40)
    honors: list[str] | None = None
    academic_ranks: list[str] | None = None
    degrees: list[str] | None = None
    languages: list[str] | None = None
    position: str | None = Field(default=None, max_length=160)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    education: list[str] | None = None
    work_history: list[str] | None = None
    awards: list[str] | None = None
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
        if self.facilities and sum(item.is_primary for item in self.facilities) > 1:
            raise ValueError("Only one primary facility is allowed")
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
    position: str | None = None
    is_primary: bool = False
    facility: FacilityResponse | None = None


class DoctorSpecialtyResponse(BaseModel):
    """Specialty assignment with the resolved specialty resource."""

    specialty_id: UUID
    is_primary: bool
    specialty: SpecialtyResponse | None = None


class DoctorServiceResponse(BaseModel):
    """Service assignment with the resolved service resource."""

    service_id: UUID
    active: bool
    service: ServiceResponse | None = None


class DoctorResponse(BaseModel):
    """Doctor representation with assignment identifiers and resolved resources."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    full_name: str
    bio: str | None
    status: str
    review_status: str
    booking_enabled: bool
    avatar_url: str | None
    title: str | None
    professional_role: str = "Bác sĩ"
    honors: list[str] = Field(default_factory=list)
    academic_ranks: list[str] = Field(default_factory=list)
    degrees: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    position: str | None = None
    experience_years: int | None = None
    education: list[str] = Field(default_factory=list)
    work_history: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    specialty_ids: list[UUID] = Field(default_factory=list)
    specialties: list[DoctorSpecialtyResponse] = Field(default_factory=list)
    facilities: list[DoctorFacilityResponse] = Field(default_factory=list)
    facility_ids: list[UUID] = Field(default_factory=list)
    service_ids: list[UUID] = Field(default_factory=list)
    services: list[DoctorServiceResponse] = Field(default_factory=list)
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
