"""Patient booking business rules."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.booking import Booking
from src.repositories.booking import BookingRepository
from src.schemas.booking import BookingCreate, BookingResponse, StaffBookingResponse, StaffBookingStatusUpdate

logger = get_logger(__name__)


class BookingService:
    """Create bookings for authenticated users and manage staff review decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bookings = BookingRepository(session)

    async def create(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Create a scheduled booking or a requested-time booking awaiting staff review."""
        async with self.session.begin():
            service = await self.bookings.get_service(request.service_id)
            if service is None or service.status != "active":
                raise NotFoundError("Service not found")
            specialty = await self.bookings.get_specialty(request.specialty_id)
            if specialty is None or specialty.status != "active":
                raise NotFoundError("Specialty not found")

            schedule = None
            if request.schedule_id:
                schedule = await self.bookings.get_schedule_for_update(request.schedule_id)
                if schedule is None:
                    raise NotFoundError("Schedule not found")
                self._validate_schedule(schedule)
                doctor_id = schedule.doctor_id
                facility_id = schedule.facility_id
                starts_at = schedule.starts_at
                ends_at = schedule.ends_at
            else:
                doctor_id = request.doctor_id
                facility_id = request.facility_id
                starts_at = request.starts_at
                ends_at = request.ends_at
                doctor = await self.bookings.get_doctor(doctor_id)
                facility = await self.bookings.get_facility(facility_id)
                if doctor is None or doctor.status != "active" or doctor.review_status != "approved":
                    raise ConflictError("DOCTOR_UNAVAILABLE", "Doctor is not available for booking")
                if not doctor.booking_enabled:
                    raise ConflictError("DOCTOR_BOOKING_DISABLED", "Doctor booking is disabled")
                if facility is None or facility.status != "active":
                    raise ConflictError("FACILITY_UNAVAILABLE", "Facility is not available for booking")
                if not starts_at or not ends_at or starts_at <= datetime.now(UTC):
                    raise ConflictError("SLOT_IN_PAST", "Requested booking time must be in the future")
                if not await self.bookings.has_doctor_facility(doctor_id, facility_id):
                    raise ConflictError("FACILITY_NOT_AVAILABLE", "Doctor is not available at this facility")

            if not await self.bookings.has_doctor_service(doctor_id, service.id):
                raise ConflictError("SERVICE_NOT_AVAILABLE", "Service is not available for this doctor")
            if not await self.bookings.has_doctor_specialty(doctor_id, specialty.id):
                raise ConflictError("SPECIALTY_NOT_AVAILABLE", "Specialty is not available for this doctor")

            if schedule:
                # The schedule row lock is held until this transaction commits. Every
                # concurrent request for this schedule therefore waits before counting,
                # making the count-and-insert decision serial for the same schedule.
                active_count = await self.bookings.count_active_for_schedule(schedule.id)
                if service.booking_mode == "doctor_visit" and active_count >= 1:
                    raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
                if service.booking_mode == "group" and active_count >= schedule.capacity:
                    raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")

            booking = Booking(
                user_id=user_id,
                schedule_id=schedule.id if schedule else None,
                doctor_id=doctor_id,
                facility_id=facility_id,
                starts_at=starts_at,
                ends_at=ends_at,
                service_id=service.id,
                specialty_id=specialty.id,
                encounter_type=request.encounter_type,
                reason=request.reason.strip(),
                patient_note=request.patient_note.strip() if request.patient_note else None,
                status="pending_approval",
            )
            await self.bookings.add(booking)
        logger.info("BookingService.create booking pending approval", extra={"booking_id": str(booking.id)})
        return await self.get(user_id, booking.id)

    async def list(self, user_id: UUID, status: str | None, offset: int, limit: int) -> list[Booking]:
        """List bookings owned by the authenticated user."""
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
            if booking.status == "rejected":
                raise ConflictError("BOOKING_NOT_CANCELLABLE", "Rejected booking cannot be cancelled")
            booking.status = "cancelled"
            booking.cancellation_reason = reason.strip() if reason else None
            await self.session.flush()
        logger.info("BookingService.cancel booking cancelled", extra={"booking_id": str(booking_id)})
        return await self.get(user_id, booking_id)

    async def list_for_staff(
        self,
        status: str | None,
        selected_date: date | None,
        offset: int,
        limit: int,
    ) -> list[Booking]:
        """List booking records for a staff review queue."""
        return await self.bookings.list_for_staff(status, selected_date, offset, limit)

    async def get_for_staff(self, booking_id: UUID) -> Booking:
        """Fetch one booking for staff review."""
        booking = await self.bookings.get_for_staff(booking_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    async def review(self, booking_id: UUID, actor_id: UUID, request: StaffBookingStatusUpdate) -> Booking:
        """Approve or reject a booking exactly once as staff."""
        async with self.session.begin():
            booking = await self.bookings.get_for_staff(booking_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status != "pending_approval":
                raise ConflictError("BOOKING_ALREADY_REVIEWED", "Only pending bookings can be reviewed")
            if request.status == "rejected" and not request.note:
                raise ConflictError("REJECTION_NOTE_REQUIRED", "A rejection reason is required")
            booking.status = request.status
            booking.staff_note = request.note
            booking.reviewed_by = actor_id
            booking.reviewed_at = datetime.now(UTC)
            await self.session.flush()
        logger.info(
            "BookingService.review booking reviewed",
            extra={"booking_id": str(booking_id), "status": request.status, "actor_id": str(actor_id)},
        )
        return await self.get_for_staff(booking_id)

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
        doctor_id=value.doctor_id,
        facility_id=value.facility_id,
        starts_at=value.starts_at,
        ends_at=value.ends_at,
        booking_mode=value.service.booking_mode,
        encounter_type=value.encounter_type,
        reason=value.reason,
        patient_note=value.patient_note,
        status=value.status,
        cancellation_reason=value.cancellation_reason,
        staff_note=value.staff_note,
        reviewed_by=value.reviewed_by,
        reviewed_at=value.reviewed_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def staff_booking_response(value: Booking) -> StaffBookingResponse:
    """Map a booking to the staff queue contract with resolved context."""
    base = booking_response(value)
    patient = value.user
    doctor = value.doctor
    facility = value.facility
    return StaffBookingResponse(
        **base.model_dump(),
        patient_name=patient.full_name if patient else None,
        patient_email=patient.email if patient else None,
        patient_phone=patient.phone if patient else None,
        patient_date_of_birth=patient.date_of_birth if patient else None,
        patient_gender=patient.gender if patient else None,
        patient_citizen_id=patient.citizen_id if patient else None,
        patient_health_insurance_code=patient.health_insurance_code if patient else None,
        doctor_name=doctor.full_name if doctor else None,
        doctor_title=doctor.title if doctor else None,
        doctor_avatar=doctor.avatar_url if doctor else None,
        specialty_name=value.specialty.name if value.specialty else None,
        service_name=value.service.name if value.service else None,
        facility_name=facility.name if facility else None,
        facility_address=facility.address if facility else None,
        room=None,
    )
