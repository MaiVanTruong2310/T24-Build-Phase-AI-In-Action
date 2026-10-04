"""Doctor catalog and assignment business operations."""

import logging
from uuid import UUID

from sqlalchemy import select

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
from src.models.catalog import Doctor, DoctorFacility, DoctorService, DoctorSpecialty
from src.schemas.catalog import (
    DoctorCreate,
    DoctorFacilityAssignment,
    DoctorServiceAssignment,
    DoctorSpecialtyAssignment,
    DoctorUpdate,
)

logger = get_logger(__name__)


class DoctorServiceMixin:
    """Doctor operations composed into the catalog service."""

    async def list_doctors(
        self,
        *,
        public_only: bool,
        specialty_id: UUID | None,
        facility_id: UUID | None,
        service_id: UUID | None,
        name: str | None,
        booking_enabled: bool | None,
        offset: int,
        limit: int,
    ) -> list[Doctor]:
        """List doctors with public/staff visibility rules."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.list.start",
            description="Starting doctor catalog query",
            public_only=public_only,
            specialty_id=str(specialty_id) if specialty_id else None,
            facility_id=str(facility_id) if facility_id else None,
            service_id=str(service_id) if service_id else None,
            name_filter=name,
            booking_enabled=booking_enabled,
            offset=offset,
            limit=limit,
        )
        values = await self.catalog.list_doctors(
            public_only=public_only,
            specialty_id=specialty_id,
            facility_id=facility_id,
            service_id=service_id,
            name=name,
            booking_enabled=booking_enabled,
            offset=offset,
            limit=limit,
        )
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.list.done",
            description="Doctors were listed using catalog filters and visibility rules",
            count=len(values),
            public_only=public_only,
        )
        return values

    async def get_doctor(self, resource_id: UUID, *, public_only: bool) -> Doctor:
        """Get a doctor or raise a safe not-found error."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.get.start",
            description="Starting doctor profile lookup",
            resource_id=str(resource_id),
            public_only=public_only,
        )
        value = await self.catalog.get_doctor(resource_id, public_only=public_only)
        if value is None:
            log_event(
                logger,
                logging.WARNING,
                "catalog.doctor.get.not_found",
                description="Doctor lookup returned no visible doctor",
                resource_id=str(resource_id),
            )
            raise NotFoundError("Doctor not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.get.done",
            description="Doctor profile was loaded",
            resource_id=str(resource_id),
        )
        return value

    async def create_doctor(self, request: DoctorCreate, actor_id: UUID) -> Doctor:
        """Create a doctor and optional catalog assignments."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.create.start",
            description="Starting doctor profile and assignment creation",
            actor_id=str(actor_id),
            doctor_code=request.code,
        )
        async with self.session.begin():
            await self._ensure_code_available(Doctor, request.code)
            if request.license_number:
                await self._ensure_license_available(request.license_number)
            await self._validate_assignments(request.specialty_ids, request.facilities, request.service_ids)
            values = request.model_dump(exclude={"specialty_ids", "facilities", "facility_ids", "service_ids"})
            value = Doctor(specialties=[], facilities=[], services=[], **values)
            self.session.add(value)
            await self.session.flush()
            await self.catalog.replace_doctor_assignments(
                value,
                specialty_ids=request.specialty_ids,
                facilities=request.facilities,
                service_ids=request.service_ids,
            )
            await self.session.flush()
            await self._audit(actor_id, "doctor", value.id, "created", {"code": value.code})
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.create.done",
            description="Doctor profile and catalog assignments were created",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(value.id, public_only=False)

    async def update_doctor(self, resource_id: UUID, request: DoctorUpdate, actor_id: UUID) -> Doctor:
        """Update a doctor profile and optionally replace assignments."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.update.start",
            description="Starting doctor profile and assignment update",
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            changed_fields=list(request.model_dump(exclude_unset=True).keys()),
        )
        async with self.session.begin():
            value = await self._required(self.catalog.get_doctor(resource_id), "Doctor not found")
            updates = request.model_dump(exclude_unset=True)
            specialty_ids = updates.pop("specialty_ids", None)
            facilities = updates.pop("facilities", None)
            updates.pop("facility_ids", None)
            service_ids = updates.pop("service_ids", None)
            if "license_number" in updates and updates["license_number"]:
                await self._ensure_license_available(updates["license_number"], exclude_id=value.id)
            await self._validate_assignments(specialty_ids, facilities, service_ids)
            for field, item in updates.items():
                setattr(value, field, item)
            await self.catalog.replace_doctor_assignments(
                value,
                specialty_ids=specialty_ids,
                facilities=facilities,
                service_ids=service_ids,
            )
            await self.session.flush()
            await self._audit(actor_id, "doctor", value.id, "updated", request.model_dump(exclude_unset=True))
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.update.done",
            description="Doctor profile and catalog assignments were updated",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(value.id, public_only=False)

    async def toggle_doctor_booking(self, resource_id: UUID, enabled: bool, actor_id: UUID) -> Doctor:
        """Enable or disable new bookings without deleting catalog data."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.booking_toggle.start",
            description="Starting doctor booking availability change",
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            enabled=enabled,
        )
        return await self.update_doctor(resource_id, DoctorUpdate(booking_enabled=enabled), actor_id)

    async def assign_doctor_specialty(
        self, doctor_id: UUID, request: DoctorSpecialtyAssignment, actor_id: UUID
    ) -> Doctor:
        """Assign a specialty to a doctor."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.specialty_assign.start",
            description="Starting doctor specialty assignment",
            doctor_id=str(doctor_id),
            specialty_id=str(request.specialty_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.specialty_assigned",
            description="A specialty was assigned to the doctor",
            doctor_id=str(doctor_id),
            specialty_id=str(request.specialty_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)

    async def remove_doctor_specialty(self, doctor_id: UUID, specialty_id: UUID, actor_id: UUID) -> Doctor:
        """Remove a doctor-specialty assignment."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.specialty_remove.start",
            description="Starting doctor specialty assignment removal",
            doctor_id=str(doctor_id),
            specialty_id=str(specialty_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.specialty_removed",
            description="A specialty assignment was removed from the doctor",
            doctor_id=str(doctor_id),
            specialty_id=str(specialty_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)

    async def assign_doctor_facility(
        self, doctor_id: UUID, request: DoctorFacilityAssignment, actor_id: UUID
    ) -> Doctor:
        """Assign a facility and operational location to a doctor."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.facility_assign.start",
            description="Starting doctor facility assignment",
            doctor_id=str(doctor_id),
            facility_id=str(request.facility_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.facility_assigned",
            description="A facility was assigned to the doctor",
            doctor_id=str(doctor_id),
            facility_id=str(request.facility_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)

    async def update_doctor_facility(
        self, doctor_id: UUID, assignment_id: UUID, request: DoctorFacilityAssignment, actor_id: UUID
    ) -> Doctor:
        """Update a doctor's facility assignment."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.facility_update.start",
            description="Starting doctor facility assignment update",
            doctor_id=str(doctor_id),
            assignment_id=str(assignment_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.facility_updated",
            description="A doctor facility assignment was updated",
            doctor_id=str(doctor_id),
            assignment_id=str(assignment_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)

    async def assign_doctor_service(self, doctor_id: UUID, request: DoctorServiceAssignment, actor_id: UUID) -> Doctor:
        """Assign a service to a doctor."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.service_assign.start",
            description="Starting doctor medical service assignment",
            doctor_id=str(doctor_id),
            service_id=str(request.service_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.service_assigned",
            description="A medical service was assigned to the doctor",
            doctor_id=str(doctor_id),
            service_id=str(request.service_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)

    async def remove_doctor_service(self, doctor_id: UUID, service_id: UUID, actor_id: UUID) -> Doctor:
        """Remove a doctor-service assignment."""
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.service_remove.start",
            description="Starting doctor medical service assignment removal",
            doctor_id=str(doctor_id),
            service_id=str(service_id),
            actor_id=str(actor_id),
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.doctor.service_removed",
            description="A medical service assignment was removed from the doctor",
            doctor_id=str(doctor_id),
            service_id=str(service_id),
            actor_id=str(actor_id),
        )
        return await self.get_doctor(doctor_id, public_only=False)
