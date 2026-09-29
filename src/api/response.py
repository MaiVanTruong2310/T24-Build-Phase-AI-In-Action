"""Helpers for the unified API response envelope."""

from typing import TypeVar

from src.schemas.common import ApiError, ApiResponse

DataT = TypeVar("DataT")


def success_response(data: DataT, message: str = "Success", status: int = 200) -> ApiResponse[DataT]:
    """Build a successful API response."""
    return ApiResponse(data=data, message=message, status=status)


def error_response(
    code: int,
    message: str,
    status: int,
) -> ApiResponse[None]:
    """Build an error API response."""
    return ApiResponse(
        error=ApiError(code=code),
        message=message,
        status=status,
        data=None,
    )
