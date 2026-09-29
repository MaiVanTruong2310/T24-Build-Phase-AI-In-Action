"""Persistence queries for patient bookings."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.models.booking import Booking
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
        """Count bookings that still consume a schedule slot."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status.notin_(("cancelled", "rejected")),
        )
        return int((await self.session.execute(statement)).scalar_one())

    async def add(self, booking: Booking) -> None:
        """Stage a booking for the current transaction."""
        self.session.add(booking)
        await self.session.flush()

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
