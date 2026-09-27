"""Business rules for the medical catalog and availability bounded context."""

import inspect
from datetime import date, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.catalog import (
    CatalogAuditEvent,
    Doctor,
    DoctorFacility,
    DoctorSchedule,
    DoctorService,
    DoctorSpecialty,
    Facility,
    Service,
    Specialty,
)
from src.repositories.catalog import CatalogRepository
from src.schemas.catalog import (
    BulkImportItemResult,
    BulkImportResponse,
    BulkScheduleImportRequest,
    DoctorCreate,
    DoctorFacilityAssignment,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    DoctorScheduleUpdate,
    DoctorServiceAssignment,
    DoctorSpecialtyAssignment,
    DoctorUpdate,
    FacilityCreate,
    FacilityUpdate,
    ScheduleImportRecord,
    ServiceCreate,
    ServiceUpdate,
    SpecialtyCreate,
    SpecialtyUpdate,
)

logger = get_logger(__name__)


class CatalogService:
    """Coordinate validation, transactions, persistence, and audit events."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with one request-scoped session."""
        self.session = session
        self.catalog = CatalogRepository(session)

    async def list_specialties(self, *, public_only: bool, offset: int, limit: int) -> list[Specialty]:
        """List specialties."""
        return await self.catalog.list_specialties(public_only=public_only, offset=offset, limit=limit)

    async def get_specialty(self, resource_id: UUID, *, public_only: bool) -> Specialty:
        """Get a specialty or raise a safe not-found error."""
        value = await self.catalog.get_specialty(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Specialty not found")
        return value

    async def create_specialty(self, request: SpecialtyCreate, actor_id: UUID) -> Specialty:
        """Create a specialty and audit the operation."""
        async with self.session.begin():
            await self._ensure_code_available(Specialty, request.code)
            value = Specialty(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "created", {"code": value.code})
        return value

    async def update_specialty(self, resource_id: UUID, request: SpecialtyUpdate, actor_id: UUID) -> Specialty:
        """Update a specialty without hard deletion."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_specialty(resource_id), "Specialty not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "updated", request.model_dump(exclude_unset=True))
        return value

    async def list_facilities(self, *, public_only: bool, offset: int, limit: int) -> list[Facility]:
        """List facilities."""
        return await self.catalog.list_facilities(public_only=public_only, offset=offset, limit=limit)

    async def get_facility(self, resource_id: UUID, *, public_only: bool) -> Facility:
        """Get a facility or raise a safe not-found error."""
        value = await self.catalog.get_facility(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Facility not found")
        return value

    async def create_facility(self, request: FacilityCreate, actor_id: UUID) -> Facility:
        """Create a facility."""
        async with self.session.begin():
            await self._ensure_code_available(Facility, request.code)
            value = Facility(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "facility", value.id, "created", {"code": value.code})
        return value

    async def update_facility(self, resource_id: UUID, request: FacilityUpdate, actor_id: UUID) -> Facility:
        """Update a facility."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_facility(resource_id), "Facility not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "facility", value.id, "updated", request.model_dump(exclude_unset=True))
        return value

    async def list_services(self, *, public_only: bool, offset: int, limit: int) -> list[Service]:
        """List services."""
        return await self.catalog.list_services(public_only=public_only, offset=offset, limit=limit)

    async def get_service(self, resource_id: UUID, *, public_only: bool) -> Service:
        """Get a service or raise a safe not-found error."""
        value = await self.catalog.get_service(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Service not found")
        return value

    async def create_service(self, request: ServiceCreate, actor_id: UUID) -> Service:
        """Create a medical service."""
        async with self.session.begin():
            await self._ensure_code_available(Service, request.code)
            value = Service(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "service", value.id, "created", {"code": value.code})
        return value

    async def update_service(self, resource_id: UUID, request: ServiceUpdate, actor_id: UUID) -> Service:
        """Update a medical service."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_service(resource_id), "Service not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "service", value.id, "updated", request.model_dump(exclude_unset=True))
        return value

    async def list_doctors(
        self,
        *,
        public_only: bool,
        specialty_id: UUID | None,
        facility_id: UUID | None,
        name: str | None,
        booking_enabled: bool | None,
        offset: int,
        limit: int,
    ) -> list[Doctor]:
        """List doctors with public/staff visibility rules."""
        return await self.catalog.list_doctors(
            public_only=public_only,
            specialty_id=specialty_id,
            facility_id=facility_id,
            name=name,
            booking_enabled=booking_enabled,
            offset=offset,
            limit=limit,
        )

    async def get_doctor(self, resource_id: UUID, *, public_only: bool) -> Doctor:
        """Get a doctor or raise a safe not-found error."""
        value = await self.catalog.get_doctor(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Doctor not found")
        return value

    async def create_doctor(self, request: DoctorCreate, actor_id: UUID) -> Doctor:
        """Create a doctor and optional catalog assignments."""
        async with self.session.begin():
            await self._ensure_code_available(Doctor, request.code)
            if request.license_number:
                await self._ensure_license_available(request.license_number)
            await self._validate_assignments(request.specialty_ids, request.facility_ids, request.service_ids)
            values = request.model_dump(exclude={"specialty_ids", "facility_ids", "service_ids"})
            value = Doctor(**values)
            self.session.add(value)
            await self.session.flush()
            await self.catalog.replace_doctor_assignments(
                value,
                specialty_ids=request.specialty_ids,
                facility_ids=request.facility_ids,
                service_ids=request.service_ids,
            )
            await self.session.flush()
            await self._audit(actor_id, "doctor", value.id, "created", {"code": value.code})
        return await self.get_doctor(value.id, public_only=False)

    async def update_doctor(self, resource_id: UUID, request: DoctorUpdate, actor_id: UUID) -> Doctor:
        """Update a doctor profile and optionally replace assignments."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_doctor(resource_id), "Doctor not found")
            updates = request.model_dump(exclude_unset=True)
            specialty_ids = updates.pop("specialty_ids", None)
            facility_ids = updates.pop("facility_ids", None)
            service_ids = updates.pop("service_ids", None)
            if "license_number" in updates and updates["license_number"]:
                await self._ensure_license_available(updates["license_number"], exclude_id=value.id)
            await self._validate_assignments(specialty_ids, facility_ids, service_ids)
            for field, item in updates.items():
                setattr(value, field, item)
            await self.catalog.replace_doctor_assignments(
                value,
                specialty_ids=specialty_ids,
                facility_ids=facility_ids,
                service_ids=service_ids,
            )
            await self.session.flush()
            await self._audit(actor_id, "doctor", value.id, "updated", request.model_dump(exclude_unset=True))
        return await self.get_doctor(value.id, public_only=False)

    async def toggle_doctor_booking(self, resource_id: UUID, enabled: bool, actor_id: UUID) -> Doctor:
        """Enable or disable new bookings without deleting catalog data."""
        return await self.update_doctor(resource_id, DoctorUpdate(booking_enabled=enabled), actor_id)

    async def assign_doctor_specialty(
        self, doctor_id: UUID, request: DoctorSpecialtyAssignment, actor_id: UUID
    ) -> Doctor:
        """Assign a specialty to a doctor."""
        async with self.session.begin():
            await self._required(self.catalog.get_doctor(doctor_id), "Doctor not found")
            specialty = await self._required(self.catalog.get_specialty(request.specialty_id), "Specialty not found")
            duplicate = await self.session.scalar(
                select(DoctorSpecialty).where(
                    DoctorSpecialty.doctor_id == doctor_id,
                    DoctorSpecialty.specialty_id == request.specialty_id,
                )
            )
            if duplicate:
                raise ConflictError("ASSIGNMENT_EXISTS", "Doctor specialty assignment already exists")
            self.session.add(
                DoctorSpecialty(doctor_id=doctor_id, specialty_id=specialty.id, is_primary=request.is_primary)
            )
            await self.session.flush()
            await self._audit(actor_id, "doctor", doctor_id, "specialty_assigned", {"specialty_id": specialty.id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def remove_doctor_specialty(self, doctor_id: UUID, specialty_id: UUID, actor_id: UUID) -> Doctor:
        """Remove a doctor-specialty assignment."""
        async with self.session.begin():
            await self._required(self.catalog.get_doctor(doctor_id), "Doctor not found")
            assignment = await self.session.scalar(
                select(DoctorSpecialty).where(
                    DoctorSpecialty.doctor_id == doctor_id,
                    DoctorSpecialty.specialty_id == specialty_id,
                )
            )
            if assignment is None:
                raise NotFoundError("Doctor specialty assignment not found")
            await self.session.delete(assignment)
            await self._audit(actor_id, "doctor", doctor_id, "specialty_removed", {"specialty_id": specialty_id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def assign_doctor_facility(
        self, doctor_id: UUID, request: DoctorFacilityAssignment, actor_id: UUID
    ) -> Doctor:
        """Assign a facility and operational location to a doctor."""
        async with self.session.begin():
            await self._required(self.catalog.get_doctor(doctor_id), "Doctor not found")
            facility = await self._required(self.catalog.get_facility(request.facility_id), "Facility not found")
            duplicate = await self.session.scalar(
                select(DoctorFacility).where(
                    DoctorFacility.doctor_id == doctor_id,
                    DoctorFacility.facility_id == request.facility_id,
                )
            )
            if duplicate:
                raise ConflictError("ASSIGNMENT_EXISTS", "Doctor facility assignment already exists")
            values = request.model_dump(exclude={"facility_id"})
            self.session.add(DoctorFacility(doctor_id=doctor_id, facility_id=facility.id, **values))
            await self.session.flush()
            await self._audit(actor_id, "doctor", doctor_id, "facility_assigned", {"facility_id": facility.id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def update_doctor_facility(
        self, doctor_id: UUID, assignment_id: UUID, request: DoctorFacilityAssignment, actor_id: UUID
    ) -> Doctor:
        """Update a doctor's facility assignment."""
        async with self.session.begin():
            assignment = await self.session.scalar(
                select(DoctorFacility).where(
                    DoctorFacility.id == assignment_id,
                    DoctorFacility.doctor_id == doctor_id,
                )
            )
            if assignment is None:
                raise NotFoundError("Doctor facility assignment not found")
            for field, item in request.model_dump(exclude={"facility_id"}, exclude_unset=True).items():
                setattr(assignment, field, item)
            await self.session.flush()
            await self._audit(actor_id, "doctor", doctor_id, "facility_updated", {"assignment_id": assignment_id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def assign_doctor_service(self, doctor_id: UUID, request: DoctorServiceAssignment, actor_id: UUID) -> Doctor:
        """Assign a service to a doctor."""
        async with self.session.begin():
            doctor = await self._required(self.catalog.get_doctor(doctor_id), "Doctor not found")
            service = await self._required(self.catalog.get_service(request.service_id), "Service not found")
            duplicate = await self.session.scalar(
                select(DoctorService).where(
                    DoctorService.doctor_id == doctor_id,
                    DoctorService.service_id == request.service_id,
                )
            )
            if duplicate:
                raise ConflictError("ASSIGNMENT_EXISTS", "Doctor service assignment already exists")
            self.session.add(DoctorService(doctor_id=doctor.id, service_id=service.id))
            await self.session.flush()
            await self._audit(actor_id, "doctor", doctor_id, "service_assigned", {"service_id": service.id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def remove_doctor_service(self, doctor_id: UUID, service_id: UUID, actor_id: UUID) -> Doctor:
        """Remove a doctor-service assignment."""
        async with self.session.begin():
            await self._required(self.catalog.get_doctor(doctor_id), "Doctor not found")
            assignment = await self.session.scalar(
                select(DoctorService).where(
                    DoctorService.doctor_id == doctor_id,
                    DoctorService.service_id == service_id,
                )
            )
            if assignment is None:
                raise NotFoundError("Doctor service assignment not found")
            await self.session.delete(assignment)
            await self._audit(actor_id, "doctor", doctor_id, "service_removed", {"service_id": service_id})
        return await self.get_doctor(doctor_id, public_only=False)

    async def create_schedule(self, request: DoctorScheduleCreate, actor_id: UUID) -> DoctorSchedule:
        """Create a schedule after validating its doctor and facility."""
        async with self.session.begin():
            await self._validate_schedule_owners(request.doctor_id, request.facility_id)
            if request.source_system and request.external_schedule_id:
                existing = await self.catalog.get_schedule_by_external_identity(
                    request.source_system, request.external_schedule_id
                )
                if existing:
                    raise ConflictError("SCHEDULE_EXISTS", "Schedule already exists")
            value = DoctorSchedule(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "doctor_schedule", value.id, "created", {"version": value.version})
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found")

    async def update_schedule(self, schedule_id: UUID, request: DoctorScheduleUpdate, actor_id: UUID) -> DoctorSchedule:
        """Update a schedule only when its optimistic-lock version matches."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_schedule(schedule_id), "Schedule not found")
            if value.version != request.expected_version:
                raise ConflictError("VERSION_MISMATCH", "Schedule version is stale")
            updates = request.model_dump(exclude={"expected_version"}, exclude_unset=True)
            starts_at = updates.get("starts_at", value.starts_at)
            ends_at = updates.get("ends_at", value.ends_at)
            if ends_at <= starts_at:
                raise ConflictError("INVALID_SCHEDULE", "Schedule end must be after start")
            for field, item in updates.items():
                setattr(value, field, item)
            value.version += 1
            await self.session.flush()
            await self._audit(actor_id, "doctor_schedule", value.id, "updated", {"version": value.version})
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
    ) -> list[DoctorSchedule]:
        """List schedules for public availability or staff operations."""
        return await self.catalog.list_schedules(
            doctor_id=doctor_id,
            facility_id=facility_id,
            starts_from=starts_from,
            starts_to=starts_to,
            public_only=public_only,
            offset=offset,
            limit=limit,
        )

    async def get_schedule(self, schedule_id: UUID, *, public_only: bool) -> DoctorSchedule:
        """Get one schedule, enforcing public availability rules when requested."""
        value = await self.catalog.get_schedule(schedule_id)
        if value is None or (public_only and not self._schedule_is_public(value)):
            raise NotFoundError("Schedule not found")
        return value

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

    async def schedule_history(self, schedule_id: UUID, *, limit: int = 100) -> list[CatalogAuditEvent]:
        """Return durable audit history for a schedule."""
        await self.get_schedule(schedule_id, public_only=False)
        return await self.catalog.list_audit_events(schedule_id, limit=limit)

    async def _upsert_schedule(self, record: ScheduleImportRecord, actor_id: UUID) -> tuple[DoctorSchedule, bool]:
        """Create or update one imported schedule within the caller transaction."""
        await self._validate_schedule_owners(record.doctor_id, record.facility_id)
        value = await self.catalog.get_schedule_by_external_identity(
            record.source_system, record.external_schedule_id, for_update=True
        )
        if value is None:
            value = DoctorSchedule(**record.model_dump(exclude={"expected_version"}))
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "doctor_schedule", value.id, "imported", {"version": value.version})
            return await self._required(self.catalog.get_schedule(value.id), "Schedule not found"), True
        if record.expected_version is not None and value.version != record.expected_version:
            raise ConflictError("VERSION_MISMATCH", "Schedule version is stale")
        for field in ("doctor_id", "facility_id", "starts_at", "ends_at", "capacity", "status"):
            setattr(value, field, getattr(record, field))
        value.version += 1
        await self.session.flush()
        await self._audit(actor_id, "doctor_schedule", value.id, "imported", {"version": value.version})
        return await self._required(self.catalog.get_schedule(value.id), "Schedule not found"), False

    async def _validate_schedule_owners(self, doctor_id: UUID, facility_id: UUID) -> None:
        """Ensure schedule owners exist and are active."""
        doctor = await self.catalog.get_doctor(doctor_id)
        facility = await self.catalog.get_facility(facility_id)
        if doctor is None or doctor.status != "active":
            raise ConflictError("DOCTOR_INACTIVE", "Doctor is not active")
        if facility is None or facility.status != "active":
            raise ConflictError("FACILITY_INACTIVE", "Facility is not active")

    async def _validate_assignments(
        self,
        specialty_ids: list[UUID] | None,
        facility_ids: list[UUID] | None,
        service_ids: list[UUID] | None,
    ) -> None:
        """Ensure every supplied doctor assignment points to an active resource."""
        for resource_id in specialty_ids or []:
            value = await self.catalog.get_specialty(resource_id)
            if value is None or value.status != "active":
                raise NotFoundError("Specialty assignment not found")
        for resource_id in facility_ids or []:
            value = await self.catalog.get_facility(resource_id)
            if value is None or value.status != "active":
                raise NotFoundError("Facility assignment not found")
        for resource_id in service_ids or []:
            value = await self.catalog.get_service(resource_id)
            if value is None or value.status != "active":
                raise NotFoundError("Service assignment not found")

    async def _ensure_code_available(self, model: type, code: str) -> None:
        """Reject duplicate natural identifiers before writing."""
        existing = (await self.session.execute(select(model).where(model.code == code))).scalar_one_or_none()
        if existing is not None:
            raise ConflictError("CODE_EXISTS", "Catalog code already exists")

    async def _ensure_license_available(self, license_number: str, *, exclude_id: UUID | None = None) -> None:
        """Reject duplicate doctor license numbers."""
        statement = select(Doctor).where(Doctor.license_number == license_number)
        if exclude_id:
            statement = statement.where(Doctor.id != exclude_id)
        if (await self.session.execute(statement)).scalar_one_or_none() is not None:
            raise ConflictError("LICENSE_EXISTS", "Doctor license number already exists")

    async def _audit(self, actor_id: UUID, entity_type: str, entity_id: UUID, action: str, payload: dict) -> None:
        """Write a durable audit record and a safe application log."""
        await self.catalog.add_audit_event(
            CatalogAuditEvent(
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload=_json_safe(payload),
            )
        )
        logger.info("CatalogService.audit", extra={"entity_type": entity_type, "action": action})

    @staticmethod
    async def _required(value, message: str):
        """Return a value or raise a not-found error."""
        if inspect.isawaitable(value):
            value = await value
        if value is None:
            raise NotFoundError(message)
        return value

    @staticmethod
    def _schedule_is_public(value: DoctorSchedule) -> bool:
        """Check the non-query public availability rules for one slot."""
        return (
            value.status == "available"
            and value.capacity > 0
            and value.doctor.status == "active"
            and value.doctor.review_status == "approved"
            and value.doctor.booking_enabled
            and value.facility.status == "active"
        )


def _json_safe(values: dict) -> dict:
    """Convert UUID/date values to JSON-safe audit payloads."""
    return {
        key: value.isoformat() if isinstance(value, (UUID, date, datetime)) else value for key, value in values.items()
    }


def _import_record_label(payload: object, index: int) -> str:
    """Return a stable result label even when the record has invalid shape."""
    if isinstance(payload, dict):
        external_id = payload.get("external_schedule_id")
        if external_id not in (None, ""):
            return str(external_id)
    return f"record-{index}"
