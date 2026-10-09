"""Response schemas for staff patient search."""

from datetime import date, datetime
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
