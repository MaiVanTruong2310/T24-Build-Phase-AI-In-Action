import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
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
    database_unavailable_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from src.config import get_settings, parse_cors_origins
from src.core.exceptions import AppError
from src.core.logging import get_logger
from src.db.session import check_database_connection, close_database, get_session_factory, initialize_database
from src.medical_assistant.api.routes import router as medical_assistant_router
from src.medical_assistant.db.supabase_client import close_supabase_clients
from src.services.booking import BookingService
from src.services.cookie_session import CookieOriginMiddleware
from src.services.notification import NotificationService

logger = get_logger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _booking_maintenance_loop(interval_seconds: int) -> None:
    """Expire pending bookings and queue due reminders periodically."""
    while True:
        try:
            async with get_session_factory()() as session:
                expired_count = await BookingService(session).expire_pending_bookings()
                if expired_count:
                    logger.info("main.booking_expiration expired bookings", extra={"count": expired_count})
                notification_service = NotificationService(session)
                reminder_count = await notification_service.create_due_reminders()
                if reminder_count:
                    logger.info("main.notification_cleanup queued reminders", extra={"count": reminder_count})
                delivered_email_count = await notification_service.deliver_pending_emails()
                if delivered_email_count:
                    logger.info(
                        "main.notification_email delivered emails",
                        extra={"count": delivered_email_count},
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("main.booking_maintenance iteration failed")
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
    cleanup_task = None
    try:
        cleanup_task = asyncio.create_task(_booking_maintenance_loop(settings.booking_maintenance_interval_seconds))
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            await asyncio.gather(cleanup_task, return_exceptions=True)

        await close_database()
        close_supabase_clients()
        logger.info("Shutting down")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(CookieOriginMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(medical_assistant_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(booking_router, prefix="/api/v1")
app.include_router(staff_booking_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(catalog_staff_router, prefix="/api/v1")
app.add_exception_handler(OperationalError, database_unavailable_handler)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)


@app.get("/health")
async def health():
    """Return a lightweight service health response."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/health/ready")
async def readiness():
    """Report whether the API can execute a query on its configured database."""
    try:
        await check_database_connection()
    except Exception as exc:
        logger.warning("main.readiness database unavailable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready", "database": "connected"}
