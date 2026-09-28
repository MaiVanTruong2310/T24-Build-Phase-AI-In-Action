"""Public availability and staff schedule endpoints."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends, Query, status

from src.api.dependencies import get_current_user, require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.models.user import User
from src.schemas.catalog import (
    BulkImportResponse,
    BulkScheduleImportRequest,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
    ScheduleCancellationRequest,
    ScheduleStatus,
)
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService

BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/doctors/{doctor_id}/availability", response_model=ApiResponse[list[DoctorScheduleResponse]])
async def doctor_availability(
    doctor_id: UUID,
    facility_id: UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    selected_date: date | None = Query(default=None, alias="date"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorScheduleResponse]]:
    """Return only available slots with positive capacity."""
    starts_from, starts_to = _availability_window(from_date, to_date, selected_date)
    values = await service.list_schedules(
        doctor_id=doctor_id,
        facility_id=facility_id,
        starts_from=starts_from,
        starts_to=starts_to,
        public_only=True,
        offset=offset,
        limit=limit,
    )
    return success_response(
        [DoctorScheduleResponse.model_validate(value) for value in values], "Availability retrieved"
    )


@staff_router.get("/schedules", response_model=ApiResponse[list[DoctorScheduleResponse]])
async def staff_list_schedules(
    doctor_id: UUID | None = None,
    facility_id: UUID | None = None,
    schedule_status: ScheduleStatus | None = Query(default=None, alias="status"),
    source_system: str | None = Query(default=None, max_length=64),
    starts_from: datetime | None = Query(default=None, alias="from"),
    starts_to: datetime | None = Query(default=None, alias="to"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorScheduleResponse]]:
    """List staff schedules with filters and offset pagination."""
    values = await service.list_schedules(
        doctor_id=doctor_id,
        facility_id=facility_id,
        starts_from=starts_from,
        starts_to=starts_to,
        schedule_status=schedule_status,
        source_system=source_system,
        public_only=False,
        offset=offset,
        limit=limit,
    )
    return success_response([DoctorScheduleResponse.model_validate(value) for value in values], "Schedules retrieved")


@staff_router.post(
    "/schedules", response_model=ApiResponse[DoctorScheduleResponse], status_code=status.HTTP_201_CREATED
)
async def staff_create_schedule(
    request: DoctorScheduleCreate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorScheduleResponse]:
    """Create a schedule as staff."""
    value = await service.create_schedule(request, current_user.id)
    return success_response(DoctorScheduleResponse.model_validate(value), "Schedule created", 201)


@staff_router.put("/schedules/{schedule_id}", response_model=ApiResponse[DoctorScheduleResponse])
async def staff_update_schedule(
    schedule_id: UUID,
    request: DoctorScheduleUpdate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorScheduleResponse]:
    """Replace mutable schedule fields as staff."""
    value = await service.update_schedule(schedule_id, request, current_user.id)
    return success_response(DoctorScheduleResponse.model_validate(value), "Schedule updated")


@staff_router.post("/schedules/import", response_model=ApiResponse[BulkImportResponse])
async def staff_import_schedules(
    request: BulkScheduleImportRequest,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[BulkImportResponse]:
    """Import schedules with per-record results."""
    value = await service.bulk_import_schedules(request, current_user.id)
    return success_response(value, "Schedules imported")


@staff_router.delete("/schedules/{schedule_id}/cancel", response_model=ApiResponse[DoctorScheduleResponse])
async def staff_cancel_schedule(
    schedule_id: UUID,
    request: ScheduleCancellationRequest,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorScheduleResponse]:
    """Cancel a schedule without deleting its database row."""
    value = await service.cancel_schedule(schedule_id, request, current_user.id)
    return success_response(DoctorScheduleResponse.model_validate(value), "Schedule cancelled")


def _to_utc_start(value: date) -> datetime:
    """Convert a Vietnam local date midnight to UTC."""
    return datetime.combine(value, time.min, tzinfo=BUSINESS_TZ).astimezone(UTC)


def _availability_window(
    from_date: date | None,
    to_date: date | None,
    selected_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    """Normalize date filters to UTC boundaries in the business timezone."""
    if selected_date:
        return _to_utc_start(selected_date), _to_utc_start(selected_date + timedelta(days=1))
    starts_from = _to_utc_start(from_date) if from_date else None
    starts_to = _to_utc_start(to_date + timedelta(days=1)) if to_date else None
    return starts_from, starts_to
