"""Doctor schedule business operations."""

import logging
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.core.errors import raise_integrity_conflict, savepoint
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
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

logger = get_logger(__name__)


class ScheduleServiceMixin:
    """Schedule operations composed into the catalog service."""

    async def create_schedule(self, request: DoctorScheduleCreate, actor_id: UUID) -> DoctorSchedule:
        """Create a schedule after validating its doctor and facility."""
        try:
            async with self.session.begin():
                await self._validate_schedule_owners(request.doctor_id, request.facility_id, lock_doctor=True)
                await self._validate_schedule_service(
                    request.doctor_id,
                    request.service_id,
                    required=request.status == "available" or request.busy_reason == "consultation",
                )
                if request.status == "available" and request.service_id is not None:
                    service = await self.catalog.get_service(request.service_id)
                    if service and service.booking_mode == "doctor_visit" and request.capacity != 1:
                        raise ConflictError("INVALID_CAPACITY", "Doctor visit schedules must have capacity one")
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
            log_event(
                logger,
                logging.ERROR,
                "catalog.schedule.create.error",
                description="Schedule creation failed because the database rejected the schedule constraints",
                doctor_id=str(request.doctor_id),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            self._raise_schedule_integrity_error(exc)
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found")

    async def update_schedule(self, schedule_id: UUID, request: DoctorScheduleUpdate, actor_id: UUID) -> DoctorSchedule:
        """Replace mutable schedule fields with optimistic locking."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.update.start",
            description="Starting doctor schedule update with optimistic locking",
            schedule_id=str(schedule_id),
            actor_id=str(actor_id),
            expected_version=request.expected_version,
            changed_fields=list(request.model_dump(exclude={"expected_version"}, exclude_unset=True).keys()),
        )
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
                await self._validate_schedule_service(
                    value.doctor_id,
                    updates["service_id"],
                    required=updates["status"] == "available" or updates["busy_reason"] == "consultation",
                )
                if updates["status"] == "available" and updates["service_id"] is not None:
                    service = await self.catalog.get_service(updates["service_id"])
                    if service and service.booking_mode == "doctor_visit" and updates["capacity"] != 1:
                        raise ConflictError("INVALID_CAPACITY", "Doctor visit schedules must have capacity one")
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
            log_event(
                logger,
                logging.ERROR,
                "catalog.schedule.update.error",
                description="Schedule update failed because the database rejected the schedule constraints",
                schedule_id=str(schedule_id),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            self._raise_schedule_integrity_error(exc)
        value = await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.update.done",
            description="Doctor schedule fields were updated with optimistic locking",
            schedule_id=str(schedule_id),
            actor_id=str(actor_id),
        )
        return value

    async def list_schedules(
        self,
        *,
        doctor_id: UUID | None,
        facility_id: UUID | None,
        service_id: UUID | None,
        starts_from: datetime | None,
        starts_to: datetime | None,
        public_only: bool,
        offset: int,
        limit: int,
        schedule_status: str | None = None,
        source_system: str | None = None,
    ) -> list[DoctorSchedule]:
        """List schedules for public availability or staff operations."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.list.start",
            description="Starting doctor schedule availability query",
            doctor_id=str(doctor_id) if doctor_id else None,
            facility_id=str(facility_id) if facility_id else None,
            service_id=str(service_id) if service_id else None,
            public_only=public_only,
            schedule_status=schedule_status,
            source_system=source_system,
            offset=offset,
            limit=limit,
        )
        values = await self.catalog.list_schedules(
            doctor_id=doctor_id,
            facility_id=facility_id,
            service_id=service_id,
            starts_from=starts_from,
            starts_to=starts_to,
            schedule_status=schedule_status,
            source_system=source_system,
            public_only=public_only,
            offset=offset,
            limit=limit,
        )
        counts = await self.catalog.count_active_bookings_for_schedules([value.id for value in values])
        for value in values:
            value_type = getattr(value, "type", "consultation") or "consultation"
            value.remaining_capacity = (
                None if value_type != "consultation" else max(value.capacity - counts.get(value.id, 0), 0)
            )
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.list.done",
            description="Doctor schedules were listed with calculated remaining capacity",
            count=len(values),
            public_only=public_only,
        )
        return values

    async def get_schedule(self, schedule_id: UUID, *, public_only: bool) -> DoctorSchedule:
        """Get a schedule, enforcing public availability rules when requested."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.get.start",
            description="Starting doctor schedule lookup",
            schedule_id=str(schedule_id),
            public_only=public_only,
        )
        value = await self.catalog.get_schedule(schedule_id)
        if value is None or (public_only and not self._schedule_is_public(value)):
            log_event(
                logger,
                logging.WARNING,
                "catalog.schedule.get.not_found",
                description="Schedule lookup returned no public or existing schedule",
                schedule_id=str(schedule_id),
            )
            raise NotFoundError("Schedule not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.get.done",
            description="Doctor schedule was loaded with remaining capacity",
            schedule_id=str(schedule_id),
        )
        return value

    async def cancel_schedule(
        self,
        schedule_id: UUID,
        request: ScheduleCancellationRequest,
        actor_id: UUID,
    ) -> DoctorSchedule:
        """Soft-cancel a schedule while retaining its database row."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.cancel.start",
            description="Starting doctor schedule cancellation",
            schedule_id=str(schedule_id),
            actor_id=str(actor_id),
        )
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
        value = await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.cancel.done",
            description="Doctor schedule was soft-cancelled and retained for audit history",
            schedule_id=str(schedule_id),
            actor_id=str(actor_id),
        )
        return value

    async def bulk_import_schedules(
        self,
        request: BulkScheduleImportRequest,
        actor_id: UUID,
    ) -> BulkImportResponse:
        """Upsert a JSON schedule batch and return per-record results."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.bulk_import.start",
            description="Starting schedule import batch validation and upsert",
            actor_id=str(actor_id),
            record_count=len(request.records),
        )
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
                    async with savepoint(self.session):
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
                except IntegrityError as exc:
                    failed += 1
                    log_event(
                        logger,
                        logging.ERROR,
                        "catalog.schedule.bulk_import.persistence_conflict",
                        description="One imported schedule conflicted with a database constraint",
                        external_schedule_id=external_schedule_id,
                        error_type=type(exc.orig).__name__,
                        exc_info=True,
                    )
                    items.append(
                        BulkImportItemResult(
                            external_schedule_id=external_schedule_id,
                            error="Schedule conflicts with an existing record or schedule constraint",
                        )
                    )
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.bulk_import.done",
            description="Schedule import batch was validated and upserted",
            created_count=created,
            updated_count=updated,
            failed_count=failed,
        )
        return BulkImportResponse(created=created, updated=updated, failed=failed, items=items)

    async def schedule_history(self, schedule_id: UUID, *, limit: int = 100):
        """Return durable audit history for a schedule for internal callers."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.history.start",
            description="Starting schedule audit history query",
            schedule_id=str(schedule_id),
            limit=limit,
        )
        await self.get_schedule(schedule_id, public_only=False)
        return await self.catalog.list_audit_events(schedule_id, limit=limit)

    async def schedule_activity(self, *, doctor_id: UUID, starts_from: datetime, starts_to: datetime, limit: int = 100):
        """Return audit activity for a doctor's schedules in a time window."""
        log_event(
            logger,
            logging.INFO,
            "catalog.schedule.activity.start",
            description="Starting doctor schedule activity query",
            doctor_id=str(doctor_id),
            starts_from=starts_from.isoformat(),
            starts_to=starts_to.isoformat(),
            limit=limit,
        )
        return await self.catalog.list_schedule_audit_events(
            doctor_id=doctor_id,
            starts_from=starts_from,
            starts_to=starts_to,
            limit=limit,
        )

    async def _upsert_schedule(self, record: ScheduleImportRecord, actor_id: UUID) -> tuple[DoctorSchedule, bool]:
        """Create or update one imported schedule within the caller transaction."""
        await self._validate_schedule_owners(record.doctor_id, record.facility_id, lock_doctor=True)
        await self._validate_schedule_service(
            record.doctor_id,
            record.service_id,
            required=record.service_id is not None,
        )
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
        for field in (
            "doctor_id",
            "facility_id",
            "service_id",
            "starts_at",
            "ends_at",
            "capacity",
            "status",
            "busy_reason",
            "note",
        ):
            if field in {"service_id", "busy_reason", "note"} and field not in record.model_fields_set:
                continue
            setattr(value, field, getattr(record, field))
        value.updated_by = actor_id
        value.version += 1
        await self.session.flush()
        await self._audit(actor_id, "doctor_schedule", value.id, "imported", {"version": value.version})
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found"), False

    async def _validate_schedule_owners(self, doctor_id: UUID, facility_id: UUID, *, lock_doctor: bool = False) -> None:
        """Ensure schedule owners exist and are active."""
        doctor = await self.catalog.lock_doctor(doctor_id) if lock_doctor else await self.catalog.get_doctor(doctor_id)
        facility = await self.catalog.get_facility(facility_id)
        if doctor is None or doctor.status != "active":
            raise ConflictError("DOCTOR_INACTIVE", "Doctor is not active")
        if facility is None or facility.status != "active":
            raise ConflictError("FACILITY_INACTIVE", "Facility is not active")

    async def _validate_schedule_service(
        self, doctor_id: UUID, service_id: UUID | None, *, required: bool
    ) -> None:
        """Ensure a schedule service is active and assigned to the selected doctor."""
        if service_id is None:
            if required:
                raise ConflictError("SERVICE_REQUIRED", "An active service is required for this schedule")
            return
        service = await self.catalog.get_service(service_id)
        if service is None or service.status != "active":
            raise NotFoundError("Service not found")
        if not await self.catalog.has_doctor_service(doctor_id, service_id):
            raise ConflictError("SERVICE_NOT_AVAILABLE", "Service is not assigned to this doctor")

    @staticmethod
    def _raise_schedule_integrity_error(exc: IntegrityError) -> None:
        """Convert the database overlap guard into the public conflict error."""
        if "excl_doctor_schedule_time" in str(exc.orig):
            raise ConflictError(
                "SCHEDULE_TIME_CONFLICT",
                "Doctor already has a schedule overlapping this time range",
            ) from exc
        raise_integrity_conflict(
            exc,
            logger=logger,
            event="catalog.schedule.persistence_conflict",
            code="SCHEDULE_PERSISTENCE_CONFLICT",
            message="Schedule could not be saved",
            log_description="Schedule persistence conflicted with another schedule or schedule constraint",
        )


def _import_record_label(payload: object, index: int) -> str:
    """Return a stable result label even when the record has invalid shape."""
    if isinstance(payload, dict):
        external_id = payload.get("external_schedule_id")
        if external_id not in (None, ""):
            return str(external_id)
    return f"record-{index}"
