"""Patient booking endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_patient
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.schemas.booking import BookingCancelRequest, BookingCreate, BookingResponse
from src.schemas.common import ApiResponse
from src.services.booking import BookingService, booking_response

router = APIRouter(prefix="/bookings", tags=["bookings"])


def get_booking_service(session: AsyncSession = Depends(get_db_session)) -> BookingService:
    """Build the booking service for the current request."""
    return BookingService(session)


@router.post("", response_model=ApiResponse[BookingResponse], status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreate,
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Create a confirmed booking for the authenticated patient."""
    value = await service.create(current_user.id, request)
    return success_response(booking_response(value), "Booking created", 201)


@router.get("", response_model=ApiResponse[list[BookingResponse]])
async def list_bookings(
    booking_status: str | None = Query(default=None, alias="status", pattern="^(confirmed|cancelled)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[list[BookingResponse]]:
    """List bookings owned by the authenticated patient."""
    values = await service.list(current_user.id, booking_status, offset, limit)
    return success_response([booking_response(value) for value in values], "Bookings retrieved")


@router.get("/{booking_id}", response_model=ApiResponse[BookingResponse])
async def get_booking(
    booking_id: UUID,
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Get one booking owned by the authenticated patient."""
    value = await service.get(current_user.id, booking_id)
    return success_response(booking_response(value), "Booking retrieved")


@router.post("/{booking_id}/cancel", response_model=ApiResponse[BookingResponse])
async def cancel_booking(
    booking_id: UUID,
    request: BookingCancelRequest | None = None,
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Cancel one booking owned by the authenticated patient."""
    value = await service.cancel(current_user.id, booking_id, request.reason if request else None)
    return success_response(booking_response(value), "Booking cancelled")
