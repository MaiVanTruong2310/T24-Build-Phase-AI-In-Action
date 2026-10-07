"""Persistence queries for patient bookings."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from src.models.booking import Booking
from src.models.booking_hold import BookingHold
from src.models.catalog import DoctorSchedule, Service, Specialty
from src.models.doctor import Doctor, DoctorService, DoctorSpecialty
from src.models.facility import Facility


class BookingRepository:
    """Database operations used by the booking service."""

    def __init__(self, session):
        self.session = session

    async def get_schedule_for_update(self, schedule_id: UUID) -> DoctorSchedule | None:
        """Lock a schedule and load the resources needed by booking rules."""
        statement = (
            select(DoctorSchedule)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .where(DoctorSchedule.id == schedule_id)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_schedules_for_update(self, schedule_ids: set[UUID]) -> dict[UUID, DoctorSchedule]:
        """Lock schedules in deterministic UUID order for safe rescheduling."""
        if not schedule_ids:
            return {}
        statement = (
            select(DoctorSchedule)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .where(DoctorSchedule.id.in_(schedule_ids))
            .order_by(DoctorSchedule.id)
            .with_for_update()
        )
        schedules = (await self.session.execute(statement)).scalars().all()
        return {schedule.id: schedule for schedule in schedules}

    async def get_service(self, service_id: UUID) -> Service | None:
        """Fetch a service by UUID."""
        return await self._one(select(Service).where(Service.id == service_id))

    async def get_doctor(self, doctor_id: UUID) -> Doctor | None:
        """Fetch a doctor for a requested-time booking."""
        return await self._one(select(Doctor).where(Doctor.id == doctor_id))

    async def get_facility(self, facility_id: UUID) -> Facility | None:
        """Fetch a facility for a requested-time booking."""
        return await self._one(select(Facility).where(Facility.id == facility_id))

    async def get_specialty(self, specialty_id: UUID) -> Specialty | None:
        """Fetch a specialty by UUID."""
        return await self._one(select(Specialty).where(Specialty.id == specialty_id))

    async def has_doctor_service(self, doctor_id: UUID, service_id: UUID) -> bool:
        """Check that the selected doctor offers the selected service."""
        statement = select(DoctorService.id).where(
            DoctorService.doctor_id == doctor_id,
            DoctorService.service_id == service_id,
            DoctorService.active.is_(True),
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def has_doctor_specialty(self, doctor_id: UUID, specialty_id: UUID) -> bool:
        """Check that the selected doctor belongs to the selected specialty."""
        statement = select(DoctorSpecialty.id).where(
            DoctorSpecialty.doctor_id == doctor_id,
            DoctorSpecialty.specialty_id == specialty_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def has_doctor_facility(self, doctor_id: UUID, facility_id: UUID) -> bool:
        """Check that the doctor is assigned to the requested facility."""
        from src.models.doctor import DoctorFacility

        statement = select(DoctorFacility.id).where(
            DoctorFacility.doctor_id == doctor_id,
            DoctorFacility.facility_id == facility_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def count_active_for_schedule(self, schedule_id: UUID) -> int:
        """Count bookings and non-expired holds that consume a schedule slot."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status.notin_(("cancelled", "rejected")),
        )
        bookings = int((await self.session.execute(statement)).scalar_one())
        holds = await self.count_active_holds_for_schedule(schedule_id)
        return bookings + holds

    async def count_active_holds_for_schedule(self, schedule_id: UUID, *, exclude_hold_id: UUID | None = None) -> int:
        """Count active, non-expired holds for a schedule."""
        statement = select(func.count(BookingHold.id)).where(
            BookingHold.schedule_id == schedule_id,
            BookingHold.status == "active",
            BookingHold.expires_at > datetime.now(UTC),
        )
        if exclude_hold_id:
            statement = statement.where(BookingHold.id != exclude_hold_id)
        return int((await self.session.execute(statement)).scalar_one())

    async def count_reservations_for_schedule(
        self,
        schedule_id: UUID,
        *,
        exclude_hold_id: UUID | None = None,
        exclude_booking_id: UUID | None = None,
    ) -> int:
        """Count bookings and active holds, optionally excluding one hold."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status.notin_(("cancelled", "rejected")),
        )
        if exclude_booking_id:
            statement = statement.where(Booking.id != exclude_booking_id)
        bookings = int((await self.session.execute(statement)).scalar_one())
        return bookings + await self.count_active_holds_for_schedule(schedule_id, exclude_hold_id=exclude_hold_id)

    async def add(self, booking: Booking) -> None:
        """Stage a booking for the current transaction."""
        self.session.add(booking)
        await self.session.flush()

    async def add_hold(self, hold: BookingHold) -> None:
        """Stage a hold for the current transaction."""
        self.session.add(hold)
        await self.session.flush()

    async def get_active_hold_for_user_schedule(
        self, user_id: UUID, schedule_id: UUID, *, for_update: bool = False
    ) -> BookingHold | None:
        """Find one active hold owned by a patient for a schedule."""
        statement = select(BookingHold).where(
            (BookingHold.user_id == user_id) | (BookingHold.requested_by_user_id == user_id),
            BookingHold.schedule_id == schedule_id,
            BookingHold.status == "active",
            BookingHold.expires_at > datetime.now(UTC),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_hold_for_user(self, hold_id: UUID, user_id: UUID, *, for_update: bool = False) -> BookingHold | None:
        """Fetch a hold only when it belongs to the current user."""
        statement = select(BookingHold).where(BookingHold.id == hold_id, (BookingHold.user_id == user_id) | (BookingHold.requested_by_user_id == user_id))
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_hold(self, hold_id: UUID, *, for_update: bool = False) -> BookingHold | None:
        """Fetch a hold by ID for staff-owned maintenance flows."""
        statement = select(BookingHold).where(BookingHold.id == hold_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_booking_by_idempotency(self, user_id: UUID, key: str) -> Booking | None:
        """Find a previous booking attempt for the same user and key."""
        return await self._one(
            self._with_context(
                select(Booking).where(
                    (Booking.user_id == user_id) | (Booking.requested_by_user_id == user_id),
                    Booking.idempotency_key == key,
                )
            )
        )

    async def release_expired_holds(self, now: datetime | None = None) -> int:
        """Mark expired active holds as released capacity."""
        current_time = now or datetime.now(UTC)
        result = await self.session.execute(
            update(BookingHold)
            .where(BookingHold.status == "active", BookingHold.expires_at <= current_time)
            .values(status="expired", released_at=current_time, updated_at=current_time)
        )
        return int(result.rowcount or 0)

    async def claim_expired_pending_bookings(self, now: datetime, limit: int) -> list[Booking]:
        """Lock a bounded batch of pending bookings past the 24-hour approval deadline."""
        statement = (
            self._with_context(
                select(Booking).where(
                    Booking.status == "pending_approval",
                    Booking.expired_at.is_not(None),
                    Booking.expired_at <= now,
                )
            )
            .order_by(Booking.expired_at, Booking.id)
            .limit(max(0, limit))
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_for_user(self, user_id: UUID, status: str | None, offset: int, limit: int) -> list[Booking]:
        """List only bookings owned by the authenticated user."""
        statement = self._with_context(select(Booking).where((Booking.user_id == user_id) | (Booking.requested_by_user_id == user_id)))
        if status:
            statement = statement.where(Booking.status == status)
        statement = statement.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_for_user(self, booking_id: UUID, user_id: UUID, *, for_update: bool = False) -> Booking | None:
        """Fetch one booking only when it belongs to the current user."""
        statement = self._with_context(select(Booking).where(Booking.id == booking_id, (Booking.user_id == user_id) | (Booking.requested_by_user_id == user_id)))
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_for_staff(
        self,
        status: str | None,
        selected_date: date | None,
        offset: int,
        limit: int,
    ) -> list[Booking]:
        """List bookings for the staff review queue."""
        statement = self._with_context(select(Booking))
        if status:
            statement = statement.where(Booking.status == status)
        else:
            statement = statement.where(Booking.status != "cancelled")
        if selected_date:
            statement = statement.where(func.date(Booking.starts_at) == selected_date)
        statement = statement.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_for_staff(self, booking_id: UUID, *, for_update: bool = False) -> Booking | None:
        """Fetch one booking with all staff review context."""
        statement = self._with_context(select(Booking).where(Booking.id == booking_id))
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    @staticmethod
    def _with_context(statement):
        return statement.options(
            selectinload(Booking.user),
            selectinload(Booking.schedule).selectinload(DoctorSchedule.doctor),
            selectinload(Booking.schedule).selectinload(DoctorSchedule.facility),
            selectinload(Booking.doctor),
            selectinload(Booking.facility),
            selectinload(Booking.service),
            selectinload(Booking.specialty),
        )

    async def _one(self, statement):
        return (await self.session.execute(statement)).scalar_one_or_none()
