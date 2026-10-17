"""Facility request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.catalog_types import CatalogBase, CatalogStatus


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
