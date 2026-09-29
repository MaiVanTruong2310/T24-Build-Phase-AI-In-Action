"""Medical service persistence queries."""

from uuid import UUID

from sqlalchemy import exists, select

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
        if specialty_id or facility_id:
            eligible_doctor = (
                select(1)
                .select_from(DoctorService)
                .join(Doctor, Doctor.id == DoctorService.doctor_id)
                .where(
                    DoctorService.service_id == Service.id,
                    DoctorService.active.is_(True),
                    Doctor.status == "active",
                    Doctor.review_status == "approved",
                    Doctor.booking_enabled.is_(True),
                )
            )
            if specialty_id:
                eligible_doctor = eligible_doctor.where(
                    exists(
                        select(1).where(
                            DoctorSpecialty.doctor_id == Doctor.id,
                            DoctorSpecialty.specialty_id == specialty_id,
                        )
                    )
                )
            if facility_id:
                eligible_doctor = eligible_doctor.where(
                    exists(
                        select(1).where(
                            DoctorFacility.doctor_id == Doctor.id,
                            DoctorFacility.facility_id == facility_id,
                        )
                    )
                )
            statement = statement.where(eligible_doctor.exists())
        statement = statement.order_by(Service.name).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())
