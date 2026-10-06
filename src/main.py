import asyncio
import logging
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.auth import user_router
from src.api.endpoints.booking import router as booking_router
from src.api.endpoints.booking import staff_router as staff_booking_router
from src.api.endpoints.catalog import router as catalog_router
from src.api.endpoints.catalog import staff_router as catalog_staff_router
from src.api.endpoints.chat_takeover import router as chat_takeover_router
from src.api.endpoints.notification import router as notification_router
from src.api.exception_handlers import register_exception_handlers
from src.config import get_settings, parse_cors_origins
from src.core.context import session_id_var, trace_id_var
from src.core.logging import get_logger, log_event, setup_logging
from src.core.observability import setup_observability
from src.api.endpoints.coordination import router as coordination_router
from src.api.endpoints.coordination import staff_router as staff_coordination_router
from src.api.endpoints.notification import router as notification_router
from src.api.endpoints.package import router as package_router
from src.api.endpoints.package import staff_router as staff_package_router
from src.api.endpoints.workbench import patient_router as live_coordination_router
from src.api.endpoints.workbench import router as workbench_router
from src.api.endpoints.zalo import router as zalo_router
from src.api.handlers import (
    app_error_handler,
    database_unavailable_handler,
    http_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from src.config import allowed_cors_origins, get_settings
from src.core.exceptions import AppError
from src.core.logging import get_logger
from src.db.session import check_database_connection, close_database, get_session_factory, initialize_database
from src.medical_assistant.api.routes import router as medical_assistant_router
from src.medical_assistant.db.supabase_client import close_supabase_clients
from src.services.booking import BookingService
from src.services.cookie_session import CookieOriginMiddleware
from src.services.notification import NotificationService

logger = get_logger(__name__)
setup_logging()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _booking_hold_cleanup_loop(interval_seconds: int, stop_event: asyncio.Event | None = None) -> None:
    """Release expired booking holds periodically until application shutdown."""
    event = stop_event or asyncio.Event()
    while not event.is_set():
        try:
            async with get_session_factory()() as session:
                expired_count = await BookingService(session).expire_pending_bookings()
                if expired_count:
                    log_event(
                        logger,
                        logging.INFO,
                        "booking.maintenance.expired",
                        description="Maintenance expired bookings that missed staff approval deadlines",
                        count=expired_count,
                    )
                notification_service = NotificationService(session)
                reminder_count = await notification_service.create_due_reminders()
                if reminder_count:
                    log_event(
                        logger,
                        logging.INFO,
                        "notification.maintenance.reminders_queued",
                        description="Maintenance queued due appointment reminders",
                        count=reminder_count,
                    )
                delivered_email_count = await notification_service.deliver_pending_emails()
                if delivered_email_count:
                    log_event(
                        logger,
                        logging.INFO,
                        "notification.maintenance.emails_delivered",
                        description="Maintenance delivered pending notification emails",
                        count=delivered_email_count,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "booking.maintenance.error",
                description="Booking and notification maintenance iteration failed",
                error_type=type(exc).__name__,
                exc_info=True,
            )
        await asyncio.sleep(interval_seconds)
                released_count = await BookingService(session).release_expired_holds()
                if released_count:
                    logger.info("main.booking_hold_cleanup released holds", extra={"count": released_count})
                from src.services.workbench import expire_deposits, sync_sources
                async with session.begin():
                    await sync_sources(session)
                    await expire_deposits(session)
                reminder_count = await NotificationService(session).process_due_reminders()
                if reminder_count:
                    logger.info("main.notification_cleanup delivered reminders", extra={"count": reminder_count})
        except (asyncio.CancelledError, GeneratorExit):
            break
        except Exception as exc:
            task = asyncio.current_task()
            if event.is_set() or (task and task.cancelling()):
                break
            logger.warning("main.booking_hold_cleanup iteration warning: %s", exc)

        try:
            await asyncio.wait_for(event.wait(), timeout=min(interval_seconds, 30))
            break
        except asyncio.TimeoutError:
            pass
        except (asyncio.CancelledError, GeneratorExit):
            break


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log application startup and shutdown around the FastAPI lifespan."""
    settings = get_settings()
    log_event(
        logger,
        logging.INFO,
        "app.start",
        description="Application startup completed its initial configuration",
        app_name=settings.app_name,
        environment=settings.app_env,
    )
    if settings.database_auto_create:
        try:
            await initialize_database()
        except Exception as exc:
            log_event(
                logger,
                logging.CRITICAL,
                "database.initialize.error",
                description="Automatic database initialization failed during application startup",
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise
    stop_event = asyncio.Event()
    cleanup_task = None
    try:
        cleanup_task = asyncio.create_task(_booking_hold_cleanup_loop(settings.booking_hold_cleanup_interval_seconds, stop_event))
        yield
    finally:
        stop_event.set()
        if cleanup_task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(cleanup_task), timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                cleanup_task.cancel()
                await asyncio.gather(cleanup_task, return_exceptions=True)

        await close_database()
        close_supabase_clients()
        log_event(logger, logging.INFO, "app.stop", description="Application resources were closed during shutdown")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def context_middleware(request: Request, call_next):
    """Attach request correlation identifiers to every application log."""
    trace_token = trace_id_var.set(request.headers.get("X-Trace-Id") or uuid.uuid4().hex)
    session_token = session_id_var.set(request.headers.get("X-Session-Id") or "-")
    try:
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id_var.get()
        return response
    finally:
        trace_id_var.reset(trace_token)
        session_id_var.reset(session_token)


settings = get_settings()

@app.middleware("http")
async def coordination_capability(request, call_next):
    import secrets
    token = request.cookies.get("coordination_guest")
    valid = token and len(token) == 64 and all(c in "0123456789abcdef" for c in token)
    token = token if valid else secrets.token_hex(32)
    request.state.coordination_guest = token
    response = await call_next(request)
    if not valid and request.url.path.startswith(("/api/v1/chat", "/api/v1/booking-requests", "/api/v1/coordination/", "/api/v1/packages/")):
        secure = settings.auth_cookie_secure if settings.auth_cookie_secure is not None else settings.app_env == "production"
        response.set_cookie("coordination_guest", token, httponly=True, secure=secure, samesite=settings.auth_cookie_samesite, max_age=2592000, path="/")
    return response

app.add_middleware(CookieOriginMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(medical_assistant_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(workbench_router, prefix="/api/v1")
app.include_router(live_coordination_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(booking_router, prefix="/api/v1")
app.include_router(staff_booking_router, prefix="/api/v1")
app.include_router(coordination_router, prefix="/api/v1")
app.include_router(staff_coordination_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(chat_takeover_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(catalog_staff_router, prefix="/api/v1")
register_exception_handlers(app)
setup_observability(app)
app.include_router(staff_package_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(catalog_staff_router, prefix="/api/v1")
app.include_router(zalo_router, prefix="/api/v1")
app.add_exception_handler(OperationalError, database_unavailable_handler)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)


@app.get("/")
async def root():
    """Show API status and useful endpoints at the service root."""
    return {
        "service": "AI20K Agent API",
        "status": "ok",
        "health": "/health",
        "readiness": "/health/ready",
        "docs": "/docs",
    }


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
        log_event(
            logger,
            logging.WARNING,
            "database.readiness.error",
            description="Readiness check could not reach the configured database",
            error_type=type(exc).__name__,
        )
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready", "database": "connected"}
