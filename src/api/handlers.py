"""Backward-compatible imports for the centralized API exception handlers."""

from src.api.exception_handlers import (
    app_exception_handler,
    database_unavailable_handler,
    http_error_handler,
    register_exception_handlers,
    unexpected_error_handler,
    validation_error_handler,
)

app_error_handler = app_exception_handler

__all__ = [
    "app_error_handler",
    "app_exception_handler",
    "database_unavailable_handler",
    "http_error_handler",
    "register_exception_handlers",
    "unexpected_error_handler",
    "validation_error_handler",
]
