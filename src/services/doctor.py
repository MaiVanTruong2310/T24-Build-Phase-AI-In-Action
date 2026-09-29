"""Doctor catalog and assignment business operations."""

from uuid import UUID

from sqlalchemy import select

from src.core.exceptions import ConflictError, NotFoundError
from src.models.catalog import Doctor, DoctorFacility, DoctorService, DoctorSpecialty
from src.schemas.catalog import (
    DoctorCreate,
    DoctorFacilityAssignment,
    DoctorServiceAssignment,
    DoctorSpecialtyAssignment,
    DoctorUpdate,
)


class DoctorServiceMixin:
    """Doctor operations composed into the catalog service."""

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
        return await self.get_doctor(value.id, public_only=False)

    async def update_doctor(self, resource_id: UUID, request: DoctorUpdate, actor_id: UUID) -> Doctor:
        """Update a doctor profile and optionally replace assignments."""
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
