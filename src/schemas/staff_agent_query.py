"""Strict query-plan contracts for staff operational lookups."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class StaffQuerySubject(StrEnum):
    CATALOG = "catalog"
    AVAILABILITY = "availability"
    BOOKING_OPERATIONS = "booking_operations"
    CASE_OPERATIONS = "case_operations"


class StaffQueryOperator(StrEnum):
    EQUALS = "equals"
    CONTAINS = "contains"
    GTE = "gte"
    LTE = "lte"
    BETWEEN = "between"
    IN = "in"


class StaffQueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: StrictStr = Field(min_length=1, max_length=40)
    operator: StaffQueryOperator
    value: Any


class StaffQuerySort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: StrictStr = Field(min_length=1, max_length=40)
    direction: Literal["asc", "desc"]


class StaffQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: StaffQuerySubject
    select: list[StrictStr] = Field(min_length=1, max_length=8)
    filters: list[StaffQueryFilter] = Field(min_length=1, max_length=8)
    sort: list[StaffQuerySort] = Field(default_factory=list, max_length=1)
    limit: StrictInt = Field(default=10, ge=1, le=20)
