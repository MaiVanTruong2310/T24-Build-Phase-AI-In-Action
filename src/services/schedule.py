"""Doctor schedule business operations."""

from datetime import datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, NotFoundError
from src.models.catalog import DoctorSchedule
from src.schemas.catalog import (
    BulkImportItemResult,
    BulkImportResponse,
    BulkScheduleImportRequest,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
    ScheduleCancellationRequest,
    ScheduleImportRecord,
)


class ScheduleServiceMixin:
    """Schedule operations composed into the catalog service."""

    async def create_schedule(self, request: DoctorScheduleCreate, actor_id: UUID) -> DoctorSchedule:
        """Create a schedule after validating its doctor and facility."""
        try:
            async with self.session.begin():
                await self._validate_schedule_owners(request.doctor_id, request.facility_id, lock_doctor=True)
                if request.source_system and request.external_schedule_id:
                    existing = await self.catalog.get_schedule_by_external_identity(
                        request.source_system, request.external_schedule_id
                    )
                    if existing:
                        raise ConflictError("SCHEDULE_EXISTS", "Schedule already exists")
                conflict = await self.catalog.find_schedule_conflict(
                    doctor_id=request.doctor_id,
                    starts_at=request.starts_at,
                    ends_at=request.ends_at,
                )
                if conflict:
                    raise ConflictError(
                        "SCHEDULE_TIME_CONFLICT",
                        "Doctor already has a schedule overlapping this time range",
                    )
                value = DoctorSchedule(
                    **request.model_dump(),
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                self.session.add(value)
                await self.session.flush()
                await self._audit(actor_id, "doctor_schedule", value.id, "created", {"version": value.version})
        except IntegrityError as exc:
            self._raise_schedule_integrity_error(exc)
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found")

    async def update_schedule(self, schedule_id: UUID, request: DoctorScheduleUpdate, actor_id: UUID) -> DoctorSchedule:
        """Replace mutable schedule fields with optimistic locking."""
        try:
            async with self.session.begin():
                current = await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")
                await self._validate_schedule_owners(current.doctor_id, current.facility_id, lock_doctor=True)
                value = await self._required(
                    self.catalog.get_schedule(schedule_id, for_update=True), "Schedule not found"
                )
                if value.version != request.expected_version:
                    raise ConflictError("VERSION_MISMATCH", "Schedule version is stale")
                if value.status == "cancelled":
                    raise ConflictError("SCHEDULE_ALREADY_CANCELLED", "Cancelled schedule cannot be updated")
                updates = request.model_dump(exclude={"expected_version"})
                if updates["ends_at"] <= updates["starts_at"]:
                    raise ConflictError("INVALID_SCHEDULE", "Schedule end must be after start")
                conflict = await self.catalog.find_schedule_conflict(
                    doctor_id=value.doctor_id,
                    starts_at=updates["starts_at"],
                    ends_at=updates["ends_at"],
                    exclude_schedule_id=value.id,
                )
                if conflict:
                    raise ConflictError(
                        "SCHEDULE_TIME_CONFLICT",
                        "Doctor already has a schedule overlapping this time range",
                    )
                for field, item in updates.items():
                    setattr(value, field, item)
                value.updated_by = actor_id
                value.version += 1
                await self.session.flush()
                await self._audit(actor_id, "doctor_schedule", value.id, "updated", {"version": value.version})
        except IntegrityError as exc:
            self._raise_schedule_integrity_error(exc)
        return await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")

    async def list_schedules(
        self,
        *,
        doctor_id: UUID | None,
        facility_id: UUID | None,
        starts_from: datetime | None,
        starts_to: datetime | None,
        public_only: bool,
        offset: int,
        limit: int,
        schedule_status: str | None = None,
        source_system: str | None = None,
    ) -> list[DoctorSchedule]:
        """List schedules for public availability or staff operations."""
        return await self.catalog.list_schedules(
            doctor_id=doctor_id,
            facility_id=facility_id,
            starts_from=starts_from,
            starts_to=starts_to,
            schedule_status=schedule_status,
            source_system=source_system,
            public_only=public_only,
            offset=offset,
            limit=limit,
        )

    async def get_schedule(self, schedule_id: UUID, *, public_only: bool) -> DoctorSchedule:
        """Get a schedule, enforcing public availability rules when requested."""
        value = await self.catalog.get_schedule(schedule_id)
        if value is None or (public_only and not self._schedule_is_public(value)):
            raise NotFoundError("Schedule not found")
        return value

    async def cancel_schedule(
        self,
        schedule_id: UUID,
        request: ScheduleCancellationRequest,
        actor_id: UUID,
    ) -> DoctorSchedule:
        """Soft-cancel a schedule while retaining its database row."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")
            if value.status == "cancelled":
                raise ConflictError("SCHEDULE_ALREADY_CANCELLED", "Schedule is already cancelled")
            value.status = "cancelled"
            value.cancellation_reason = request.reason
            value.updated_by = actor_id
            value.version += 1
            await self.session.flush()
            await self._audit(actor_id, "doctor_schedule", value.id, "cancelled", {"version": value.version})
        return await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")

    async def bulk_import_schedules(
        self,
        request: BulkScheduleImportRequest,
        actor_id: UUID,
    ) -> BulkImportResponse:
        """Upsert a JSON schedule batch and return per-record results."""
        created = updated = failed = 0
        items: list[BulkImportItemResult] = []
        async with self.session.begin():
            for index, payload in enumerate(request.records, start=1):
                external_schedule_id = _import_record_label(payload, index)
                try:
                    record = ScheduleImportRecord.model_validate(payload)
                except ValidationError:
                    failed += 1
                    items.append(
                        BulkImportItemResult(
                            external_schedule_id=external_schedule_id,
                            error="Invalid schedule record",
                        )
                    )
                    continue
                try:
                    value, was_created = await self._upsert_schedule(record, actor_id)
                    created += int(was_created)
                    updated += int(not was_created)
                    items.append(
                        BulkImportItemResult(
                            external_schedule_id=record.external_schedule_id,
                            schedule=DoctorScheduleResponse.model_validate(value),
                        )
                    )
                except (ConflictError, NotFoundError) as exc:
                    failed += 1
                    items.append(BulkImportItemResult(external_schedule_id=external_schedule_id, error=exc.message))
        return BulkImportResponse(created=created, updated=updated, failed=failed, items=items)

    async def schedule_history(self, schedule_id: UUID, *, limit: int = 100):
        """Return durable audit history for a schedule for internal callers."""
        await self.get_schedule(schedule_id, public_only=False)
        return await self.catalog.list_audit_events(schedule_id, limit=limit)

    async def schedule_activity(self, *, doctor_id: UUID, starts_from: datetime, starts_to: datetime, limit: int = 100):
        """Return audit activity for a doctor's schedules in a time window."""
        return await self.catalog.list_schedule_audit_events(
            doctor_id=doctor_id,
            starts_from=starts_from,
            starts_to=starts_to,
            limit=limit,
        )

    async def _upsert_schedule(self, record: ScheduleImportRecord, actor_id: UUID) -> tuple[DoctorSchedule, bool]:
        """Create or update one imported schedule within the caller transaction."""
        await self._validate_schedule_owners(record.doctor_id, record.facility_id, lock_doctor=True)
        value = await self.catalog.get_schedule_by_external_identity(
            record.source_system, record.external_schedule_id, for_update=True
        )
        conflict = await self.catalog.find_schedule_conflict(
            doctor_id=record.doctor_id,
            starts_at=record.starts_at,
            ends_at=record.ends_at,
            exclude_schedule_id=value.id if value else None,
        )
        if conflict:
            raise ConflictError(
                "SCHEDULE_TIME_CONFLICT",
                "Doctor already has a schedule overlapping this time range",
            )
        if value is None:
            value = DoctorSchedule(
                **record.model_dump(exclude={"expected_version"}),
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "doctor_schedule", value.id, "imported", {"version": value.version})
            return await self._required(self.catalog.get_schedule(value.id), "Schedule not found"), True
        if record.expected_version is not None and value.version != record.expected_version:
            raise ConflictError("VERSION_MISMATCH", "Schedule version is stale")
        if value.status == "cancelled":
            raise ConflictError("SCHEDULE_ALREADY_CANCELLED", "Cancelled schedule cannot be imported")
        for field in ("doctor_id", "facility_id", "starts_at", "ends_at", "capacity", "status"):
            setattr(value, field, getattr(record, field))
        value.updated_by = actor_id
        value.version += 1
        await self.session.flush()
        await self._audit(actor_id, "doctor_schedule", value.id, "imported", {"version": value.version})
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found"), False

    async def _validate_schedule_owners(
        self, doctor_id: UUID, facility_id: UUID, *, lock_doctor: bool = False
    ) -> None:
        """Ensure schedule owners exist and are active."""
        doctor = (
            await self.catalog.lock_doctor(doctor_id)
            if lock_doctor
            else await self.catalog.get_doctor(doctor_id)
        )
        facility = await self.catalog.get_facility(facility_id)
        if doctor is None or doctor.status != "active":
            raise ConflictError("DOCTOR_INACTIVE", "Doctor is not active")
        if facility is None or facility.status != "active":
            raise ConflictError("FACILITY_INACTIVE", "Facility is not active")

    @staticmethod
    def _raise_schedule_integrity_error(exc: IntegrityError) -> None:
        """Convert the database overlap guard into the public conflict error."""
        if "excl_doctor_schedule_time" in str(exc.orig):
            raise ConflictError(
                "SCHEDULE_TIME_CONFLICT",
                "Doctor already has a schedule overlapping this time range",
            ) from exc
        raise exc


def _import_record_label(payload: object, index: int) -> str:
    """Return a stable result label even when the record has invalid shape."""
    if isinstance(payload, dict):
        external_id = payload.get("external_schedule_id")
        if external_id not in (None, ""):
            return str(external_id)
    return f"record-{index}"
