"""Patient booking business rules."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
from src.models.booking import Booking
from src.models.catalog import CatalogAuditEvent, DoctorSchedule
from src.models.user import User
from src.repositories.booking import BookingRepository
from src.repositories.user import UserRepository
from src.schemas.booking import (
    BookingCreate,
    BookingRescheduleCreate,
    StaffBookingStatusUpdate,
)
from src.schemas.schedule import GuestPatientCreate
from src.services.notification import NotificationService

logger = get_logger(__name__)
BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DEFAULT_WORKING_START = time(8, 0)
DEFAULT_WORKING_END = time(18, 0)


class BookingService:
    """Create bookings for authenticated users and manage staff review decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bookings = BookingRepository(session)
        self.users = UserRepository(session)
        self.notifications = NotificationService(session)

    @staticmethod
    def _approval_expiry(now: datetime) -> datetime:
        """Return the fixed approval deadline for a newly submitted booking."""
        return now + timedelta(hours=24)

    async def create(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Create a scheduled booking or a requested-time booking awaiting staff review."""
        log_event(
            logger,
            logging.INFO,
            "booking.create.start",
            description="Starting patient booking validation and persistence",
            user_id=str(user_id),
            service_id=str(request.service_id),
            specialty_id=str(request.specialty_id),
            schedule_id=str(request.schedule_id) if request.schedule_id else None,
        )
        async with self.session.begin():
            booking = await self._create_in_transaction(user_id, request)
        log_event(
            logger,
            logging.INFO,
            "booking.create.done",
            description="A patient booking was created and submitted for approval",
            booking_id=str(booking.id),
            user_id=str(user_id),
            status=booking.status,
        )
        return await self.get(user_id, booking.id)

    async def create_idempotent(self, user_id: UUID, request: BookingCreate, key: str) -> tuple[Booking, bool]:
        """Create a booking once and replay the same result for duplicate submits."""
        log_event(
            logger,
            logging.INFO,
            "booking.create.start",
            description="Starting idempotent booking lookup or creation",
            user_id=str(user_id),
            service_id=str(request.service_id),
            specialty_id=str(request.specialty_id),
            mode="idempotent",
        )
        normalized_key = key.strip()
        if not normalized_key:
            raise ConflictError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key must not be blank")
        request_hash = self._request_hash(request)
        replay = False
        try:
            async with self.session.begin():
                existing = await self.bookings.get_booking_by_idempotency(user_id, normalized_key)
                if existing is not None:
                    if existing.idempotency_hash != request_hash:
                        raise ConflictError(
                            "IDEMPOTENCY_KEY_REUSED", "Idempotency-Key was used with a different request"
                        )
                    booking = existing
                    replay = True
                else:
                    booking = await self._create_in_transaction(user_id, request)
                    booking.idempotency_key = normalized_key
                    booking.idempotency_hash = request_hash
                    await self.session.flush()
        except IntegrityError as exc:
            # A concurrent request may win the partial unique index between the
            # lookup and insert. Re-read the committed winner and replay it.
            await self.session.rollback()
            existing = await self.bookings.get_booking_by_idempotency(user_id, normalized_key)
            if existing is None or existing.idempotency_hash != request_hash:
                log_event(
                    logger,
                    logging.ERROR,
                    "booking.create.error",
                    description="Booking creation failed after an idempotency conflict",
                    user_id=str(user_id),
                    error_type=type(exc).__name__,
                    exc_info=True,
                )
                raise
            booking = existing
            replay = True
        if replay:
            log_event(
                logger,
                logging.INFO,
                "booking.create.replayed",
                description="The existing booking was returned for an idempotent request replay",
                booking_id=str(booking.id),
                user_id=str(user_id),
            )
        else:
            log_event(
                logger,
                logging.INFO,
                "booking.create.done",
                description="A patient booking was created through the idempotent flow",
                booking_id=str(booking.id),
                user_id=str(user_id),
                status=booking.status,
            )
        return await self.get(user_id, booking.id), replay

    async def create_staff_confirmed_in_transaction(
        self,
        schedule: DoctorSchedule,
        *,
        actor_id: UUID,
        service_id: UUID,
        specialty_id: UUID,
        patient_id: UUID | None,
        guest_patient: GuestPatientCreate | None,
        encounter_type: str,
        reason: str,
        patient_note: str | None,
    ) -> Booking:
        """Create a confirmed doctor-visit booking inside a caller transaction."""
        log_event(
            logger,
            logging.INFO,
            "booking.staff_create.start",
            description="Starting staff-confirmed booking creation inside an existing transaction",
            actor_id=str(actor_id),
            schedule_id=str(schedule.id),
            service_id=str(service_id),
            specialty_id=str(specialty_id),
            patient_id=str(patient_id) if patient_id else None,
        )
        service = await self.bookings.get_service(service_id)
        specialty = await self.bookings.get_specialty(specialty_id)
        if service is None or service.status != "active":
            raise NotFoundError("Service not found")
        if service.booking_mode != "doctor_visit":
            raise ConflictError("GROUP_SERVICE_BOOKING_NOT_ALLOWED", "Group schedules do not create staff bookings")
        if specialty is None or specialty.status != "active":
            raise NotFoundError("Specialty not found")
        await self._validate_catalog_relationships(schedule, service, specialty)

        active_count = await self.bookings.count_active_for_schedule(schedule.id)
        if active_count >= 1:
            raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")

        patient = await self._resolve_staff_patient(patient_id, guest_patient)
        booking = Booking(
            user_id=patient.id,
            schedule_id=schedule.id,
            doctor_id=schedule.doctor_id,
            facility_id=schedule.facility_id,
            starts_at=schedule.starts_at,
            ends_at=schedule.ends_at,
            service_id=service.id,
            specialty_id=specialty.id,
            encounter_type=encounter_type,
            reason=reason.strip(),
            patient_note=patient_note.strip() if patient_note else None,
            status="confirmed",
            expired_at=self._approval_expiry(datetime.now(UTC)),
            reviewed_by=actor_id,
            reviewed_at=datetime.now(UTC),
        )
        await self.bookings.add(booking)
        await self.notifications.create_for_booking_review(booking, "confirmed")
        log_event(
            logger,
            logging.INFO,
            "booking.staff_create.done",
            description="Staff created a confirmed booking inside the schedule transaction",
            booking_id=str(booking.id),
            actor_id=str(actor_id),
            status=booking.status,
        )
        return booking

    async def _resolve_staff_patient(self, patient_id: UUID | None, guest_patient: GuestPatientCreate | None) -> User:
        """Resolve an existing patient or create a temporary guest patient."""
        if patient_id:
            patient = await self.users.get_by_id(patient_id)
            if patient is None or patient.role != "patient":
                raise NotFoundError("Patient not found")
            return patient
        if guest_patient is None:
            raise ConflictError("PATIENT_REQUIRED", "A patient or guest contact is required")

        patient = await self.users.get_by_identity(guest_patient.email, guest_patient.phone)
        if patient is not None:
            if patient.role != "patient":
                raise ConflictError("PATIENT_IDENTITY_CONFLICT", "Contact belongs to a non-patient account")
            return patient

        return await self.users.create(
            User(
                full_name=guest_patient.full_name,
                email=guest_patient.email,
                phone=guest_patient.phone,
                password_hash=None,
                role="patient",
                status="guest",
            )
        )

    async def _create_in_transaction(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Validate and stage a booking while the caller owns the transaction."""
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
            doctor_finder = getattr(self.bookings, "get_doctor_for_update", self.bookings.get_doctor)
            doctor = await doctor_finder(doctor_id)
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
            local_start = starts_at.astimezone(BUSINESS_TZ)
            local_end = ends_at.astimezone(BUSINESS_TZ)
            if (
                local_start.date() != local_end.date()
                or local_start.time() < DEFAULT_WORKING_START
                or local_end.time() > DEFAULT_WORKING_END
            ):
                raise ConflictError(
                    "OUTSIDE_WORKING_HOURS", "Requested booking time is outside the default working hours"
                )
            published_finder = getattr(self.bookings, "find_schedule_conflict", None)
            published_schedule = (
                await published_finder(
                    doctor_id=doctor_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
                if published_finder
                else None
            )
            if published_schedule is not None:
                raise ConflictError("SCHEDULE_REQUIRED", "Select the published consultation schedule for this time")
            blocking_finder = getattr(self.bookings, "find_blocking_schedule", None)
            blocking = (
                await blocking_finder(
                    doctor_id=doctor_id,
                    facility_id=facility_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )
                if blocking_finder
                else None
            )
            if blocking is not None:
                raise ConflictError("DOCTOR_BUSY", "Doctor is busy during the requested time")
            if service.booking_mode == "doctor_visit":
                conflict_finder = getattr(self.bookings, "find_active_booking_conflict", None)
                conflict = (
                    await conflict_finder(
                        doctor_id=doctor_id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                    )
                    if conflict_finder
                    else None
                )
                if conflict is not None:
                    raise ConflictError("SCHEDULE_CONFLICT", "This doctor is already booked during the requested time")

        await self._validate_catalog_relationships(
            schedule, service, specialty, doctor_id=doctor_id, facility_id=facility_id
        )

        if schedule:
            # The schedule row lock is held until commit, serializing capacity decisions.
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
            expired_at=self._approval_expiry(datetime.now(UTC)),
        )
        await self.bookings.add(booking)
        await self.notifications.create_for_booking_request(booking)
        return booking

    async def _validate_catalog_relationships(
        self, schedule, service, specialty, *, doctor_id: UUID | None = None, facility_id: UUID | None = None
    ) -> None:
        """Ensure selected catalog resources match the doctor and schedule."""
        resolved_doctor_id = doctor_id or schedule.doctor_id
        resolved_facility_id = facility_id or schedule.facility_id
        if not await self.bookings.has_doctor_service(resolved_doctor_id, service.id):
            raise ConflictError("SERVICE_NOT_AVAILABLE", "Service is not available for this doctor")
        if not await self.bookings.has_doctor_specialty(resolved_doctor_id, specialty.id):
            raise ConflictError("SPECIALTY_NOT_AVAILABLE", "Specialty is not available for this doctor")
        if schedule is not None and resolved_facility_id != schedule.facility_id:
            raise ConflictError("FACILITY_NOT_AVAILABLE", "Doctor is not available at this facility")

    @staticmethod
    def _request_hash(request: BookingCreate) -> str:
        """Hash the normalized request body for idempotency-key reuse checks."""
        payload = request.model_dump(mode="json")
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    async def list(self, user_id: UUID, status: str | None, offset: int, limit: int) -> list[Booking]:
        """List bookings owned by the authenticated user."""
        log_event(
            logger,
            logging.INFO,
            "booking.list.start",
            description="Starting patient booking list query",
            user_id=str(user_id),
            status=status,
            offset=offset,
            limit=limit,
        )
        values = await self.bookings.list_for_user(user_id, status, offset, limit)
        log_event(
            logger,
            logging.INFO,
            "booking.list.done",
            description="Bookings were listed for the authenticated patient",
            user_id=str(user_id),
            count=len(values),
            status=status,
        )
        return values

    async def get(self, user_id: UUID, booking_id: UUID) -> Booking:
        """Get one booking owned by a patient."""
        log_event(
            logger,
            logging.INFO,
            "booking.get.start",
            description="Starting patient-owned booking lookup",
            booking_id=str(booking_id),
            user_id=str(user_id),
        )
        booking = await self.bookings.get_for_user(booking_id, user_id)
        if booking is None:
            log_event(
                logger,
                logging.WARNING,
                "booking.get.not_found",
                description="Patient booking lookup returned no owned booking",
                booking_id=str(booking_id),
                user_id=str(user_id),
            )
            raise NotFoundError("Booking not found")
        log_event(
            logger,
            logging.INFO,
            "booking.get.done",
            description="Patient booking was loaded",
            booking_id=str(booking_id),
            user_id=str(user_id),
            status=booking.status,
        )
        return booking

    async def cancel(self, user_id: UUID, booking_id: UUID, reason: str | None) -> Booking:
        """Cancel an owned booking without deleting its history."""
        log_event(
            logger,
            logging.INFO,
            "booking.cancel.start",
            description="Starting patient booking cancellation and reminder cleanup",
            booking_id=str(booking_id),
            user_id=str(user_id),
        )
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
            await self.notifications.discard_reminders_for_booking(booking.id)
            await self.session.flush()
        log_event(
            logger,
            logging.INFO,
            "booking.cancel.done",
            description="Patient booking was cancelled and its reminders were discarded",
            booking_id=str(booking_id),
            user_id=str(user_id),
            status="cancelled",
        )
        return await self.get(user_id, booking_id)

    async def reschedule(self, user_id: UUID, booking_id: UUID, request: BookingRescheduleCreate) -> Booking:
        """Move an owned scheduled booking to a newly held slot for re-approval."""
        log_event(
            logger,
            logging.INFO,
            "booking.reschedule.start",
            description="Starting booking schedule validation and rescheduling",
            booking_id=str(booking_id),
            user_id=str(user_id),
            target_schedule_id=str(request.schedule_id),
        )
        async with self.session.begin():
            booking = await self.bookings.get_for_user(booking_id, user_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status in ("cancelled", "rejected"):
                raise ConflictError("BOOKING_NOT_RESCHEDULABLE", "This booking cannot be rescheduled")
            if booking.schedule_id is None:
                raise ConflictError("BOOKING_NOT_RESCHEDULABLE", "Requested-time bookings cannot be rescheduled yet")
            if request.schedule_id == booking.schedule_id:
                raise ConflictError("SAME_SCHEDULE", "Choose a different schedule")

            schedules = await self.bookings.get_schedules_for_update({booking.schedule_id, request.schedule_id})
            old_schedule = schedules.get(booking.schedule_id)
            new_schedule = schedules.get(request.schedule_id)
            if old_schedule is None or new_schedule is None:
                raise NotFoundError("Schedule not found")
            self._validate_schedule(new_schedule)

            active_count = await self.bookings.count_reservations_for_schedule(
                new_schedule.id,
                exclude_booking_id=booking.id,
            )
            if booking.service.booking_mode == "doctor_visit" and active_count >= 1:
                raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
            if booking.service.booking_mode == "group" and active_count >= new_schedule.capacity:
                raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
            await self._validate_catalog_relationships(new_schedule, booking.service, booking.specialty)

            old_values = {
                "schedule_id": str(booking.schedule_id),
                "starts_at": booking.starts_at.isoformat(),
                "ends_at": booking.ends_at.isoformat(),
                "status": booking.status,
            }
            await self.notifications.discard_reminders_for_booking(booking.id)
            booking.schedule_id = new_schedule.id
            booking.doctor_id = new_schedule.doctor_id
            booking.facility_id = new_schedule.facility_id
            booking.starts_at = new_schedule.starts_at
            booking.ends_at = new_schedule.ends_at
            booking.status = "pending_approval"
            booking.expired_at = self._approval_expiry(datetime.now(UTC))
            booking.staff_note = None
            booking.reviewed_by = None
            booking.reviewed_at = None
            await self.notifications.create_for_booking_request(booking, cycle="rescheduled")
            self.session.add(
                CatalogAuditEvent(
                    actor_id=user_id,
                    entity_type="booking",
                    entity_id=booking.id,
                    action="rescheduled",
                    payload={
                        "old": old_values,
                        "new": {
                            "schedule_id": str(new_schedule.id),
                            "starts_at": new_schedule.starts_at.isoformat(),
                            "ends_at": new_schedule.ends_at.isoformat(),
                            "status": booking.status,
                        },
                    },
                )
            )
            await self.session.flush()
        log_event(
            logger,
            logging.INFO,
            "booking.reschedule.done",
            description="Booking was moved to a new schedule and returned to approval",
            booking_id=str(booking_id),
            user_id=str(user_id),
        )
        return await self.get(user_id, booking_id)

    async def list_for_staff(
        self,
        status: str | None,
        selected_date: date | None,
        offset: int,
        limit: int,
    ) -> list[Booking]:
        """List booking records for a staff review queue."""
        log_event(
            logger,
            logging.INFO,
            "booking.staff_list.start",
            description="Starting staff booking review queue query",
            status=status,
            selected_date=selected_date.isoformat() if selected_date else None,
            offset=offset,
            limit=limit,
        )
        values = await self.bookings.list_for_staff(status, selected_date, offset, limit)
        log_event(
            logger,
            logging.INFO,
            "booking.staff_list.done",
            description="Staff booking review queue was listed",
            count=len(values),
            status=status,
        )
        return values

    async def get_for_staff(self, booking_id: UUID) -> Booking:
        """Fetch one booking for staff review."""
        log_event(
            logger,
            logging.INFO,
            "booking.staff_get.start",
            description="Starting staff booking lookup for review",
            booking_id=str(booking_id),
        )
        booking = await self.bookings.get_for_staff(booking_id)
        if booking is None:
            log_event(
                logger,
                logging.WARNING,
                "booking.staff_get.not_found",
                description="Staff booking lookup returned no matching booking",
                booking_id=str(booking_id),
            )
            raise NotFoundError("Booking not found")
        log_event(
            logger,
            logging.INFO,
            "booking.staff_get.done",
            description="Staff booking record was loaded for review",
            booking_id=str(booking_id),
            status=booking.status,
        )
        return booking

    async def review(self, booking_id: UUID, actor_id: UUID, request: StaffBookingStatusUpdate) -> Booking:
        """Approve or reject a booking exactly once as staff."""
        log_event(
            logger,
            logging.INFO,
            "booking.review.start",
            description="Starting staff booking approval or rejection workflow",
            booking_id=str(booking_id),
            actor_id=str(actor_id),
            requested_status=request.status,
        )
        expired = False
        async with self.session.begin():
            booking = await self.bookings.get_for_staff(booking_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status != "pending_approval":
                raise ConflictError("BOOKING_ALREADY_REVIEWED", "Only pending bookings can be reviewed")
            if booking.expired_at <= datetime.now(UTC):
                booking.status = "expired"
                await self.notifications.create_for_booking_expired(booking)
                await self.session.flush()
                expired = True
            if not expired and request.status == "rejected" and not request.note:
                raise ConflictError("REJECTION_NOTE_REQUIRED", "A rejection reason is required")
            created_schedule = False
            if not expired and request.status == "confirmed" and booking.schedule_id is None:
                blocking_finder = getattr(self.bookings, "find_blocking_schedule", None)
                blocking = (
                    await blocking_finder(
                        doctor_id=booking.doctor_id,
                        facility_id=booking.facility_id,
                        starts_at=booking.starts_at,
                        ends_at=booking.ends_at,
                    )
                    if blocking_finder
                    else None
                )
                if blocking is not None:
                    raise ConflictError("DOCTOR_BUSY", "Doctor is busy during the requested time")
                conflict = await self.bookings.find_schedule_conflict(
                    doctor_id=booking.doctor_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                )
                if conflict is not None:
                    raise ConflictError("SCHEDULE_TIME_CONFLICT", "Doctor already has a schedule overlapping this time")
                schedule = DoctorSchedule(
                    doctor_id=booking.doctor_id,
                    facility_id=booking.facility_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    capacity=1,
                    status="available",
                    type="consultation",
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                await self.bookings.add_schedule(schedule)
                booking.schedule_id = schedule.id
                created_schedule = True
                self.session.add(
                    CatalogAuditEvent(
                        actor_id=actor_id,
                        entity_type="doctor_schedule",
                        entity_id=schedule.id,
                        action="created_from_booking",
                        payload={"booking_id": str(booking.id)},
                    )
                )
            if not expired and request.status == "confirmed" and booking.schedule_id is not None:
                schedule = await self.bookings.get_schedule_for_update(booking.schedule_id)
                if schedule is None:
                    raise ConflictError("SCHEDULE_UNAVAILABLE", "Schedule is not available")
                if not created_schedule:
                    self._validate_schedule(schedule)
                active_count = await self.bookings.count_reservations_for_schedule(
                    schedule.id,
                    exclude_booking_id=booking.id,
                )
                if booking.service.booking_mode == "doctor_visit" and active_count >= 1:
                    raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
                if booking.service.booking_mode == "group" and active_count >= schedule.capacity:
                    raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
            if not expired:
                booking.status = request.status
                booking.staff_note = request.note
                booking.reviewed_by = actor_id
                booking.reviewed_at = datetime.now(UTC)
                await self.notifications.create_for_booking_review(booking, request.status)
                await self.session.flush()
        if expired:
            log_event(
                logger,
                logging.WARNING,
                "booking.review.expired",
                description="Booking review was blocked because the approval deadline had passed",
                booking_id=str(booking_id),
            )
            raise ConflictError("BOOKING_EXPIRED", "Booking approval deadline has passed")
        log_event(
            logger,
            logging.INFO,
            "booking.review.done",
            description="Staff reviewed a pending booking",
            booking_id=str(booking_id),
            status=request.status,
            actor_id=str(actor_id),
        )
        return await self.get_for_staff(booking_id)

    async def expire_pending_bookings(self, limit: int = 100) -> int:
        """Expire pending approvals and enqueue patient notifications atomically."""
        log_event(
            logger,
            logging.INFO,
            "booking.expire.start",
            description="Starting maintenance scan for expired pending bookings",
            limit=limit,
        )
        async with self.session.begin():
            bookings = await self.bookings.claim_expired_pending_bookings(datetime.now(UTC), limit)
            for booking in bookings:
                booking.status = "expired"
                await self.notifications.create_for_booking_expired(booking)
            if bookings:
                await self.session.flush()
        log_event(
            logger,
            logging.INFO,
            "booking.expire.done",
            description="Pending bookings past their approval deadline were expired",
            expired_count=len(bookings),
        )
        return len(bookings)

    @staticmethod
    def _validate_schedule(schedule) -> None:
        """Validate public schedule state before counting capacity."""
        if (getattr(schedule, "type", "consultation") or "consultation") != "consultation":
            raise ConflictError("SCHEDULE_UNAVAILABLE", "This schedule is not a consultation slot")
        if schedule.status != "available":
            raise ConflictError("SCHEDULE_UNAVAILABLE", "Schedule is not available")
        if schedule.capacity <= 0:
            raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
        if schedule.doctor.status != "active" or schedule.doctor.review_status != "approved":
            raise ConflictError("DOCTOR_UNAVAILABLE", "Doctor is not available for booking")
        if not schedule.doctor.booking_enabled:
            raise ConflictError("DOCTOR_BOOKING_DISABLED", "Doctor booking is disabled")
        if getattr(schedule, "facility", None) is None or schedule.facility.status != "active":
            raise ConflictError("FACILITY_UNAVAILABLE", "Facility is not available for booking")
