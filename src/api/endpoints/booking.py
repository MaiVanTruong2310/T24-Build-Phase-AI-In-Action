"""Authenticated booking endpoints and staff review endpoints."""

import hashlib
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, oauth2_scheme, require_patient, require_staff
from src.api.response import success_response
from src.core.exceptions import AuthenticationError, AuthorizationError, ConflictError, NotFoundError
from src.core.logging import get_logger
from src.db.dependencies import get_auth_db_session, get_db_session
from src.models.booking import Booking
from src.models.coordination import ConsultationRequest, ConsultationRequestEvent, ConsultationSession
from src.models.user import User
from src.models.workbench import CoordinationCase, CoordinationEvent
from src.models.workbench import CoordinationDeposit as Deposit
from src.schemas.booking import (
    BookingCancelRequest,
    BookingCreate,
    BookingHoldCreate,
    BookingHoldResponse,
    BookingRescheduleCreate,
    BookingResponse,
    StaffBookingResponse,
    StaffBookingStatusUpdate,
)
from src.schemas.common import ApiResponse
from src.services.booking import BookingService, booking_hold_response
from src.services.workbench import release_hold
from src.utils.response_mappers import booking_response, staff_booking_response

logger = get_logger(__name__)

router = APIRouter(prefix="/bookings", tags=["bookings"])
staff_router = APIRouter(prefix="/staff/bookings", tags=["staff-bookings"])


async def require_patient_for_hold(
    request: Request,
    session: AsyncSession = Depends(get_auth_db_session),
) -> User:
    """Authenticate hold requests while preserving the legacy hold error shape.

    The booking hold endpoint predates the unified error envelope and is still
    consumed by clients that read ``error.code``.  Keep that compatibility
    only for this endpoint; all other APIs continue using the stable
    ``error_code`` contract.
    """
    try:
        token = await oauth2_scheme(request)
        user = await get_current_user(token, session)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail={"legacy_error": {"code": 401}}) from exc
    if user.role != "patient":
        raise AuthorizationError()
    return user


def get_booking_service(session: AsyncSession = Depends(get_db_session)) -> BookingService:
    """Build the booking service for the current request."""
    return BookingService(session)


async def _get_owned_case(
    session: AsyncSession,
    case_id: UUID,
    user_id: UUID,
    user_key: str,
    guest_token: str | None = None,
    for_update: bool = False,
) -> CoordinationCase | None:
    owner_conditions = [
        CoordinationCase.patient_id == user_id,
        CoordinationCase.owner_key == user_key,
    ]
    if guest_token:
        guest_key = f"guest:{hashlib.sha256(guest_token.encode()).hexdigest()}"
        owner_conditions.append(CoordinationCase.owner_key == guest_key)

    stmt = select(CoordinationCase).where(
        CoordinationCase.id == case_id,
        or_(*owner_conditions),
    )
    if for_update:
        stmt = stmt.with_for_update()
    return (await session.execute(stmt)).scalar_one_or_none()


def _case_to_booking_response(
    case: CoordinationCase,
    user_id: UUID,
    cancellation_reason: str | None = None,
) -> BookingResponse:
    pref_date = case.patient.get("preferred_date") if case.patient else None
    pref_period = case.patient.get("preferred_period") if case.patient else None
    time_str = "T13:30:00+07:00" if pref_period == "afternoon" else "T08:30:00+07:00"

    starts_at = None
    if pref_date:
        try:
            iso_str = pref_date if "T" in pref_date else f"{pref_date}{time_str}"
            starts_at = datetime.fromisoformat(iso_str)
        except Exception:
            starts_at = case.created_at
    else:
        starts_at = case.created_at

    status_map = {
        "new": "pending_approval",
        "contacting": "pending_approval",
        "waiting_patient": "pending_approval",
        "waiting_deposit": "pending_approval",
        "deposit_verified": "pending_approval",
        "confirmed": "confirmed",
        "completed": "confirmed",
        "cancelled": "cancelled",
    }
    booking_status = status_map.get(case.status, "pending_approval")
    reason = (
        case.patient.get("notes") or (case.ai_snapshot or {}).get("symptoms") or "Khám chuyên khoa theo định hướng AI"
    )
    patient_note = f"Phiếu điều phối AI: {case.patient.get('name', '')} - SĐT: {case.patient.get('phone', '')} - Cơ sở: {case.patient.get('facility_preference', 'Vinmec Riverside')}"

    return BookingResponse(
        id=case.id,
        user_id=case.patient_id or user_id,
        schedule_id=None,
        hold_id=None,
        service_id=None,
        specialty_id=None,
        doctor_id=None,
        facility_id=case.facility_id,
        starts_at=starts_at,
        ends_at=starts_at,
        booking_mode="doctor_visit",
        encounter_type="in_person",
        reason=reason,
        patient_note=patient_note,
        status=booking_status,
        cancellation_reason=cancellation_reason or (case.patient or {}).get("cancellation_reason"),
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("", response_model=ApiResponse[BookingResponse], status_code=status.HTTP_201_CREATED)
async def create_booking(
    request: BookingCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Create a pending booking exactly once after consuming a valid hold."""
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    value, replay = await service.create_idempotent(current_user.id, request, idempotency_key)
    if replay:
        response.status_code = status.HTTP_200_OK
        return success_response(booking_response(value), "Booking replayed")
    return success_response(booking_response(value), "Booking created", 201)


@router.post("/hold", response_model=ApiResponse[BookingHoldResponse], status_code=status.HTTP_201_CREATED)
async def create_booking_hold(
    request: BookingHoldCreate,
    current_user: User = Depends(require_patient_for_hold),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingHoldResponse]:
    """Reserve one available schedule before the patient confirms a booking."""
    value = await service.hold(current_user.id, request)
    return success_response(booking_hold_response(value), "Booking hold created", 201)


@router.delete("/holds/{hold_id}", response_model=ApiResponse[None])
async def release_booking_hold(
    hold_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[None]:
    """Release a patient's hold, or let staff release an operational hold."""
    await service.release_hold(current_user.id, hold_id, is_staff=current_user.role == "staff")
    return success_response(None, "Booking hold released")


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
    http_request: Request,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Get one booking owned by the authenticated user."""
    user_id = current_user.id
    user_key = f"user:{user_id}"
    guest_token = getattr(getattr(http_request, "state", None), "coordination_guest", None)

    existing_booking = await service.bookings.get_for_user(booking_id, user_id)
    if existing_booking is not None:
        return success_response(booking_response(existing_booking), "Booking retrieved")

    case = await _get_owned_case(service.session, booking_id, user_id, user_key, guest_token)
    if case is None:
        raise NotFoundError("Booking not found")
    return success_response(_case_to_booking_response(case, user_id), "Booking retrieved")


@router.post("/{booking_id}/cancel", response_model=ApiResponse[BookingResponse])
async def cancel_booking(
    booking_id: UUID,
    http_request: Request,
    request: BookingCancelRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Cancel one booking or intake coordination case owned by the authenticated user."""
    user_id = current_user.id
    user_key = f"user:{user_id}"
    guest_token = getattr(getattr(http_request, "state", None), "coordination_guest", None)
    reason = request.reason if request else None

    # 1. Check if booking exists as a direct Booking
    booking = await service.bookings.get_for_user(booking_id, user_id, for_update=True)
    if booking is not None:
        if booking.status == "cancelled":
            raise ConflictError("BOOKING_ALREADY_CANCELLED", "Booking is already cancelled")
        if booking.status == "rejected":
            raise ConflictError("BOOKING_NOT_CANCELLABLE", "Rejected booking cannot be cancelled")
        booking.status = "cancelled"
        booking.cancellation_reason = reason.strip() if reason else None
        consultation = (
            await service.session.execute(
                select(ConsultationRequest)
                .where(
                    ConsultationRequest.booking_id == booking.id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if consultation is not None:
            await service.session.execute(
                select(ConsultationSession.id)
                .where(
                    ConsultationSession.id == consultation.session_id,
                )
                .with_for_update()
            )
            consultation.status = "cancelled"
            service.session.add(
                ConsultationRequestEvent(
                    request_id=consultation.id,
                    actor_id=user_id,
                    action="cancelled",
                    note=booking.cancellation_reason,
                )
            )
        resp = booking_response(booking)
        await service.session.commit()
        logger.info("cancel_booking: booking cancelled", extra={"booking_id": str(booking_id)})
        return success_response(resp, "Booking cancelled")

    # 2. Otherwise, check and cancel as an owned CoordinationCase
    case = await _get_owned_case(service.session, booking_id, user_id, user_key, guest_token, for_update=True)
    if case is None:
        raise NotFoundError("Booking not found")

    if case.status == "cancelled":
        raise ConflictError("BOOKING_ALREADY_CANCELLED", "Lịch hẹn đã được hủy trước đó")
    if case.status == "completed":
        raise ConflictError("BOOKING_NOT_CANCELLABLE", "Lịch hẹn đã hoàn tất, không thể hủy")

    await release_hold(service.session, case)
    deposits = (
        (
            await service.session.execute(
                select(Deposit).where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "verified"]))
            )
        )
        .scalars()
        .all()
    )
    for deposit in deposits:
        deposit.status = "refund_pending" if deposit.status == "verified" else "voided"

    if case.booking_id:
        direct_booking = await service.session.get(Booking, case.booking_id, with_for_update=True)
        if direct_booking and direct_booking.status != "cancelled":
            direct_booking.status = "cancelled"
            direct_booking.cancellation_reason = reason.strip() if reason else None
            await service.notifications.discard_reminders_for_booking(direct_booking.id)

    case.status = "cancelled"
    case.control = "ai"
    case.follow_up_at = None
    patient_data = dict(case.patient or {})
    if reason:
        patient_data["cancellation_reason"] = reason.strip()
    case.patient = patient_data
    case.version += 1
    service.session.add(
        CoordinationEvent(
            case_id=case.id,
            actor_id=user_id,
            action="patient_cancelled",
            note=reason or "",
            details={},
        )
    )
    response_data = _case_to_booking_response(case, user_id, reason)
    await service.session.commit()

    logger.info("cancel_booking: coordination case cancelled", extra={"case_id": str(booking_id)})
    return success_response(response_data, "Booking cancelled")


@router.post("/{booking_id}/reschedule", response_model=ApiResponse[BookingResponse])
async def reschedule_booking(
    booking_id: UUID,
    request: BookingRescheduleCreate,
    current_user: User = Depends(require_patient),
    service: BookingService = Depends(get_booking_service),
) -> ApiResponse[BookingResponse]:
    """Move a patient booking to a held schedule and return it to staff review."""
    value = await service.reschedule(current_user.id, booking_id, request)
    return success_response(booking_response(value), "Booking rescheduled")


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
    return success_response(staff_booking_response(value), "Staff booking reviewed")
