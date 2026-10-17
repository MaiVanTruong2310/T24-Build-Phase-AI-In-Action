"""The single error response schema exposed by the API."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Stable public error payload without internal implementation details."""

    error_code: str
    message: str
