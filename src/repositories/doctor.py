"""Doctor and assignment persistence queries."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.models.catalog import Doctor, DoctorFacility, DoctorService, DoctorSpecialty
from src.models.service import Service


class DoctorRepositoryMixin:
    """Doctor queries composed into the catalog repository."""

    async def get_doctor(self, resource_id: UUID, *, public_only: bool = False) -> Doctor | None:
        """Fetch a doctor and assignment collections."""
        statement = (
            select(Doctor)
            .options(
                selectinload(Doctor.specialties).selectinload(DoctorSpecialty.specialty),
                selectinload(Doctor.facilities).selectinload(DoctorFacility.facility),
                selectinload(Doctor.services).selectinload(DoctorService.service),
            )
            .where(Doctor.id == resource_id)
        )
        if public_only:
            statement = statement.where(
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        return (await self.session.execute(statement)).scalar_one_or_none()

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
        """List doctors with catalog filters and assignment collections."""
        statement = (
            select(Doctor)
            .options(
                selectinload(Doctor.specialties).selectinload(DoctorSpecialty.specialty),
                selectinload(Doctor.facilities).selectinload(DoctorFacility.facility),
                selectinload(Doctor.services).selectinload(DoctorService.service),
            )
            .order_by(Doctor.full_name)
            .offset(offset)
            .limit(limit)
        )
        if public_only:
            statement = statement.where(
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        if booking_enabled is not None:
            statement = statement.where(Doctor.booking_enabled.is_(booking_enabled))
        if name:
            statement = statement.where(Doctor.full_name.ilike(f"%{name.strip()}%"))
        if specialty_id:
            statement = statement.join(DoctorSpecialty).where(DoctorSpecialty.specialty_id == specialty_id)
        if facility_id:
            statement = statement.join(DoctorFacility).where(DoctorFacility.facility_id == facility_id)
        if service_id:
            statement = statement.join(DoctorService).join(Service, Service.id == DoctorService.service_id).where(
                DoctorService.service_id == service_id,
                DoctorService.active.is_(True),
                Service.status == "active",
            )
        if specialty_id or facility_id or service_id:
            statement = statement.distinct()
        return list((await self.session.execute(statement)).scalars().unique().all())

    async def replace_doctor_assignments(
        self,
        doctor: Doctor,
        *,
        specialty_ids: list[UUID] | None = None,
        facilities: list[Any] | None = None,
        service_ids: list[UUID] | None = None,
    ) -> None:
        """Replace supplied assignment collections while preserving omitted ones."""
        if specialty_ids is not None:
            await self.session.execute(delete(DoctorSpecialty).where(DoctorSpecialty.doctor_id == doctor.id))
            doctor.specialties = [
                DoctorSpecialty(doctor_id=doctor.id, specialty_id=value, is_primary=index == 0)
                for index, value in enumerate(dict.fromkeys(specialty_ids))
            ]
        if facilities is not None:
            await self.session.execute(delete(DoctorFacility).where(DoctorFacility.doctor_id == doctor.id))
            seen = set()
            unique_facilities = []
            for facility in facilities:
                if facility.facility_id not in seen:
                    seen.add(facility.facility_id)
                    unique_facilities.append(facility)
            doctor.facilities = [
                DoctorFacility(
                    doctor_id=doctor.id,
                    facility_id=facility.facility_id,
                    department=facility.department,
                    room=facility.room,
                    active_from=facility.active_from,
                    active_to=facility.active_to,
                )
                for facility in unique_facilities
            ]
        if service_ids is not None:
            await self.session.execute(delete(DoctorService).where(DoctorService.doctor_id == doctor.id))
            doctor.services = [
                DoctorService(doctor_id=doctor.id, service_id=value) for value in dict.fromkeys(service_ids)
            ]
