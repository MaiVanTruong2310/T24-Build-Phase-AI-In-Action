"""Response schemas for staff patient search."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StaffPatientListItem(BaseModel):
    """Minimal patient fields suitable for a staff search result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str | None
    email: str | None
    phone: str | None
    status: str
    gender: str | None
    created_at: datetime


class StaffPatientPage(BaseModel):
    """Offset-paginated patient search response data."""

    items: list[StaffPatientListItem]
    total: int
    offset: int
    limit: int


class StaffPatientDetail(BaseModel):
    """Allowlisted patient profile fields; identifiers are pre-masked server-side."""

    id: UUID
    full_name: str | None
    email: str | None
    phone: str | None
    status: str
    gender: str | None
    date_of_birth: date | None
    citizen_id_masked: str | None
    health_insurance_code_masked: str | None


class StaffPatientProfileSummary(BaseModel):
    """Allowlisted related patient profile fields for staff assistant context."""

    id: UUID
    full_name: str | None
    date_of_birth: date | None
    gender: str | None
    contact_phone: str | None
    citizen_id_masked: str | None
    health_insurance_code_masked: str | None
    address: str | None


class StaffPatientAgentDetail(BaseModel):
    """Curated staff assistant patient context with arbitrary JSON excluded."""

    id: UUID
    full_name: str | None
    email: str | None
    phone: str | None
    status: str
    gender: str | None
    date_of_birth: date | None
    patient_profiles: list[StaffPatientProfileSummary]
    patient_details: dict[str, Any]
