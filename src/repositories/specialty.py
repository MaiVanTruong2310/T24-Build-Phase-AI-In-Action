"""Specialty persistence queries."""

from uuid import UUID

from sqlalchemy import select

from src.models.catalog import Specialty


class SpecialtyRepositoryMixin:
    """Specialty queries composed into the catalog repository."""

    async def get_specialty(self, resource_id: UUID, *, public_only: bool = False) -> Specialty | None:
        """Fetch one specialty."""
        statement = select(Specialty).where(Specialty.id == resource_id)
        if public_only:
            statement = statement.where(Specialty.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_specialties(
        self,
        *,
        public_only: bool,
        offset: int,
        limit: int,
        facility_id: UUID | None = None,
    ) -> list[Specialty]:
        """List specialties with pagination, optionally filtered by facility."""
        statement = select(Specialty)
        if public_only:
            statement = statement.where(Specialty.status == "active")
        if facility_id:
            from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty

            statement = (
                statement.join(DoctorSpecialty, DoctorSpecialty.specialty_id == Specialty.id)
                .join(DoctorFacility, DoctorFacility.doctor_id == DoctorSpecialty.doctor_id)
                .join(Doctor, Doctor.id == DoctorSpecialty.doctor_id)
                .where(
                    DoctorFacility.facility_id == facility_id,
                    Doctor.status == "active",
                )
                .distinct()
            )
        statement = statement.order_by(Specialty.name).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())
