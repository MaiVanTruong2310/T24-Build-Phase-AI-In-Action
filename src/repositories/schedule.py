"""Doctor schedule persistence queries."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.catalog import Doctor, DoctorSchedule, Facility, Service


class ScheduleRepositoryMixin:
    """Schedule queries composed into the catalog repository."""

    async def get_schedule(self, schedule_id: UUID, *, for_update: bool = False) -> DoctorSchedule | None:
        """Fetch a schedule with its doctor and facility."""
        statement = (
            select(DoctorSchedule)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .where(DoctorSchedule.id == schedule_id)
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_schedule_by_external_identity(
        self,
        source_system: str,
        external_schedule_id: str,
        *,
        for_update: bool = False,
    ) -> DoctorSchedule | None:
        """Find an imported schedule by its idempotency identity."""
        statement = select(DoctorSchedule).where(
            DoctorSchedule.source_system == source_system,
            DoctorSchedule.external_schedule_id == external_schedule_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def lock_doctor(self, doctor_id: UUID) -> Doctor | None:
        """Lock a doctor row so schedule conflict checks serialize per doctor."""
        statement = select(Doctor).where(Doctor.id == doctor_id).with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_schedule_conflict(
        self,
        *,
        doctor_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        exclude_schedule_id: UUID | None = None,
    ) -> DoctorSchedule | None:
        """Find an active schedule that overlaps the requested time range."""
        statement = (
            select(DoctorSchedule)
            .where(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.status != "cancelled",
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
            )
            .order_by(DoctorSchedule.starts_at)
            .limit(1)
        )
        if exclude_schedule_id:
            statement = statement.where(DoctorSchedule.id != exclude_schedule_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_schedules(
        self,
        *,
        doctor_id: UUID | None,
        facility_id: UUID | None,
        service_id: UUID | None,
        starts_from: datetime | None,
        starts_to: datetime | None,
        schedule_status: str | None,
        source_system: str | None,
        public_only: bool,
        offset: int,
        limit: int,
    ) -> list[DoctorSchedule]:
        """List schedule slots, optionally restricted to public availability."""
        statement = (
            select(DoctorSchedule)
            .join(Doctor)
            .join(Facility)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .order_by(DoctorSchedule.starts_at)
            .offset(offset)
            .limit(limit)
        )
        if doctor_id:
            statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
        if facility_id:
            statement = statement.where(DoctorSchedule.facility_id == facility_id)
        if service_id:
            statement = statement.where(DoctorSchedule.service_id == service_id)
        if starts_from:
            statement = statement.where(DoctorSchedule.ends_at > starts_from)
        if starts_to:
            statement = statement.where(DoctorSchedule.starts_at < starts_to)
        if schedule_status:
            statement = statement.where(DoctorSchedule.status == schedule_status)
        if source_system:
            statement = statement.where(DoctorSchedule.source_system == source_system)
        if public_only:
            statement = statement.where(
                DoctorSchedule.status == "available",
                DoctorSchedule.capacity > 0,
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
                Facility.status == "active",
            )
        return list((await self.session.execute(statement)).scalars().all())
