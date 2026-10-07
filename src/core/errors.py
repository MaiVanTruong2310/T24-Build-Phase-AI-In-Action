"""Exception-to-error translation and persistence failure helpers."""

import logging
from contextlib import asynccontextmanager
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from src.core.exceptions import AppException, ConflictError
from src.core.logging import log_event

INTERNAL_ERROR_MESSAGE = "Đã có lỗi xảy ra. Vui lòng thử lại sau."


def exception_message(exc: Exception) -> str:
    """Return a public message only for an explicitly defined application exception."""
    if isinstance(exc, AppException):
        return exc.message
    return INTERNAL_ERROR_MESSAGE


def raise_integrity_conflict(
    exc: IntegrityError,
    *,
    logger: logging.Logger,
    event: str,
    code: str,
    message: str,
    log_description: str | None = None,
    **context: str | None,
) -> NoReturn:
    """Log a database constraint failure and expose a business-safe conflict."""
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    log_event(
        logger,
        logging.ERROR,
        event,
        description=log_description or "A database constraint rejected the business operation",
        error_type=type(exc.orig).__name__,
        constraint_name=constraint_name,
        exc_info=True,
        **context,
    )
    raise ConflictError(code, message) from exc


@asynccontextmanager
async def integrity_guard(
    *,
    logger: logging.Logger,
    event: str,
    code: str,
    message: str,
    log_description: str | None = None,
    **context: str | None,
):
    """Convert an integrity failure raised inside one transaction scope."""
    try:
        yield
    except IntegrityError as exc:
        raise_integrity_conflict(
            exc,
            logger=logger,
            event=event,
            code=code,
            message=message,
            log_description=log_description,
            **context,
        )


@asynccontextmanager
async def savepoint(session):
    """Use a nested transaction when the session supports partial rollback."""
    begin_nested = getattr(session, "begin_nested", None)
    if begin_nested is None:
        yield
        return
    async with begin_nested():
        yield
