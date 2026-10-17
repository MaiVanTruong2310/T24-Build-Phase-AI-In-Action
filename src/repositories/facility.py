"""Facility persistence queries."""

from uuid import UUID

from sqlalchemy import select

from src.models.catalog import Facility


class FacilityRepositoryMixin:
    """Facility queries composed into the catalog repository."""

    async def get_facility(self, resource_id: UUID, *, public_only: bool = False) -> Facility | None:
        """Fetch one facility."""
        statement = select(Facility).where(Facility.id == resource_id)
        if public_only:
            statement = statement.where(Facility.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_facilities(
        self,
        *,
        public_only: bool,
        offset: int,
        limit: int,
        specialty_id: UUID | None = None,
    ) -> list[Facility]:
        """List facilities with pagination, optionally filtered by specialty."""
        statement = select(Facility)
        if public_only:
            statement = statement.where(Facility.status == "active")
        if specialty_id:
            from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty

            statement = (
                statement.join(DoctorFacility, DoctorFacility.facility_id == Facility.id)
                .join(DoctorSpecialty, DoctorSpecialty.doctor_id == DoctorFacility.doctor_id)
                .join(Doctor, Doctor.id == DoctorFacility.doctor_id)
                .where(
                    DoctorSpecialty.specialty_id == specialty_id,
                    Doctor.status == "active",
                )
                .distinct()
            )
        statement = statement.order_by(Facility.name).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())
