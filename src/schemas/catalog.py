"""Medical catalog request and response schemas."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CatalogStatus = Literal["active", "inactive"]
ReviewStatus = Literal["needs_review", "approved", "rejected"]
ScheduleStatus = Literal["available", "inactive", "blocked"]


class CatalogBase(BaseModel):
    """Shared fields for simple catalog resources."""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class SpecialtyCreate(CatalogBase):
    """Create a specialty."""


class SpecialtyUpdate(BaseModel):
    """Partially update a specialty."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: CatalogStatus | None = None


class SpecialtyResponse(CatalogBase):
    """Public specialty representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class FacilityCreate(CatalogBase):
    """Create a facility."""

    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)


class FacilityUpdate(BaseModel):
    """Partially update a facility."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    status: CatalogStatus | None = None


class FacilityResponse(BaseModel):
    """Public facility representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    address: str | None
    phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ServiceCreate(CatalogBase):
    """Create a medical service."""

    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price: float | None = Field(default=None, ge=0)
    original_price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    features: list[str] | None = Field(default=None)


class ServiceUpdate(BaseModel):
    """Partially update a medical service."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price: float | None = Field(default=None, ge=0)
    original_price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    features: list[str] | None = Field(default=None)
    status: CatalogStatus | None = None


class ServiceResponse(BaseModel):
    """Public service representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    duration_minutes: int | None
    price: float | None
    original_price: float | None
    category: str | None
    features: list[str] | None
    patient_count: int | None
    satisfaction_rate: float | None
    status: str
    created_at: datetime
    updated_at: datetime


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
    facilities: list["DoctorFacilityAssignment"] = Field(default_factory=list)
    facility_ids: list[UUID] | None = None
    service_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_facility_ids(self) -> "DoctorCreate":
        """Accept the public facility_ids contract and normalize it internally."""
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
    facilities: list["DoctorFacilityAssignment"] | None = None
    facility_ids: list[UUID] | None = None
    service_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def normalize_facility_ids(self) -> "DoctorUpdate":
        """Accept the public facility_ids contract and normalize it internally."""
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
    def validate_date_range(self) -> "DoctorFacilityUpdate":
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


class DoctorFacilityAssignment(BaseModel):
    """Assign one facility to a doctor."""

    facility_id: UUID
    department: str | None = Field(default=None, max_length=160)
    room: str | None = Field(default=None, max_length=64)
    active_from: date | None = None
    active_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "DoctorFacilityAssignment":
        """Reject an assignment whose end predates its start."""
        if self.active_from and self.active_to and self.active_to < self.active_from:
            raise ValueError("active_to must be on or after active_from")
        return self


class DoctorScheduleCreate(BaseModel):
    """Create an availability slot."""

    doctor_id: UUID
    facility_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=0)
    status: ScheduleStatus = "available"
    source_system: str | None = Field(default=None, max_length=64)
    external_schedule_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleCreate":
        """Reject a slot whose end is not after its start."""
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class DoctorScheduleUpdate(BaseModel):
    """Update a slot using optimistic-lock versioning."""

    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = Field(default=None, ge=0)
    status: ScheduleStatus | None = None
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> "DoctorScheduleUpdate":
        """Validate a complete time range when both bounds are provided."""
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
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
    status: str
    version: int
    source_system: str | None
    external_schedule_id: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleImportRecord(DoctorScheduleCreate):
    """One idempotent schedule import record."""

    source_system: str = Field(min_length=1, max_length=64)
    external_schedule_id: str = Field(min_length=1, max_length=128)
    expected_version: int | None = Field(default=None, ge=1)


class BulkScheduleImportRequest(BaseModel):
    """JSON batch payload with per-record validation in the service layer."""

    records: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


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


class CatalogAuditResponse(BaseModel):
    """Audit history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: UUID
    action: str
    payload: dict
    created_at: datetime
