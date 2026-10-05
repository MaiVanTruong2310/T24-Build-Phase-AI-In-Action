"""Centralized translation from application/framework exceptions to HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.error_codes import ErrorCode
from src.core.error_response import ErrorResponse
from src.core.exceptions import AppException
from src.core.logging import get_logger, log_event

logger = get_logger(__name__)


def _error_response(error_code: ErrorCode | str, message: str, status_code: int) -> JSONResponse:
    """Build the only error payload shape exposed by the API."""
    payload = ErrorResponse(error_code=str(error_code), message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _log_handled_exception(event: str, exc: Exception, status_code: int, description: str) -> None:
    """Log client errors as warnings and server errors with their traceback."""
    log_event(
        logger,
        logging.ERROR if status_code >= 500 else logging.WARNING,
        event,
        description=description,
        error_type=type(exc).__name__,
        error_code=getattr(exc, "error_code", None),
        status_code=status_code,
        exc_info=status_code >= 500,
    )


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """Return the public contract defined by a known application exception."""
    _log_handled_exception(
        "api.application_error",
        exc,
        exc.status_code,
        "A defined application exception was converted to an error response",
    )
    return _error_response(exc.error_code, exc.message, exc.status_code)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Hide field-level validation details behind one stable public message."""
    _log_handled_exception("api.validation_error", exc, 400, "Request validation failed")
    return _error_response(ErrorCode.VALIDATION_ERROR, "Request validation failed", 400)


def _http_error_code(status_code: int) -> ErrorCode:
    """Map common framework statuses to stable causes instead of exposing status numbers."""
    return {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        429: ErrorCode.RATE_LIMITED,
    }.get(status_code, ErrorCode.HTTP_ERROR)


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize framework HTTP errors without leaking server-side details."""
    is_server_error = exc.status_code >= 500
    _log_handled_exception(
        "api.http_error",
        exc,
        exc.status_code,
        "A framework HTTP exception was converted to an error response",
    )
    if is_server_error:
        return _error_response(ErrorCode.INTERNAL_ERROR, "Đã có lỗi xảy ra. Vui lòng thử lại sau.", exc.status_code)
    return _error_response(_http_error_code(exc.status_code), str(exc.detail), exc.status_code)


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a generic 500 response and keep the original traceback in server logs."""
    log_event(
        logger,
        logging.ERROR,
        "api.request.error",
        description="Unhandled API exception was converted to a generic error response",
        error_type=type(exc).__name__,
        exc_info=True,
    )
    return _error_response(ErrorCode.INTERNAL_ERROR, "Đã có lỗi xảy ra. Vui lòng thử lại sau.", 500)


async def database_unavailable_handler(_: Request, exc: OperationalError) -> JSONResponse:
    """Return a safe infrastructure error while retaining the database traceback in logs."""
    log_event(
        logger,
        logging.ERROR,
        "database.request.error",
        description="API request failed because the database was unavailable",
        error_type=type(exc).__name__,
        exc_info=True,
    )
    return _error_response(ErrorCode.DATABASE_UNAVAILABLE, "Service temporarily unavailable", 503)


def register_exception_handlers(app: FastAPI) -> None:
    """Register every API exception handler in one place."""
    app.add_exception_handler(OperationalError, database_unavailable_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
