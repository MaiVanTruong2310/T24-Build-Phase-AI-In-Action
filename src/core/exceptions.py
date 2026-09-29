"""Application-level exception types and stable error codes."""


class AppError(Exception):
    """Base exception for expected application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
    ) -> None:
        """Initialize an application error with a stable code and HTTP status."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AuthenticationError(AppError):
    """Raised when authentication credentials are invalid or missing."""

    def __init__(self, code: str = "UNAUTHORIZED", message: str = "Authentication required") -> None:
        """Initialize an authentication failure."""
        super().__init__(code, message, 401)


class AuthorizationError(AppError):
    """Raised when an authenticated user lacks permission."""

    def __init__(self, message: str = "You do not have permission for this action") -> None:
        """Initialize an authorization failure."""
        super().__init__("FORBIDDEN", message, 403)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist or is not public."""

    def __init__(self, message: str = "Resource not found") -> None:
        """Initialize a not-found error."""
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(AppError):
    """Raised when a resource conflicts with current state."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize a conflict with a stable application code."""
        super().__init__(code, message, 409)


class RateLimitError(AppError):
    """Raised when a protected action is attempted too often."""

    def __init__(self, message: str = "Too many attempts") -> None:
        """Initialize a rate-limit failure."""
        super().__init__("RATE_LIMITED", message, 429)
