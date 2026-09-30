import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.auth import user_router
from src.api.endpoints.booking import router as booking_router
from src.api.endpoints.booking import staff_router as staff_booking_router
from src.api.endpoints.catalog import router as catalog_router
from src.api.endpoints.catalog import staff_router as catalog_staff_router
from src.api.endpoints.notification import router as notification_router
from src.api.handlers import (
    app_error_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from src.api.routes import router
from src.config import get_settings
from src.core.exceptions import AppError
from src.core.logging import get_logger
from src.db.session import get_session_factory, initialize_database
from src.services.booking import BookingService
from src.services.notification import NotificationService

logger = get_logger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _booking_hold_cleanup_loop(interval_seconds: int) -> None:
    """Release expired booking holds periodically until application shutdown."""
    while True:
        try:
            async with get_session_factory()() as session:
                released_count = await BookingService(session).release_expired_holds()
                if released_count:
                    logger.info("main.booking_hold_cleanup released holds", extra={"count": released_count})
                reminder_count = await NotificationService(session).process_due_reminders()
                if reminder_count:
                    logger.info("main.notification_cleanup delivered reminders", extra={"count": reminder_count})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("main.booking_hold_cleanup iteration failed")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log application startup and shutdown around the FastAPI lifespan."""
    settings = get_settings()
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    if settings.database_auto_create:
        try:
            await initialize_database()
        except Exception:
            logger.exception("main.lifespan database initialization failed")
            raise
    cleanup_task = asyncio.create_task(_booking_hold_cleanup_loop(settings.booking_hold_cleanup_interval_seconds))
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        logger.info("Shutting down")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(booking_router, prefix="/api/v1")
app.include_router(staff_booking_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(catalog_staff_router, prefix="/api/v1")
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)


@app.get("/health")
async def health():
    """Return a lightweight service health response."""
    return {"status": "ok", "env": settings.app_env}
