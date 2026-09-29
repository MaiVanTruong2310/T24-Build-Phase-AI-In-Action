"""Authenticated booking endpoints and staff review endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_staff
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.schemas.booking import (
    BookingCancelRequest,
    BookingCreate,
    BookingResponse,
    StaffBookingResponse,
    StaffBookingStatusUpdate,
)
from src.schemas.common import ApiResponse
from src.services.booking import BookingService, booking_response, staff_booking_response

router = APIRouter(prefix="/bookings", tags=["bookings"])
staff_router = APIRouter(prefix="/staff/bookings", tags=["staff-bookings"])


def get_booking_service(session: AsyncSession = Depends(get_db_session)) -> BookingService:
    """Build the booking service for the current request."""
    return BookingService(session)


@router.post("", response_model=ApiResponse[BookingResponse], status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreate,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Create a pending booking for any authenticated user to be reviewed by staff."""
    value = await service.create(current_user.id, request)
    return success_response(booking_response(value), "Booking created", 201)


@router.get("", response_model=ApiResponse[list[BookingResponse]])
async def list_bookings(
    booking_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending_approval|confirmed|rejected|cancelled)$",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[list[BookingResponse]]:
    """List bookings owned by the authenticated user."""
    values = await service.list(current_user.id, booking_status, offset, limit)
    return success_response([booking_response(value) for value in values], "Bookings retrieved")


@router.get("/{booking_id}", response_model=ApiResponse[BookingResponse])
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Get one booking owned by the authenticated user."""
    value = await service.get(current_user.id, booking_id)
    return success_response(booking_response(value), "Booking retrieved")


@router.post("/{booking_id}/cancel", response_model=ApiResponse[BookingResponse])
async def cancel_booking(
    booking_id: UUID,
    request: BookingCancelRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Cancel one booking owned by the authenticated user."""
    value = await service.cancel(current_user.id, booking_id, request.reason if request else None)
    return success_response(booking_response(value), "Booking cancelled")


@staff_router.get("", response_model=ApiResponse[list[StaffBookingResponse]])
async def staff_list_bookings(
    booking_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending_approval|confirmed|rejected|cancelled)$",
    ),
    selected_date: date | None = Query(default=None, alias="date"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    _: User = Depends(require_staff),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[list[StaffBookingResponse]]:
    """List bookings for staff review, optionally filtered by status and date."""
    values = await service.list_for_staff(booking_status, selected_date, offset, limit)
    return success_response([staff_booking_response(value) for value in values], "Staff bookings retrieved")


@staff_router.get("/{booking_id}", response_model=ApiResponse[StaffBookingResponse])
async def staff_get_booking(
    booking_id: UUID,
    _: User = Depends(require_staff),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[StaffBookingResponse]:
    """Get one booking with patient and appointment context for staff review."""
    value = await service.get_for_staff(booking_id)
    return success_response(staff_booking_response(value), "Staff booking retrieved")


@staff_router.patch("/{booking_id}/status", response_model=ApiResponse[StaffBookingResponse])
async def staff_update_booking_status(
    booking_id: UUID,
    request: StaffBookingStatusUpdate,
    current_user: User = Depends(require_staff),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[StaffBookingResponse]:
    """Approve or reject one pending booking as staff."""
    value = await service.review(booking_id, current_user.id, request)
    return success_response(staff_booking_response(value), "Booking status updated")
