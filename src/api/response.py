"""Helpers for successful API responses and the public error payload."""

from typing import TypeVar

from src.core.error_response import ErrorResponse
from src.schemas.common import ApiResponse

DataT = TypeVar("DataT")


def success_response(data: DataT, message: str = "Success", status: int = 200) -> ApiResponse[DataT]:
    """Build a successful API response."""
    return ApiResponse(data=data, message=message, status=status)


def error_response(
    error_code: str | int,
    message: str,
    status: int | None = None,
) -> ErrorResponse:
    """Build the stable error payload; status is accepted for migration compatibility."""
    del status
    return ErrorResponse(error_code=str(error_code), message=message)
