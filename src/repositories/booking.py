"""Persistence queries for patient bookings."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import String, cast, exists, func, or_, select, update
from sqlalchemy.orm import selectinload

from src.models.booking import Booking
from src.models.booking_hold import BookingHold
from src.models.catalog import DoctorSchedule, Service, Specialty
from src.models.doctor import Doctor, DoctorService, DoctorSpecialty
from src.models.facility import Facility
from src.models.patient_profile import PatientProfile
from src.models.user import User
from src.models.workbench import CoordinationCase


class BookingRepository:
    """Database operations used by the booking service."""

    def __init__(self, session):
        self.session = session

    async def get_schedule_for_update(self, schedule_id: UUID) -> DoctorSchedule | None:
        """Lock a schedule and load the resources needed by booking rules."""
        statement = (
            select(DoctorSchedule)
            .options(
                selectinload(DoctorSchedule.doctor),
                selectinload(DoctorSchedule.facility),
                selectinload(DoctorSchedule.service),
            )
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
            .options(
                selectinload(DoctorSchedule.doctor),
                selectinload(DoctorSchedule.facility),
                selectinload(DoctorSchedule.service),
            )
            .where(DoctorSchedule.id.in_(schedule_ids))
            .order_by(DoctorSchedule.id)
            .with_for_update()
        )
        schedules = (await self.session.execute(statement)).scalars().all()
        return {schedule.id: schedule for schedule in schedules}

    async def get_service(self, service_id: UUID) -> Service | None:
        """Fetch a service by UUID."""
        return await self._one(select(Service).where(Service.id == service_id))

    async def get_doctor(self, doctor_id: UUID, *, for_update: bool = False) -> Doctor | None:
        """Fetch a doctor for a requested-time booking."""
        statement = select(Doctor).where(Doctor.id == doctor_id)
        if for_update:
            statement = statement.with_for_update()
        return await self._one(statement)

    async def has_pending_requested_time_overlap(self, doctor_id: UUID, starts_at: datetime, ends_at: datetime) -> bool:
        """Check pending free-time requests when Redis is not available."""
        value = await self.session.scalar(
            select(Booking.id)
            .where(
                Booking.schedule_id.is_(None),
                Booking.status == "pending_approval",
                Booking.doctor_id == doctor_id,
                Booking.starts_at < ends_at,
                Booking.ends_at > starts_at,
                Booking.expired_at > datetime.now(UTC),
            )
            .limit(1)
        )
        return value is not None

    async def has_confirmed_appointment_overlap(self, doctor_id: UUID, starts_at: datetime, ends_at: datetime) -> bool:
        """Check requested-time approval against already persisted appointments."""
        value = await self.session.scalar(
            select(DoctorSchedule.id)
            .join(Booking, Booking.appointment_schedule_id == DoctorSchedule.id)
            .where(
                Booking.status == "confirmed",
                DoctorSchedule.status == "available",
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
            )
            .limit(1)
        )
        return value is not None

    async def has_schedule_overlap(self, doctor_id: UUID, starts_at: datetime, ends_at: datetime) -> bool:
        """Check every non-cancelled schedule, including confirmed appointment schedules."""
        value = await self.session.scalar(
            select(DoctorSchedule.id)
            .where(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.status != "cancelled",
                DoctorSchedule.starts_at < ends_at,
                DoctorSchedule.ends_at > starts_at,
            )
            .limit(1)
        )
        return value is not None

    async def get_facility(self, facility_id: UUID) -> Facility | None:
        """Fetch a facility for a requested-time booking."""
        return await self._one(select(Facility).where(Facility.id == facility_id))

    async def get_specialty(self, specialty_id: UUID) -> Specialty | None:
        """Fetch a specialty by UUID."""
        return await self._one(select(Specialty).where(Specialty.id == specialty_id))

    async def has_doctor_service(self, doctor_id: UUID, service_id: UUID) -> bool:
        """Check that the selected doctor offers an active service."""
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

    async def has_doctor_facility(self, doctor_id: UUID, facility_id: UUID, on_date: date | None = None) -> bool:
        """Check that the doctor has an active assignment at the requested facility."""
        from src.models.doctor import DoctorFacility

        statement = select(DoctorFacility.id).where(
            DoctorFacility.doctor_id == doctor_id,
            DoctorFacility.facility_id == facility_id,
        )
        if on_date:
            statement = statement.where(
                or_(DoctorFacility.active_from.is_(None), DoctorFacility.active_from <= on_date),
                or_(DoctorFacility.active_to.is_(None), DoctorFacility.active_to >= on_date),
            )
        return (await self.session.execute(statement)).scalar_one_or_none() is not None

    async def count_active_for_schedule(self, schedule_id: UUID) -> int:
        """Count pending bookings and non-expired holds against remaining capacity."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status == "pending_approval",
        )
        bookings = int((await self.session.execute(statement)).scalar_one())
        holds = await self.count_active_holds_for_schedule(schedule_id)
        return bookings + holds

    async def list_pending_reservations(self, schedule_id: UUID) -> list[tuple[UUID, datetime]]:
        """Return durable pending booking IDs and expiries for Redis recovery."""
        result = await self.session.execute(
            select(Booking.id, Booking.expired_at).where(
                Booking.schedule_id == schedule_id,
                Booking.status == "pending_approval",
                Booking.expired_at > datetime.now(UTC),
            )
        )
        return [(booking_id, expires_at) for booking_id, expires_at in result if expires_at is not None]

    async def count_active_holds_for_schedule(self, schedule_id: UUID, *, exclude_hold_id: UUID | None = None) -> int:
        """Count unexpired DB holds, optionally excluding one being consumed."""
        statement = select(func.count(BookingHold.id)).where(
            BookingHold.schedule_id == schedule_id,
            BookingHold.status == "active",
            BookingHold.expires_at > datetime.now(UTC),
        )
        if exclude_hold_id:
            statement = statement.where(BookingHold.id != exclude_hold_id)
        return int((await self.session.execute(statement)).scalar_one())

    async def count_active_holds_for_schedules(self, schedule_ids: list[UUID]) -> dict[UUID, int]:
        """Batch count unexpired database holds for schedule listing."""
        if not schedule_ids:
            return {}
        result = await self.session.execute(
            select(BookingHold.schedule_id, func.count(BookingHold.id))
            .where(
                BookingHold.schedule_id.in_(schedule_ids),
                BookingHold.status == "active",
                BookingHold.expires_at > datetime.now(UTC),
            )
            .group_by(BookingHold.schedule_id)
        )
        return {schedule_id: int(count) for schedule_id, count in result}

    async def count_reservations_for_schedule(
        self,
        schedule_id: UUID,
        *,
        exclude_hold_id: UUID | None = None,
        exclude_booking_id: UUID | None = None,
    ) -> int:
        """Count pending bookings and active holds against remaining capacity."""
        statement = select(func.count(Booking.id)).where(
            Booking.schedule_id == schedule_id,
            Booking.status == "pending_approval",
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
        statement = select(BookingHold).where(
            BookingHold.id == hold_id, (BookingHold.user_id == user_id) | (BookingHold.requested_by_user_id == user_id)
        )
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
        statement = self._with_context(
            select(Booking).where((Booking.user_id == user_id) | (Booking.requested_by_user_id == user_id))
        )
        if status:
            statement = statement.where(Booking.status == status)
        statement = statement.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_for_user(self, booking_id: UUID, user_id: UUID, *, for_update: bool = False) -> Booking | None:
        """Fetch one booking only when it belongs to the current user."""
        statement = self._with_context(
            select(Booking).where(
                Booking.id == booking_id, (Booking.user_id == user_id) | (Booking.requested_by_user_id == user_id)
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

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
    ) -> tuple[list[Booking], int, dict[str, int]]:
        """List bookings for the staff review queue."""
        common_conditions = [] if status == "cancelled" or include_cancelled else [Booking.status != "cancelled"]
        if scheduled_only:
            common_conditions.append(
                exists(
                    select(DoctorSchedule.id).where(
                        DoctorSchedule.id == Booking.appointment_schedule_id,
                        DoctorSchedule.status == "available",
                    )
                )
            )
        if selected_date and (date_from or date_to):
            raise ValueError("Use either one booking date or a date range")
        if bool(date_from) != bool(date_to):
            raise ValueError("Booking date ranges require both bounds")
        if date_from and date_to:
            if date_field not in {"starts_at", "created_at"} or date_from >= date_to:
                raise ValueError("Unsupported staff booking date range")
            local_start = datetime.combine(date_from, time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            local_end = datetime.combine(date_to, time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            date_column = Booking.starts_at if date_field == "starts_at" else Booking.created_at
            common_conditions.extend(
                (date_column >= local_start.astimezone(UTC), date_column < local_end.astimezone(UTC))
            )
        elif selected_date:
            if date_field not in {"starts_at", "created_at"}:
                raise ValueError("Unsupported staff booking date field")
            local_start = datetime.combine(selected_date, time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            local_end = datetime.combine(
                selected_date + timedelta(days=1), time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")
            )
            date_column = Booking.starts_at if date_field == "starts_at" else Booking.created_at
            common_conditions.extend(
                (date_column >= local_start.astimezone(UTC), date_column < local_end.astimezone(UTC))
            )
        if service_id:
            common_conditions.append(Booking.service_id == service_id)
        if query:
            escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_query}%"
            code_query = query.upper().removeprefix("MED-")
            common_conditions.append(
                or_(
                    User.full_name.ilike(pattern, escape="\\"),
                    PatientProfile.full_name.ilike(pattern, escape="\\"),
                    cast(Booking.id, String).ilike(pattern, escape="\\"),
                    func.left(cast(Booking.id, String), 8).ilike(f"%{code_query}%"),
                )
            )

        base_conditions = [*common_conditions, *([Booking.status == status] if status else [])]
        base = select(Booking).join(User, Booking.user_id == User.id)
        status_query = select(Booking.status, func.count()).join(User, Booking.user_id == User.id)
        if query:
            base = base.outerjoin(PatientProfile, Booking.patient_profile_id == PatientProfile.id)
            status_query = status_query.outerjoin(PatientProfile, Booking.patient_profile_id == PatientProfile.id)
        base = base.where(*base_conditions)
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        status_rows = await self.session.execute(status_query.where(*common_conditions).group_by(Booking.status))
        grouped_counts = dict(status_rows.all())
        status_counts = {
            "all": sum(grouped_counts.values()),
            "pending_approval": grouped_counts.get("pending_approval", 0),
            "confirmed": grouped_counts.get("confirmed", 0),
            "rejected": grouped_counts.get("rejected", 0),
        }
        page = (
            self._with_context(base).order_by(Booking.updated_at.desc(), Booking.id.desc()).offset(offset).limit(limit)
        )
        values = list((await self.session.execute(page)).scalars().all())
        return values, total, status_counts

    async def get_for_staff(self, booking_id: UUID, *, for_update: bool = False) -> Booking | None:
        """Fetch one booking with all staff review context."""
        statement = self._with_context(select(Booking).where(Booking.id == booking_id))
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_staff_ai_triage(self, booking_ids: list[UUID]) -> dict[UUID, dict]:
        """Return unambiguous saved triage snapshots linked to these bookings."""
        if not booking_ids:
            return {}
        rows = (
            (
                await self.session.execute(
                    select(CoordinationCase).where(
                        (CoordinationCase.booking_id.in_(booking_ids))
                        | (
                            (CoordinationCase.source == "booking")
                            & (CoordinationCase.source_id.in_([str(value) for value in booking_ids]))
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        by_booking: dict[UUID, list[CoordinationCase]] = {booking_id: [] for booking_id in booking_ids}
        for case in rows:
            booking_id = case.booking_id if case.booking_id in by_booking else None
            if booking_id is None and case.source == "booking":
                try:
                    candidate = UUID(case.source_id)
                except ValueError:
                    continue
                if candidate in by_booking:
                    booking_id = candidate
            if booking_id is not None:
                by_booking[booking_id].append(case)
        result = {}
        for booking_id, cases in by_booking.items():
            canonical = [case for case in cases if case.booking_id == booking_id]
            matches = canonical if canonical else cases
            if len(matches) == 1 and matches[0].ai_snapshot:
                result[booking_id] = {**matches[0].ai_snapshot, "source": matches[0].source}
        return result

    @staticmethod
    def _with_context(statement):
        return statement.options(
            selectinload(Booking.user),
            selectinload(Booking.patient_profile),
            selectinload(Booking.schedule).selectinload(DoctorSchedule.doctor),
            selectinload(Booking.schedule).selectinload(DoctorSchedule.facility),
            selectinload(Booking.appointment_schedule),
            selectinload(Booking.doctor),
            selectinload(Booking.facility),
            selectinload(Booking.service),
            selectinload(Booking.specialty),
        )

    async def _one(self, statement):
        return (await self.session.execute(statement)).scalar_one_or_none()
