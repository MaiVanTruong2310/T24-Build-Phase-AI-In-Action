"""Specialty request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.catalog_types import CatalogBase, CatalogStatus


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
