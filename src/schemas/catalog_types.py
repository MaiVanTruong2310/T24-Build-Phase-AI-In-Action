"""Shared catalog schema types."""

from typing import Literal

from pydantic import BaseModel, Field

CatalogStatus = Literal["active", "inactive"]
BookingMode = Literal["group", "doctor_visit"]
ReviewStatus = Literal["needs_review", "approved", "rejected"]
ScheduleStatus = Literal["available", "inactive", "blocked", "cancelled"]
MutableScheduleStatus = Literal["available", "inactive", "blocked"]
ScheduleType = Literal["consultation", "busy", "leave", "other"]


class CatalogBase(BaseModel):
    """Shared fields for simple catalog resources."""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
