"""Doctor and assignment persistence queries."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select
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
        honor: str | None = None,
        academic_rank: str | None = None,
        degree: str | None = None,
        language: str | None = None,
        on_date: date | None = None,
        professional_role: str | None = None,
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
            )
        if booking_enabled is not None:
            statement = statement.where(Doctor.booking_enabled.is_(booking_enabled))
        if professional_role:
            statement = statement.where(Doctor.professional_role == professional_role)
        if name:
            statement = statement.where(Doctor.full_name.ilike(f"%{name.strip()}%"))
        if specialty_id:
            statement = statement.join(DoctorSpecialty).where(DoctorSpecialty.specialty_id == specialty_id)
        if facility_id:
            day = on_date or date.today()
            statement = statement.join(DoctorFacility).where(
                DoctorFacility.facility_id == facility_id,
                or_(DoctorFacility.active_from.is_(None), DoctorFacility.active_from <= day),
                or_(DoctorFacility.active_to.is_(None), DoctorFacility.active_to >= day),
            )
        if honor:
            statement = statement.where(Doctor.honors.contains([honor]))
        if academic_rank:
            statement = statement.where(Doctor.academic_ranks.contains([academic_rank]))
        if degree:
            statement = statement.where(Doctor.degrees.contains([degree]))
        if language:
            statement = statement.where(Doctor.languages.contains([language]))
        if service_id:
            statement = (
                statement.join(DoctorService)
                .join(Service, Service.id == DoctorService.service_id)
                .where(
                    DoctorService.service_id == service_id,
                    DoctorService.active.is_(True),
                    Service.status == "active",
                )
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
                    position=facility.position,
                    is_primary=facility.is_primary,
                )
                for facility in unique_facilities
            ]
        if service_ids is not None:
            await self.session.execute(delete(DoctorService).where(DoctorService.doctor_id == doctor.id))
            doctor.services = [
                DoctorService(doctor_id=doctor.id, service_id=value) for value in dict.fromkeys(service_ids)
            ]
