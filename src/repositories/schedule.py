"""Doctor schedule persistence queries."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import selectinload

from src.models.booking import Booking
from src.models.catalog import Doctor, DoctorSchedule, Facility, Service
from src.models.doctor import DoctorService


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

    async def has_doctor_service(self, doctor_id: UUID, service_id: UUID) -> bool:
        """Check that a doctor offers a selected service."""
        statement = select(DoctorService.id).where(
            DoctorService.doctor_id == doctor_id,
            DoctorService.service_id == service_id,
            DoctorService.active.is_(True),
        )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def count_active_bookings_for_schedules(self, schedule_ids: list[UUID]) -> dict[UUID, int]:
        """Count pending and confirmed reservations for a schedule batch."""
        if not schedule_ids:
            return {}
        statement = (
            select(Booking.schedule_id, func.count(Booking.id))
            .where(
                Booking.schedule_id.in_(schedule_ids),
                Booking.status.in_(("pending_approval", "confirmed")),
            )
            .group_by(Booking.schedule_id)
        )
        return {schedule_id: int(count) for schedule_id, count in (await self.session.execute(statement)).all()}

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
                DoctorSchedule.type == "consultation",
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
            )
            .order_by(DoctorSchedule.starts_at)
            .limit(1)
        )
        if exclude_schedule_id:
            statement = statement.where(DoctorSchedule.id != exclude_schedule_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def find_blocking_schedule(
        self, *, doctor_id: UUID, facility_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> DoctorSchedule | None:
        """Find a busy schedule that applies globally or to one facility."""
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
            .outerjoin(Facility)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .order_by(DoctorSchedule.starts_at)
            .offset(offset)
            .limit(limit)
        )
        if doctor_id:
            statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
        if facility_id:
            statement = statement.where(
                or_(
                    DoctorSchedule.facility_id == facility_id,
                    and_(DoctorSchedule.type != "consultation", DoctorSchedule.facility_id.is_(None)),
                )
            )
        if service_id:
            service_available = exists(
                select(DoctorService.id)
                .join(Service, Service.id == DoctorService.service_id)
                .where(
                    DoctorService.doctor_id == DoctorSchedule.doctor_id,
                    DoctorService.service_id == service_id,
                    DoctorService.active.is_(True),
                    Service.status == "active",
                )
            )
            statement = statement.where(or_(DoctorSchedule.type != "consultation", service_available))
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
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
                DoctorSchedule.status != "cancelled",
                or_(
                    and_(
                        DoctorSchedule.type == "consultation",
                        DoctorSchedule.status == "available",
                        Facility.status == "active",
                    ),
                    and_(
                        DoctorSchedule.type != "consultation",
                        or_(DoctorSchedule.facility_id.is_(None), Facility.status == "active"),
                    ),
                ),
            )
        return list((await self.session.execute(statement)).scalars().all())
