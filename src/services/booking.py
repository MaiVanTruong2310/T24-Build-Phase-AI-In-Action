"""Patient booking business rules."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.booking_reservations import (
    cache_schedule,
    get_draft,
    pending_count,
    requested_time_conflict,
    reserve_requested_time,
    reserve_schedule,
    save_draft,
)
from src.core.booking_reservations import (
    release as release_booking_reservation,
)
from src.core.cache import invalidate_redis_api_cache
from src.core.errors import raise_integrity_conflict
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
from src.models.booking import Booking
from src.models.booking_hold import BookingHold
from src.models.catalog import CatalogAuditEvent, DoctorSchedule
from src.models.coordination import ConsultationRequest, ConsultationRequestEvent, ConsultationSession
from src.models.user import User
from src.repositories.booking import BookingRepository
from src.repositories.user import UserRepository
from src.schemas.booking import (
    BookingCreate,
    BookingHoldCreate,
    BookingHoldResponse,
    BookingRescheduleCreate,
    BookingResponse,
    StaffBookingResponse,
    StaffBookingStatusUpdate,
)
from src.services.chat_takeover import publish_workbench_case_update
from src.services.notification import NotificationService
from src.services.workbench import record_booking_review

logger = get_logger(__name__)


class BookingService:
    """Create bookings for authenticated users and manage staff review decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bookings = BookingRepository(session)
        self.users = UserRepository(session)
        self.notifications = NotificationService(session)

    async def requested_time_available(
        self, doctor_id: UUID, facility_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> bool:
        """Check a patient-selected free period without exposing conflicting records."""
        self._validate_requested_period(starts_at, ends_at)
        doctor = await self.bookings.get_doctor(doctor_id)
        facility = await self.bookings.get_facility(facility_id)
        if (
            doctor is None
            or doctor.status != "active"
            or doctor.review_status != "approved"
            or not doctor.booking_enabled
        ):
            raise NotFoundError("Doctor not found")
        if facility is None or facility.status != "active":
            raise NotFoundError("Facility not found")
        local_date = starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        if not await self.bookings.has_doctor_facility(doctor_id, facility_id, local_date):
            raise ConflictError("FACILITY_NOT_AVAILABLE", "Doctor is not available at this facility")
        if await self.bookings.has_schedule_overlap(doctor_id, starts_at, ends_at):
            return False
        cached_conflict = await requested_time_conflict(doctor_id, starts_at, ends_at)
        if cached_conflict is True:
            return False
        return cached_conflict is False or not await self.bookings.has_pending_requested_time_overlap(
            doctor_id, starts_at, ends_at
        )

    @staticmethod
    def _validate_requested_period(starts_at: datetime, ends_at: datetime) -> None:
        """Keep patient-requested periods within the same clinic limits as staff free periods."""
        if starts_at.tzinfo is None or ends_at.tzinfo is None:
            raise ConflictError("INVALID_REQUESTED_TIME", "Requested time must include a timezone")
        if starts_at <= datetime.now(UTC):
            raise ConflictError("SLOT_IN_PAST", "Requested time must be in the future")
        duration = (ends_at - starts_at).total_seconds() / 60
        local_start = starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        local_end = ends_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        morning = local_start.hour >= 8 and local_end.hour <= 12
        afternoon = local_start.hour >= 13 and (local_end.hour < 18 or (local_end.hour == 18 and local_end.minute == 0))
        if duration < 5 or duration > 480 or local_start.date() != local_end.date() or not (morning or afternoon):
            raise ConflictError(
                "INVALID_REQUESTED_TIME", "Requested time must be 5 minutes to 8 hours within clinic hours"
            )

    async def create(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Create a scheduled booking or a requested-time booking awaiting staff review."""
        log_event(logger, logging.INFO, "booking.create.start", service_id=str(request.service_id))
        try:
            async with self.session.begin():
                booking = await self._create_in_transaction(user_id, request)
        except IntegrityError as exc:
            raise_integrity_conflict(
                exc,
                logger=logger,
                event="booking.create.persistence_conflict",
                code="BOOKING_CREATE_CONFLICT",
                message="Booking could not be created",
                log_description="Booking creation conflicted with a selected slot or related resource",
                user_id=str(user_id),
                service_id=str(request.service_id),
                specialty_id=str(request.specialty_id),
            )
        log_event(logger, logging.INFO, "booking.create.done", booking_id=str(booking.id), status=booking.status)
        return await self.get(user_id, booking.id)

    async def create_idempotent(self, user_id: UUID, request: BookingCreate, key: str) -> tuple[Booking, bool]:
        """Create a booking once and replay the same result for duplicate submits."""
        log_event(logger, logging.INFO, "booking.create.start", service_id=str(request.service_id))
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
                log_event(logger, logging.ERROR, "booking.create.error")
                raise_integrity_conflict(
                    exc,
                    logger=logger,
                    event="booking.create.persistence_conflict",
                    code="BOOKING_CREATE_CONFLICT",
                    message="Booking could not be created",
                    log_description="Idempotent booking creation conflicted with a selected slot or related resource",
                    user_id=str(user_id),
                    idempotency_key=normalized_key,
                )
            booking = existing
            replay = True
        if replay:
            log_event(logger, logging.INFO, "booking.create.replayed", booking_id=str(booking.id))
        else:
            await invalidate_redis_api_cache("staff-bookings")
            log_event(logger, logging.INFO, "booking.create.done", booking_id=str(booking.id), status=booking.status)
        return await self.get(user_id, booking.id), replay

    async def create_staff_confirmed_in_transaction(
        self,
        schedule: DoctorSchedule,
        *,
        actor_id: UUID,
        service_id: UUID | None,
        specialty_id: UUID,
        patient_id: UUID | None,
        guest_patient: object | None,
        requested_by_user_id: UUID | None = None,
        patient_profile_id: UUID | None = None,
        encounter_type: str,
        reason: str,
        patient_note: str | None,
    ) -> Booking:
        """Create a confirmed doctor visit inside a caller-owned transaction."""
        service = await self.bookings.get_service(service_id) if service_id else None
        specialty = await self.bookings.get_specialty(specialty_id)
        if service_id and (service is None or service.status != "active"):
            raise NotFoundError("Service not found")
        if service and service.booking_mode != "doctor_visit":
            raise ConflictError("GROUP_SERVICE_BOOKING_NOT_ALLOWED", "Group schedules do not create staff bookings")
        if specialty is None or specialty.status != "active":
            raise NotFoundError("Specialty not found")
        schedule = await self.bookings.get_schedule_for_update(schedule.id)
        if schedule is None or schedule.status != "available":
            raise ConflictError("SCHEDULE_UNAVAILABLE", "Schedule is not available")
        await self._validate_catalog_relationships(schedule, service, specialty)
        reserved_count = await self.bookings.count_reservations_for_schedule(schedule.id)
        if schedule.capacity <= reserved_count:
            raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
        patient = await self._resolve_staff_patient(patient_id, guest_patient)
        appointment_schedule = DoctorSchedule(
            doctor_id=schedule.doctor_id,
            facility_id=schedule.facility_id,
            service_id=service.id if service else None,
            starts_at=schedule.starts_at,
            ends_at=schedule.ends_at,
            capacity=1,
            status="available",
            created_by=actor_id,
            updated_by=actor_id,
        )
        schedule.capacity -= 1
        schedule.version += 1
        schedule.updated_by = actor_id
        self.session.add(appointment_schedule)
        booking = Booking(
            user_id=patient.id,
            patient_id=patient.id,
            approved_by_receptionist_id=actor_id,
            requested_by_user_id=requested_by_user_id,
            patient_profile_id=patient_profile_id,
            schedule_id=schedule.id,
            doctor_id=schedule.doctor_id,
            facility_id=schedule.facility_id,
            starts_at=schedule.starts_at,
            ends_at=schedule.ends_at,
            service_id=service.id if service else None,
            specialty_id=specialty.id,
            encounter_type=encounter_type,
            reason=reason.strip(),
            patient_note=patient_note.strip() if patient_note else None,
            status="confirmed",
            appointment_schedule=appointment_schedule,
            reviewed_by=actor_id,
            reviewed_at=datetime.now(UTC),
        )
        await self.bookings.add(booking)
        await self.notifications.create_for_booking_review(booking, "confirmed")
        return booking

    async def _resolve_staff_patient(self, patient_id: UUID | None, guest_patient: object | None) -> User:
        """Resolve an existing patient or create a guest patient identity."""
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
            # Do not attach an intake to a verified account by contact fields alone.
            if patient.status != "guest":
                raise ConflictError(
                    "PATIENT_SELECTION_REQUIRED", "Resolve the intake to its patient account before booking"
                )
            return patient
        return await self.users.create(
            User(
                full_name=guest_patient.full_name,
                email=guest_patient.email,
                phone=guest_patient.phone,
                date_of_birth=getattr(guest_patient, "date_of_birth", None),
                gender=getattr(guest_patient, "gender", None),
                role="patient",
                status="guest",
            )
        )

    async def hold(self, user_id: UUID, request: BookingHoldCreate) -> BookingHold:
        """Reserve schedule capacity for five to ten minutes."""
        async with self.session.begin():
            service = await self.bookings.get_service(request.service_id)
            specialty = await self.bookings.get_specialty(request.specialty_id)
            if service is None or service.status != "active":
                raise NotFoundError("Service not found")
            if specialty is None or specialty.status != "active":
                raise NotFoundError("Specialty not found")

            schedule = await self.bookings.get_schedule_for_update(request.schedule_id)
            if schedule is None:
                raise NotFoundError("Schedule not found")
            self._validate_schedule(schedule)
            if schedule.starts_at <= datetime.now(UTC):
                raise ConflictError("SLOT_IN_PAST", "Requested schedule is no longer bookable")
            await self._validate_catalog_relationships(schedule, service, specialty)

            existing = await self.bookings.get_active_hold_for_user_schedule(user_id, schedule.id, for_update=True)
            if existing is not None:
                if existing.service_id == service.id and existing.specialty_id == specialty.id:
                    hold = existing
                else:
                    raise ConflictError("HOLD_ALREADY_EXISTS", "Patient already holds this schedule")
            else:
                cached_pending = await pending_count(schedule.id, schedule.version)
                if cached_pending is None:
                    pending_rows = await self.bookings.list_pending_reservations(schedule.id)
                    cached_pending = await pending_count(schedule.id, schedule.version, pending_rows)
                    pending_total = cached_pending if cached_pending is not None else len(pending_rows)
                else:
                    pending_total = cached_pending
                active_count = pending_total + await self.bookings.count_active_holds_for_schedule(schedule.id)
                if service.booking_mode == "doctor_visit" and active_count >= 1:
                    raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
                if service.booking_mode == "group" and active_count >= schedule.capacity:
                    raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
                hold = BookingHold(
                    user_id=user_id,
                    schedule_id=schedule.id,
                    service_id=service.id,
                    specialty_id=specialty.id,
                    status="active",
                    expires_at=datetime.now(UTC) + timedelta(seconds=request.hold_seconds),
                )
                await self.bookings.add_hold(hold)
        log_event(logger, logging.INFO, "booking.hold.created", schedule_id=str(request.schedule_id))
        return hold

    async def release_hold(self, user_id: UUID, hold_id: UUID, *, is_staff: bool = False) -> BookingHold:
        """Release an owned hold; repeated release is safe."""
        async with self.session.begin():
            hold = (
                await self.bookings.get_hold(hold_id, for_update=True)
                if is_staff
                else await self.bookings.get_hold_for_user(hold_id, user_id, for_update=True)
            )
            if hold is None:
                raise NotFoundError("Hold not found")
            if hold.status == "active":
                now = datetime.now(UTC)
                hold.status = "expired" if hold.expires_at <= now else "released"
                hold.released_at = now
                await self.session.flush()
        return hold

    async def release_expired_holds(self) -> int:
        """Release expired holds for a periodic worker or maintenance command."""
        async with self.session.begin():
            count = await self.bookings.release_expired_holds()
        return count

    async def _create_in_transaction(self, user_id: UUID, request: BookingCreate) -> Booking:
        """Validate and stage a booking while the caller owns the transaction."""
        service = await self.bookings.get_service(request.service_id) if request.service_id else None
        if request.service_id and (service is None or service.status != "active"):
            raise NotFoundError("Service not found")
        specialty = await self.bookings.get_specialty(request.specialty_id)
        if specialty is None or specialty.status != "active":
            raise NotFoundError("Specialty not found")

        schedule = None
        hold = None
        if request.schedule_id:
            schedule = await self.bookings.get_schedule_for_update(request.schedule_id)
            if schedule is None:
                raise NotFoundError("Schedule not found")
            self._validate_schedule(schedule)
            doctor_id = schedule.doctor_id
            facility_id = schedule.facility_id
            starts_at = schedule.starts_at
            ends_at = schedule.ends_at
            if request.hold_id:
                hold = await self.bookings.get_hold_for_user(request.hold_id, user_id, for_update=True)
                if hold is None:
                    raise NotFoundError("Hold not found")
                if hold.status != "active" or hold.expires_at <= datetime.now(UTC):
                    raise ConflictError("HOLD_EXPIRED", "The booking hold has expired or was released")
                if hold.schedule_id != schedule.id:
                    raise ConflictError("HOLD_SCHEDULE_MISMATCH", "Hold does not belong to this schedule")
                if service is None or hold.service_id != service.id or hold.specialty_id != specialty.id:
                    raise ConflictError("HOLD_REQUEST_MISMATCH", "Hold does not match the booking request")
        else:
            if request.hold_id:
                raise ConflictError("HOLD_SCHEDULE_REQUIRED", "A hold booking must include schedule_id")
            doctor_id = request.doctor_id
            facility_id = request.facility_id
            starts_at = request.starts_at
            ends_at = request.ends_at
            doctor = await self.bookings.get_doctor(doctor_id, for_update=True)
            facility = await self.bookings.get_facility(facility_id)
            if doctor is None or doctor.status != "active" or doctor.review_status != "approved":
                raise ConflictError("DOCTOR_UNAVAILABLE", "Doctor is not available for booking")
            if not doctor.booking_enabled:
                raise ConflictError("DOCTOR_BOOKING_DISABLED", "Doctor booking is disabled")
            if facility is None or facility.status != "active":
                raise ConflictError("FACILITY_UNAVAILABLE", "Facility is not available for booking")
            if not starts_at or not ends_at or starts_at <= datetime.now(UTC):
                raise ConflictError("SLOT_IN_PAST", "Requested booking time must be in the future")
            facility_date = starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
            if not await self.bookings.has_doctor_facility(doctor_id, facility_id, facility_date):
                raise ConflictError("FACILITY_NOT_AVAILABLE", "Doctor is not available at this facility")
            self._validate_requested_period(starts_at, ends_at)
            if service is not None and service.booking_mode == "group":
                raise ConflictError("SCHEDULE_REQUIRED", "Group bookings must select a published schedule")
            if await self.bookings.has_schedule_overlap(doctor_id, starts_at, ends_at):
                raise ConflictError("SCHEDULE_CONFLICT", "Doctor already has an overlapping schedule")

        await self._validate_catalog_relationships(
            schedule, service, specialty, doctor_id=doctor_id, facility_id=facility_id
        )
        if service is not None and not await self.bookings.has_doctor_service(doctor_id, service.id):
            raise ConflictError("SERVICE_NOT_AVAILABLE", "Service is not assigned to this doctor")

        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(hours=24)
        booking_id = uuid4()
        appointment_schedule_id = uuid4()
        draft = {
            "id": str(appointment_schedule_id),
            "doctor_id": str(doctor_id),
            "facility_id": str(facility_id),
            "service_id": str(service.id) if service else None,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "capacity": 1,
            "status": "draft",
        }
        if schedule:
            capacity = 1 if service is None or service.booking_mode == "doctor_visit" else schedule.capacity
            pending_count_cached = await pending_count(schedule.id, schedule.version)
            if pending_count_cached is None:
                pending = await self.bookings.list_pending_reservations(schedule.id)
                await pending_count(schedule.id, schedule.version, pending)
            else:
                pending = []
            active_holds = await self.bookings.count_active_holds_for_schedule(
                schedule.id, exclude_hold_id=hold.id if hold else None
            )
            reserved = await reserve_schedule(
                schedule_id=schedule.id,
                booking_id=booking_id,
                capacity=capacity,
                schedule_version=schedule.version,
                active_holds=active_holds,
                pending=pending,
                expires_at=expires_at,
                draft=draft,
            )
            if reserved is None:
                reserved_count = await self.bookings.count_reservations_for_schedule(
                    schedule.id, exclude_hold_id=hold.id if hold else None
                )
                if reserved_count >= capacity:
                    if service is None or service.booking_mode == "doctor_visit":
                        raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
                    raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
                await save_draft(booking_id, draft, expires_at)
            elif not reserved:
                if service is None or service.booking_mode == "doctor_visit":
                    raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
                raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
        else:
            reserved = await reserve_requested_time(
                booking_id=booking_id,
                doctor_id=doctor_id,
                starts_at=starts_at,
                ends_at=ends_at,
                draft=draft,
                expires_at=expires_at,
            )
            if reserved is False or (
                reserved is None
                and await self.bookings.has_pending_requested_time_overlap(doctor_id, starts_at, ends_at)
            ):
                raise ConflictError("SCHEDULE_CONFLICT", "A booking is already pending for this doctor and time")
            if reserved is None:
                await save_draft(booking_id, draft, expires_at)
        booking = Booking(
            id=booking_id,
            user_id=user_id,
            hold_id=hold.id if hold else None,
            schedule_id=schedule.id if schedule else None,
            doctor_id=doctor_id,
            facility_id=facility_id,
            starts_at=starts_at,
            ends_at=ends_at,
            service_id=service.id if service else None,
            specialty_id=specialty.id,
            encounter_type=request.encounter_type,
            reason=request.reason.strip(),
            patient_note=request.patient_note.strip() if request.patient_note else None,
            status="pending_approval",
            created_at=created_at,
            expired_at=expires_at,
        )
        try:
            await self.bookings.add(booking)
        except Exception:
            await release_booking_reservation(booking.id, schedule.id if schedule else None, doctor_id=doctor_id)
            raise
        if hold:
            hold.status = "consumed"
            hold.released_at = datetime.now(UTC)
        return booking

    async def _validate_catalog_relationships(
        self, schedule, service, specialty, *, doctor_id: UUID | None = None, facility_id: UUID | None = None
    ) -> None:
        """Ensure selected catalog resources match the doctor and schedule."""
        resolved_doctor_id = doctor_id or schedule.doctor_id
        resolved_facility_id = facility_id or schedule.facility_id
        if schedule is not None and getattr(schedule, "service_id", None) not in (
            None,
            service.id if service else None,
        ):
            raise ConflictError("SERVICE_NOT_AVAILABLE", "Service does not match this schedule")
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
        log_event(logger, logging.INFO, "booking.list.start", status=status)
        values = await self.bookings.list_for_user(user_id, status, offset, limit)
        log_event(logger, logging.INFO, "booking.list.done", status=status)
        return values

    async def get(self, user_id: UUID, booking_id: UUID) -> Booking:
        """Get one booking owned by a patient."""
        log_event(logger, logging.INFO, "booking.get.start", booking_id=str(booking_id))
        booking = await self.bookings.get_for_user(booking_id, user_id)
        if booking is None:
            log_event(logger, logging.WARNING, "booking.get.not_found", booking_id=str(booking_id))
            raise NotFoundError("Booking not found")
        log_event(logger, logging.INFO, "booking.get.done", booking_id=str(booking_id), status=booking.status)
        return booking

    async def cancel(self, user_id: UUID, booking_id: UUID, reason: str | None) -> Booking:
        """Cancel an owned booking without deleting its history."""
        log_event(logger, logging.INFO, "booking.cancel.start", booking_id=str(booking_id))
        async with self.session.begin():
            booking = await self.bookings.get_for_user(booking_id, user_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status == "cancelled":
                raise ConflictError("BOOKING_ALREADY_CANCELLED", "Booking is already cancelled")
            if booking.status == "rejected":
                raise ConflictError("BOOKING_NOT_CANCELLABLE", "Rejected booking cannot be cancelled")
            release_version = None
            source_schedule = None
            changed_schedules: list[DoctorSchedule] = []
            if booking.schedule_id is not None:
                source_schedule = await self.bookings.get_schedule_for_update(booking.schedule_id)
            if booking.appointment_schedule_id is None and booking.status == "pending_approval":
                draft = await get_draft(booking.id)
                appointment_schedule = DoctorSchedule(
                    id=UUID(draft["id"]) if draft and draft.get("id") else uuid4(),
                    doctor_id=booking.doctor_id,
                    facility_id=booking.facility_id,
                    service_id=booking.service_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    capacity=1,
                    status="cancelled",
                    cancellation_reason=reason.strip() if reason else "Booking cancelled",
                )
                self.session.add(appointment_schedule)
                booking.appointment_schedule_id = appointment_schedule.id
                changed_schedules.append(appointment_schedule)
            elif booking.appointment_schedule_id is not None:
                appointment_schedule = await self.bookings.get_schedule_for_update(booking.appointment_schedule_id)
                if appointment_schedule and appointment_schedule.status != "cancelled":
                    appointment_schedule.status = "cancelled"
                    appointment_schedule.cancellation_reason = reason.strip() if reason else "Booking cancelled"
                    appointment_schedule.version += 1
                    appointment_schedule.updated_by = user_id
                    changed_schedules.append(appointment_schedule)
            if source_schedule and booking.status == "confirmed":
                source_schedule.capacity += 1
                source_schedule.version += 1
                source_schedule.updated_by = user_id
                release_version = source_schedule.version
                changed_schedules.append(source_schedule)
            booking.status = "cancelled"
            booking.cancellation_reason = reason.strip() if reason else None
            consultation = (
                await self.session.execute(
                    select(ConsultationRequest)
                    .where(
                        ConsultationRequest.booking_id == booking.id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if consultation is not None:
                await self.session.execute(
                    select(ConsultationSession.id)
                    .where(
                        ConsultationSession.id == consultation.session_id,
                    )
                    .with_for_update()
                )
                consultation.status = "cancelled"
                self.session.add(
                    ConsultationRequestEvent(
                        request_id=consultation.id,
                        actor_id=user_id,
                        action="cancelled",
                        note=booking.cancellation_reason,
                    )
                )
            await self.session.flush()
            release_schedule_id = booking.schedule_id
        for value in changed_schedules:
            await cache_schedule(value)
        await invalidate_redis_api_cache("staff-bookings")
        await release_booking_reservation(booking_id, release_schedule_id, release_version, booking.doctor_id)
        log_event(logger, logging.INFO, "booking.cancel.done", booking_id=str(booking_id), status="cancelled")
        return await self.get(user_id, booking_id)

    async def reschedule(self, user_id: UUID, booking_id: UUID, request: BookingRescheduleCreate) -> Booking:
        """Move an owned scheduled booking to a newly held slot for re-approval."""
        log_event(logger, logging.INFO, "booking.reschedule.start", booking_id=str(booking_id))
        changed_schedules: list[DoctorSchedule] = []
        async with self.session.begin():
            booking = await self.bookings.get_for_user(booking_id, user_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            coordination_result = await self.session.execute(
                select(ConsultationRequest.id).where(ConsultationRequest.booking_id == booking.id)
            )
            is_coordinated = coordination_result.first() if hasattr(coordination_result, "first") else None
            if is_coordinated:
                raise ConflictError(
                    "COORDINATED_BOOKING", "Please contact the coordinator to reschedule this appointment"
                )
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
            prior_schedule_id = old_schedule.id
            self._validate_schedule(new_schedule)

            hold = await self.bookings.get_hold_for_user(request.hold_id, user_id, for_update=True)
            if hold is None:
                raise NotFoundError("Hold not found")
            if hold.status != "active" or hold.expires_at <= datetime.now(UTC):
                raise ConflictError("HOLD_EXPIRED", "The booking hold has expired or was released")
            if hold.schedule_id != new_schedule.id:
                raise ConflictError("HOLD_SCHEDULE_MISMATCH", "Hold does not belong to this schedule")
            if hold.service_id != booking.service_id or hold.specialty_id != booking.specialty_id:
                raise ConflictError("HOLD_REQUEST_MISMATCH", "Hold does not match the booking request")

            active_count = await self.bookings.count_reservations_for_schedule(
                new_schedule.id,
                exclude_hold_id=hold.id,
                exclude_booking_id=booking.id,
            )
            if booking.service and booking.service.booking_mode == "doctor_visit" and active_count >= 1:
                raise ConflictError("SCHEDULE_CONFLICT", "This doctor schedule is already booked")
            if booking.service and booking.service.booking_mode == "group" and active_count >= new_schedule.capacity:
                raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
            await self._validate_catalog_relationships(new_schedule, booking.service, booking.specialty)

            old_values = {
                "schedule_id": str(booking.schedule_id),
                "starts_at": booking.starts_at.isoformat(),
                "ends_at": booking.ends_at.isoformat(),
                "status": booking.status,
            }
            if booking.appointment_schedule_id is not None:
                old_appointment = await self.bookings.get_schedule_for_update(booking.appointment_schedule_id)
                if old_appointment is not None and old_appointment.status != "cancelled":
                    old_appointment.status = "cancelled"
                    old_appointment.cancellation_reason = "Booking rescheduled"
                    old_appointment.version += 1
                    old_appointment.updated_by = user_id
                    changed_schedules.append(old_appointment)
            if booking.status == "confirmed":
                old_schedule.capacity += 1
                old_schedule.version += 1
                old_schedule.updated_by = user_id
                changed_schedules.append(old_schedule)
            prior_schedule_version = old_schedule.version
            booking.appointment_schedule_id = None
            await self.notifications.discard_reminders_for_booking(booking.id)
            booking.schedule_id = new_schedule.id
            booking.doctor_id = new_schedule.doctor_id
            booking.facility_id = new_schedule.facility_id
            booking.starts_at = new_schedule.starts_at
            booking.ends_at = new_schedule.ends_at
            booking.hold_id = hold.id
            booking.status = "pending_approval"
            booking.expired_at = datetime.now(UTC) + timedelta(hours=24)
            booking.staff_note = None
            booking.reviewed_by = None
            booking.reviewed_at = None
            hold.status = "consumed"
            hold.released_at = datetime.now(UTC)
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
            draft = {
                "id": str(uuid4()),
                "doctor_id": str(new_schedule.doctor_id),
                "facility_id": str(new_schedule.facility_id),
                "service_id": str(booking.service_id),
                "starts_at": new_schedule.starts_at.isoformat(),
                "ends_at": new_schedule.ends_at.isoformat(),
                "capacity": 1,
                "status": "draft",
            }
            expires_at = booking.expired_at
            new_schedule_id = new_schedule.id
            new_schedule_version = new_schedule.version
            new_schedule_capacity = new_schedule.capacity
            doctor_id = new_schedule.doctor_id
        await invalidate_redis_api_cache("staff-bookings")
        await release_booking_reservation(booking_id, prior_schedule_id, prior_schedule_version, doctor_id)
        for value in changed_schedules:
            await cache_schedule(value)
        pending_count_cached = await pending_count(new_schedule_id, new_schedule_version)
        if pending_count_cached is None:
            pending = await self.bookings.list_pending_reservations(new_schedule_id)
            await pending_count(new_schedule_id, new_schedule_version, pending)
        else:
            pending = []
        holds = await self.bookings.count_active_holds_for_schedule(new_schedule_id)
        reserved = await reserve_schedule(
            schedule_id=new_schedule_id,
            booking_id=booking_id,
            capacity=new_schedule_capacity,
            schedule_version=new_schedule_version,
            active_holds=holds,
            pending=pending,
            expires_at=expires_at,
            draft=draft,
        )
        if reserved is None:
            await save_draft(booking_id, draft, expires_at)
        log_event(logger, logging.INFO, "booking.reschedule.done", booking_id=str(booking_id))
        return await self.get(user_id, booking_id)

    async def list_for_staff(
        self,
        status: str | None,
        selected_date: date | None,
        offset: int,
        limit: int,
        query: str | None = None,
        service_id: UUID | None = None,
        scheduled_only: bool = False,
        date_field: str = "starts_at",
        include_cancelled: bool = False,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Booking], int, dict[str, int], dict[UUID, dict]]:
        """List booking records for a staff review queue."""
        log_event(logger, logging.INFO, "booking.staff_list.start", status=status)
        values, total, status_counts = await self.bookings.list_for_staff(
            status,
            selected_date,
            offset,
            limit,
            query,
            service_id,
            scheduled_only,
            date_field,
            include_cancelled,
            date_from,
            date_to,
        )
        ai_triage = await self.bookings.get_staff_ai_triage([value.id for value in values])
        log_event(logger, logging.INFO, "booking.staff_list.done", status=status)
        return values, total, status_counts, ai_triage

    async def cancel_for_staff(self, booking_id: UUID, actor_id: UUID, reason: str) -> Booking:
        """Cancel one confirmed, scheduled appointment and release its capacity atomically."""
        changed_schedules: list[DoctorSchedule] = []
        reservation_version = None
        async with self.session.begin():
            booking = await self.bookings.get_for_staff(booking_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status != "confirmed":
                raise ConflictError("BOOKING_NOT_CANCELLABLE", "Only confirmed appointments can be cancelled")
            if booking.appointment_schedule_id is None:
                raise ConflictError("APPOINTMENT_NOT_SCHEDULED", "Booking has no confirmed appointment schedule")

            appointment = await self.bookings.get_schedule_for_update(booking.appointment_schedule_id)
            if appointment is None or appointment.status != "available":
                raise ConflictError("APPOINTMENT_NOT_SCHEDULED", "Appointment schedule is no longer active")
            appointment.status = "cancelled"
            appointment.cancellation_reason = reason
            appointment.version += 1
            appointment.updated_by = actor_id
            changed_schedules.append(appointment)

            if booking.schedule_id is not None:
                source = await self.bookings.get_schedule_for_update(booking.schedule_id)
                if source is not None:
                    source.capacity += 1
                    source.version += 1
                    source.updated_by = actor_id
                    reservation_version = source.version
                    changed_schedules.append(source)

            booking.status = "cancelled"
            booking.cancellation_reason = reason
            booking.reviewed_by = actor_id
            booking.reviewed_at = datetime.now(UTC)
            self.session.add(
                CatalogAuditEvent(
                    actor_id=actor_id,
                    entity_type="booking",
                    entity_id=booking.id,
                    action="cancelled",
                    payload={"reason": reason},
                )
            )
            await self.notifications.discard_reminders_for_booking(booking.id)
            await self.notifications.create_for_booking_cancelled(booking, reason)
            await self.session.flush()

        await release_booking_reservation(booking.id, booking.schedule_id, reservation_version, booking.doctor_id)
        for schedule in changed_schedules:
            await cache_schedule(schedule)
        await invalidate_redis_api_cache("staff-bookings")
        return await self.get_for_staff(booking_id)

    async def get_staff_ai_triage(self, booking_id: UUID) -> dict | None:
        return (await self.bookings.get_staff_ai_triage([booking_id])).get(booking_id)

    async def get_for_staff(self, booking_id: UUID) -> Booking:
        """Fetch one booking for staff review."""
        log_event(logger, logging.INFO, "booking.staff_get.start", booking_id=str(booking_id))
        booking = await self.bookings.get_for_staff(booking_id)
        if booking is None:
            log_event(logger, logging.WARNING, "booking.staff_get.not_found", booking_id=str(booking_id))
            raise NotFoundError("Booking not found")
        log_event(logger, logging.INFO, "booking.staff_get.done", booking_id=str(booking_id), status=booking.status)
        return booking

    async def review(self, booking_id: UUID, actor_id: UUID, request: StaffBookingStatusUpdate) -> Booking:
        """Approve or reject a booking exactly once as staff."""
        log_event(logger, logging.INFO, "booking.review.start", booking_id=str(booking_id))
        expired = False
        reviewed_case = None
        reservation_schedule_id = None
        reservation_schedule_version = None
        reservation_doctor_id = None
        changed_schedules: list[DoctorSchedule] = []
        async with self.session.begin():
            booking = await self.bookings.get_for_staff(booking_id, for_update=True)
            if booking is None:
                raise NotFoundError("Booking not found")
            if booking.status != "pending_approval":
                raise ConflictError("BOOKING_ALREADY_REVIEWED", "Only pending bookings can be reviewed")
            expired = booking.expired_at is not None and booking.expired_at <= datetime.now(UTC)
            if request.status == "rejected" and not request.note:
                raise ConflictError("REJECTION_NOTE_REQUIRED", "A rejection reason is required")
            if request.status == "confirmed" and not expired:
                await self.bookings.get_doctor(booking.doctor_id, for_update=True)
            source_schedule = None
            if booking.schedule_id is not None:
                source_schedule = await self.bookings.get_schedule_for_update(booking.schedule_id)
                if source_schedule is None:
                    raise ConflictError("SCHEDULE_UNAVAILABLE", "Source schedule was not found")
                if (
                    request.status == "confirmed"
                    and not expired
                    and (source_schedule.status != "available" or source_schedule.capacity < 1)
                ):
                    raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
                if request.status == "confirmed" and not expired:
                    capacity = (
                        1
                        if booking.service and booking.service.booking_mode == "doctor_visit"
                        else source_schedule.capacity
                    )
                    reserved_count = await self.bookings.count_reservations_for_schedule(
                        source_schedule.id, exclude_booking_id=booking.id
                    )
                    if reserved_count >= capacity:
                        raise ConflictError("CAPACITY_EXCEEDED", "This schedule has no remaining capacity")
            if request.status == "confirmed" and not expired and booking.schedule_id is None:
                if await self.bookings.has_schedule_overlap(booking.doctor_id, booking.starts_at, booking.ends_at):
                    raise ConflictError("SCHEDULE_CONFLICT", "Doctor already has an overlapping schedule")
            if expired:
                draft = await get_draft(booking.id)
                appointment_schedule = DoctorSchedule(
                    id=UUID(draft["id"]) if draft and draft.get("id") else uuid4(),
                    doctor_id=booking.doctor_id,
                    facility_id=booking.facility_id,
                    service_id=booking.service_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    capacity=1,
                    status="cancelled",
                    cancellation_reason="Booking review expired",
                )
                self.session.add(appointment_schedule)
                booking.appointment_schedule_id = appointment_schedule.id
                changed_schedules.append(appointment_schedule)
                booking.status = "expired"
                await self.notifications.create_for_booking_expired(booking)
                await self.session.flush()
                reservation_schedule_id = source_schedule.id if source_schedule else None
                reservation_schedule_version = source_schedule.version if source_schedule else None
                reservation_doctor_id = booking.doctor_id
            else:
                draft = await get_draft(booking.id)
                appointment_schedule_id = UUID(draft["id"]) if draft and draft.get("id") else uuid4()
                appointment_schedule = DoctorSchedule(
                    id=appointment_schedule_id,
                    doctor_id=booking.doctor_id,
                    facility_id=booking.facility_id,
                    service_id=booking.service_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    capacity=1,
                    status="available" if request.status == "confirmed" else "cancelled",
                    created_by=actor_id,
                    updated_by=actor_id,
                    cancellation_reason=request.note if request.status == "rejected" else None,
                )
                self.session.add(appointment_schedule)
                booking.appointment_schedule_id = appointment_schedule.id
                changed_schedules.append(appointment_schedule)
                if request.status == "confirmed" and source_schedule:
                    source_schedule.capacity -= 1
                    source_schedule.version += 1
                    source_schedule.updated_by = actor_id
                    changed_schedules.append(source_schedule)
                booking.status = request.status
                booking.staff_note = request.note
                booking.reviewed_by = actor_id
                booking.reviewed_at = datetime.now(UTC)
                await self.notifications.create_for_booking_review(booking, request.status)
                reviewed_case = await record_booking_review(
                    self.session, booking, actor_id, request.status, request.note or ""
                )
                await self.session.flush()
                reservation_schedule_id = source_schedule.id if source_schedule else None
                reservation_schedule_version = source_schedule.version if source_schedule else None
                reservation_doctor_id = booking.doctor_id
        await release_booking_reservation(
            booking_id,
            reservation_schedule_id,
            reservation_schedule_version,
            reservation_doctor_id,
        )
        for value in changed_schedules:
            await cache_schedule(value)
        await invalidate_redis_api_cache("staff-bookings")
        if reviewed_case is not None:
            await invalidate_redis_api_cache("workbench-cases")
            await publish_workbench_case_update(reviewed_case)
        if expired:
            log_event(logger, logging.WARNING, "booking.review.expired", booking_id=str(booking_id))
            raise ConflictError("BOOKING_EXPIRED", "Booking approval deadline has passed")
        log_event(logger, logging.INFO, "booking.review.done", booking_id=str(booking_id), status=request.status)
        return await self.get_for_staff(booking_id)

    async def expire_pending_bookings(self, limit: int = 100) -> int:
        """Expire pending approvals and enqueue patient notifications atomically."""
        log_event(logger, logging.INFO, "booking.expire.start")
        expired_schedules: list[DoctorSchedule] = []
        async with self.session.begin():
            bookings = await self.bookings.claim_expired_pending_bookings(datetime.now(UTC), limit)
            for booking in bookings:
                draft = await get_draft(booking.id)
                appointment_schedule = DoctorSchedule(
                    id=UUID(draft["id"]) if draft and draft.get("id") else uuid4(),
                    doctor_id=booking.doctor_id,
                    facility_id=booking.facility_id,
                    service_id=booking.service_id,
                    starts_at=booking.starts_at,
                    ends_at=booking.ends_at,
                    capacity=1,
                    status="cancelled",
                    cancellation_reason="Booking review expired",
                )
                self.session.add(appointment_schedule)
                booking.appointment_schedule_id = appointment_schedule.id
                expired_schedules.append(appointment_schedule)
                booking.status = "expired"
                await self.notifications.create_for_booking_expired(booking)
            if bookings:
                await self.session.flush()
        if bookings:
            await invalidate_redis_api_cache("staff-bookings")
        for value in expired_schedules:
            await cache_schedule(value)
        for booking in bookings:
            await release_booking_reservation(
                booking.id,
                booking.schedule_id,
                None,
                booking.doctor_id,
            )
        log_event(logger, logging.INFO, "booking.expire.done")
        return len(bookings)

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
        appointment_schedule_id=value.appointment_schedule_id,
        hold_id=value.hold_id,
        service_id=value.service_id,
        specialty_id=value.specialty_id,
        doctor_id=value.doctor_id,
        facility_id=value.facility_id,
        starts_at=value.starts_at,
        ends_at=value.ends_at,
        booking_mode=value.service.booking_mode if value.service else "doctor_visit",
        encounter_type=value.encounter_type,
        reason=value.reason,
        patient_note=value.patient_note,
        status=value.status,
        expired_at=value.expired_at,
        cancellation_reason=value.cancellation_reason,
        staff_note=value.staff_note,
        reviewed_by=value.reviewed_by,
        reviewed_at=value.reviewed_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def booking_hold_response(value: BookingHold) -> BookingHoldResponse:
    """Map a hold to its stable API representation."""
    return BookingHoldResponse(
        id=value.id,
        user_id=value.user_id,
        schedule_id=value.schedule_id,
        service_id=value.service_id,
        specialty_id=value.specialty_id,
        status=value.status,
        expires_at=value.expires_at,
        released_at=value.released_at,
        created_at=value.created_at,
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
