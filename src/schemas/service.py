"""Medical service request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.catalog_types import BookingMode, CatalogBase, CatalogStatus


class ServiceCreate(CatalogBase):
    """Create a medical service."""

    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price: float | None = Field(default=None, ge=0)
    original_price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    features: list[str] | None = Field(default=None)
    booking_mode: BookingMode = "group"


class ServiceUpdate(BaseModel):
    """Partially update a medical service."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price: float | None = Field(default=None, ge=0)
    original_price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    features: list[str] | None = Field(default=None)
    booking_mode: BookingMode | None = None
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
    booking_mode: BookingMode
    patient_count: int | None
    satisfaction_rate: float | None
    status: str
    created_at: datetime
    updated_at: datetime
