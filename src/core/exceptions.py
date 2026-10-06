"""Application exceptions that are independent from the HTTP layer."""

from typing import Any

from src.core.error_codes import ErrorCode


def _code_value(value: ErrorCode | str) -> str:
    """Return the string value for an enum member or an existing public code."""
    return value.value if isinstance(value, ErrorCode) else str(value)


class AppException(Exception):  # noqa: N818 - name is part of the public exception design
    """Base exception translated by the centralized API exception handler."""

    status_code: int = 500
    error_code: ErrorCode | str = ErrorCode.INTERNAL_ERROR
    default_message: str = "Đã có lỗi xảy ra. Vui lòng thử lại sau."

    def __init__(
        self,
        message: str | None = None,
        *legacy_args: Any,
        error_code: ErrorCode | str | None = None,
        status_code: int | None = None,
        code: ErrorCode | str | None = None,
    ) -> None:
        """Initialize an application exception, retaining compatibility with old calls."""
        # Existing callers used (code, message[, status_code]). Accepting that shape
        # keeps the domain migration safe while all new exceptions use named fields.
        if legacy_args:
            legacy_code = message
            message = str(legacy_args[0])
            if error_code is None and legacy_code is not None:
                error_code = legacy_code
            if len(legacy_args) > 1 and status_code is None:
                status_code = int(legacy_args[1])

        self.error_code = _code_value(error_code or code or type(self).error_code)
        self.status_code = status_code if status_code is not None else type(self).status_code
        self.message = message or type(self).default_message
        super().__init__(self.message)

    @property
    def code(self) -> str:
        """Backward-compatible alias for code assertions in existing domain tests."""
        return self.error_code


class AuthenticationException(AppException):
    """Raised when authentication credentials are invalid or missing."""

    status_code = 401
    error_code = ErrorCode.UNAUTHORIZED
    default_message = "Authentication required"


class AuthorizationException(AppException):
    """Raised when an authenticated user lacks permission."""

    status_code = 403
    error_code = ErrorCode.FORBIDDEN
    default_message = "You do not have permission for this action"


class NotFoundException(AppException):
    """Raised when a requested resource does not exist or is not public."""

    status_code = 404
    error_code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"


class ConflictException(AppException):
    """Raised when a resource conflicts with the current business state."""

    status_code = 409
    error_code = ErrorCode.CONFLICT
    default_message = "The requested operation conflicts with the current state"


class RateLimitException(AppException):
    """Raised when a protected action is attempted too often."""

    status_code = 429
    error_code = ErrorCode.RATE_LIMITED
    default_message = "Too many attempts"


# Compatibility aliases allow the service migration to happen incrementally.
AppError = AppException
AuthenticationError = AuthenticationException
AuthorizationError = AuthorizationException
NotFoundError = NotFoundException
ConflictError = ConflictException
RateLimitError = RateLimitException
