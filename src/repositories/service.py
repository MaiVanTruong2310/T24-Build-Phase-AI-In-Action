"""Medical service persistence queries."""

from datetime import date
from uuid import UUID

from sqlalchemy import select

from src.models.catalog import Service
from src.models.doctor import Doctor, DoctorFacility, DoctorService, DoctorSpecialty


class MedicalServiceRepositoryMixin:
    """Medical service queries composed into the catalog repository."""

    async def get_service(self, resource_id: UUID, *, public_only: bool = False) -> Service | None:
        """Fetch one medical service."""
        statement = select(Service).where(Service.id == resource_id)
        if public_only:
            statement = statement.where(Service.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_services(
        self,
        *,
        public_only: bool,
        offset: int,
        limit: int,
        name: str | None = None,
        category: str | None = None,
        specialty_id: UUID | None = None,
        facility_id: UUID | None = None,
    ) -> list[Service]:
        """List medical services with pagination."""
        statement = select(Service)
        if public_only:
            statement = statement.where(Service.status == "active")
        if name:
            statement = statement.where(Service.name.ilike(f"%{name}%"))
        if category:
            statement = statement.where(Service.category == category)
        if facility_id or specialty_id:
            eligible_doctors = (
                select(DoctorService.service_id)
                .join(Doctor, Doctor.id == DoctorService.doctor_id)
                .where(
                    DoctorService.service_id == Service.id,
                    DoctorService.active.is_(True),
                    Doctor.status == "active",
                    Doctor.review_status == "approved",
                    Doctor.booking_enabled.is_(True),
                    Doctor.professional_role == "Bác sĩ",
                )
            )
            if facility_id:
                eligible_doctors = eligible_doctors.join(DoctorFacility, DoctorFacility.doctor_id == Doctor.id).where(
                    DoctorFacility.facility_id == facility_id
                )
                today = date.today()
                eligible_doctors = eligible_doctors.where(
                    (DoctorFacility.active_from.is_(None)) | (DoctorFacility.active_from <= today),
                    (DoctorFacility.active_to.is_(None)) | (DoctorFacility.active_to >= today),
                )
            if specialty_id:
                eligible_doctors = eligible_doctors.join(DoctorSpecialty, DoctorSpecialty.doctor_id == Doctor.id).where(
                    DoctorSpecialty.specialty_id == specialty_id
                )
            statement = statement.where(eligible_doctors.exists())
        statement = (
            statement.order_by(Service.name if public_only else Service.updated_at.desc(), Service.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())
