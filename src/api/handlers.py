"""FastAPI exception handlers for the API response contract."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.response import error_response
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)

SUPPORTED_CLIENT_ERROR_CODES = frozenset({400, 401, 403, 404, 408, 409, 429})


def _public_error_code(status: int) -> int:
    """Return the allowed public error code for an HTTP status."""
    if status in SUPPORTED_CLIENT_ERROR_CODES:
        return status
    if 400 <= status < 500:
        return 400
    return 500


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Serialize a known application error using the shared response envelope."""
    response = error_response(_public_error_code(exc.status_code), exc.message, exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=response.model_dump(mode="json"))


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Serialize request validation failures without exposing field details."""
    del exc
    response = error_response(400, "Request validation failed", 400)
    return JSONResponse(status_code=400, content=response.model_dump(mode="json"))


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Map framework HTTP errors to the shared response envelope."""
    is_server_error = exc.status_code >= 500
    code = 500 if is_server_error else _public_error_code(exc.status_code)
    message = "Internal server error" if is_server_error else str(exc.detail)
    response = error_response(code, message, exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=response.model_dump(mode="json"))


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a safe envelope while preserving the server-side traceback."""
    logger.exception("unexpected_error_handler unhandled API exception", exc_info=exc)
    response = error_response(500, "Internal server error", 500)
    return JSONResponse(status_code=500, content=response.model_dump(mode="json"))


async def database_unavailable_handler(_: Request, exc: Exception) -> JSONResponse:
    """Handle connection failures inside ExceptionMiddleware so CORS is preserved."""
    logger.warning("API database unavailable: %s", type(exc).__name__)
    response = error_response(
        500,
        "Hệ thống tạm thời không thể truy cập dữ liệu. Vui lòng thử lại sau.",
        503,
    )
    return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
