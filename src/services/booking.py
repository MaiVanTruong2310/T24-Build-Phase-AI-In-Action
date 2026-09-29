"""Patient booking business rules."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.booking import Booking
from src.repositories.booking import BookingRepository
from src.schemas.booking import BookingCreate, BookingResponse

logger = get_logger(__name__)


class BookingService:
    """Create and manage direct-confirmed patient bookings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bookings = BookingRepository(session)

    async def create(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Create one booking while serializing writes for its schedule."""
        async with self.session.begin():
            schedule = await self.bookings.get_schedule_for_update(request.schedule_id)
            if schedule is None:
                raise NotFoundError("Schedule not found")
            self._validate_schedule(schedule)

            service = await self.bookings.get_service(request.service_id)
            if service is None or service.status != "active":
                raise NotFoundError("Service not found")
            specialty = await self.bookings.get_specialty(request.specialty_id)
            if specialty is None or specialty.status != "active":
                raise NotFoundError("Specialty not found")
            if not await self.bookings.has_doctor_service(schedule.doctor_id, service.id):
                raise ConflictError("SERVICE_NOT_AVAILABLE", "Service is not available for this doctor")
            if not await self.bookings.has_doctor_specialty(schedule.doctor_id, specialty.id):
                raise ConflictError("SPECIALTY_NOT_AVAILABLE", "Specialty is not available for this doctor")

            active_count = await self.bookings.count_active_for_schedule(schedule.id)
            if service.booking_mode == "doctor_visit" and active_count >= 1:
                raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
            if service.booking_mode == "group" and active_count >= schedule.capacity:
                raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")

            booking = Booking(
                user_id=user_id,
                schedule_id=schedule.id,
                service_id=service.id,
                specialty_id=specialty.id,
                encounter_type=request.encounter_type,
                reason=request.reason.strip(),
                patient_note=request.patient_note.strip() if request.patient_note else None,
                status="confirmed",
            )
            await self.bookings.add(booking)
        logger.info("BookingService.create booking confirmed", extra={"booking_id": str(booking.id)})
        return await self.get(user_id, booking.id)

    async def list(self, user_id: UUID, status: str | None, offset: int, limit: int) -> list[Booking]:
        """List bookings owned by a patient."""
        return await self.bookings.list_for_user(user_id, status, offset, limit)

    async def get(self, user_id: UUID, booking_id: UUID) -> Booking:
        """Get one booking owned by a patient."""
        booking = await self.bookings.get_for_user(booking_id, user_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def cancel(self, user_id: UUID, booking_id: UUID, reason: str | None) -> Booking:
        """Cancel an owned booking without deleting its history."""
        async with self.session.begin():
            booking = await self.bookings.get_for_user(booking_id, user_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status == "cancelled":
                raise ConflictError("BOOKING_ALREADY_CANCELLED", "Booking is already cancelled")
            booking.status = "cancelled"
            booking.cancellation_reason = reason.strip() if reason else None
            await self.session.flush()
        logger.info("BookingService.cancel booking cancelled", extra={"booking_id": str(booking_id)})
        return await self.get(user_id, booking_id)

    @staticmethod
    def _validate_schedule(schedule) -> None:
        """Validate public schedule state before counting capacity."""
        if schedule.status != "available":
            raise ConflictError("SCHEDULE_UNAVAILABLE", "Schedule is not available")
        if schedule.capacity <= 0:
            raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
        if schedule.doctor.status != "active" or schedule.doctor.review_status != "approved":
            raise ConflictError("DOCTOR_UNAVAILABLE", "Doctor is not available for booking")
        if not schedule.doctor.booking_enabled:
            raise ConflictError("DOCTOR_BOOKING_DISABLED", "Doctor booking is disabled")
        if schedule.facility.status != "active":
            raise ConflictError("FACILITY_UNAVAILABLE", "Facility is not available for booking")


def booking_response(value: Booking) -> BookingResponse:
    """Map a loaded booking to its stable API representation."""
    return BookingResponse(
        id=value.id,
        user_id=value.user_id,
        schedule_id=value.schedule_id,
        service_id=value.service_id,
        specialty_id=value.specialty_id,
        doctor_id=value.schedule.doctor_id,
        facility_id=value.schedule.facility_id,
        starts_at=value.schedule.starts_at,
        ends_at=value.schedule.ends_at,
        booking_mode=value.service.booking_mode,
        encounter_type=value.encounter_type,
        reason=value.reason,
        patient_note=value.patient_note,
        status=value.status,
        cancellation_reason=value.cancellation_reason,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )
