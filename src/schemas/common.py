"""Shared API response envelope schemas."""

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiError(BaseModel):
    """Stable machine-readable error payload."""

    code: int


class ApiResponse(BaseModel, Generic[DataT]):
    """Unified success and error response envelope."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error: ApiError | None = None
    message: str
    status: int
    data: DataT | None = None
