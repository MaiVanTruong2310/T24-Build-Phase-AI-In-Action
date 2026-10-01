"""Persistence queries for patient bookings."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import selectinload

from src.models.booking import Booking
from src.models.catalog import DoctorSchedule, Service, Specialty
from src.models.doctor import Doctor, DoctorService, DoctorSpecialty
from src.models.facility import Facility
from src.models.notification import Notification


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

    async def find_schedule_conflict(
        self, *, doctor_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> DoctorSchedule | None:
        """Find an active schedule overlapping a requested appointment time."""
        statement = (
            select(DoctorSchedule)
            .where(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.status != "cancelled",
                DoctorSchedule.type == "consultation",
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
            )
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_blocking_schedule(
        self, *, doctor_id: UUID, facility_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> DoctorSchedule | None:
        """Find a busy block that applies globally or to the selected facility."""
        statement = (
            select(DoctorSchedule)
            .where(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.type.in_(("busy", "leave", "other")),
                DoctorSchedule.status != "cancelled",
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
                or_(DoctorSchedule.facility_id.is_(None), DoctorSchedule.facility_id == facility_id),
            )
            .order_by(DoctorSchedule.starts_at)
            .limit(1)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_active_booking_conflict(
        self, *, doctor_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> Booking | None:
        """Find an active appointment overlapping a requested doctor-visit time."""
        statement = (
            select(Booking)
            .where(
                Booking.doctor_id == doctor_id,
                Booking.status.in_(("pending_approval", "confirmed")),
                Booking.starts_at < ends_at,
                Booking.ends_at > starts_at,
            )
            .order_by(Booking.starts_at)
            .limit(1)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def add_schedule(self, schedule: DoctorSchedule) -> None:
        """Stage a schedule created as part of staff booking approval."""
        self.session.add(schedule)
        await self.session.flush()

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

    async def get_doctor_for_update(self, doctor_id: UUID) -> Doctor | None:
        """Lock a doctor while validating a requested-time booking."""
        return await self._one(select(Doctor).where(Doctor.id == doctor_id).with_for_update())

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
        """Count bookings that currently reserve a schedule slot."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status.in_(("pending_approval", "confirmed")),
        )
        return int((await self.session.execute(statement)).scalar_one())

    async def count_reservations_for_schedule(
        self,
        schedule_id: UUID,
        *,
        exclude_booking_id: UUID | None = None,
    ) -> int:
        """Count active bookings, optionally excluding one booking."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status.in_(("pending_approval", "confirmed")),
        )
        if exclude_booking_id:
            statement = statement.where(Booking.id != exclude_booking_id)
        return int((await self.session.execute(statement)).scalar_one())

    async def add(self, booking: Booking) -> None:
        """Stage a booking for the current transaction."""
        self.session.add(booking)
        await self.session.flush()

    async def get_booking_by_idempotency(self, user_id: UUID, key: str) -> Booking | None:
        """Find a previous booking attempt for the same user and key."""
        return await self._one(
            self._with_context(
                select(Booking).where(
                    Booking.user_id == user_id,
                    Booking.idempotency_key == key,
                )
            )
        )

    async def claim_expired_pending_bookings(self, now: datetime, limit: int) -> list[Booking]:
        """Lock pending approvals whose 24-hour deadline has passed."""
        statement = (
            select(Booking)
            .where(
                Booking.status == "pending_approval",
                Booking.expired_at <= now,
            )
            .order_by(Booking.expired_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_confirmed_reminder_candidates(self, now: datetime, deadline: datetime, limit: int) -> list[Booking]:
        """Find confirmed future appointments that have no reminder yet."""
        reminder_exists = exists(
            select(Notification.id).where(
                Notification.booking_id == Booking.id,
                Notification.kind == "appointment_reminder",
                Notification.dedupe_key == func.concat("booking:", Booking.id, ":reminder:2d:in_app"),
            )
        )
        statement = (
            select(Booking)
            .where(
                Booking.status == "confirmed",
                Booking.starts_at > now,
                Booking.starts_at <= deadline,
                ~reminder_exists,
            )
            .order_by(Booking.starts_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_for_user(self, user_id: UUID, status: str | None, offset: int, limit: int) -> list[Booking]:
        """List only bookings owned by the authenticated user."""
        statement = self._with_context(select(Booking).where(Booking.user_id == user_id))
        if status:
            statement = statement.where(Booking.status == status)
        statement = statement.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_for_user(self, booking_id: UUID, user_id: UUID, *, for_update: bool = False) -> Booking | None:
        """Fetch one booking only when it belongs to the current user."""
        statement = self._with_context(select(Booking).where(Booking.id == booking_id, Booking.user_id == user_id))
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
