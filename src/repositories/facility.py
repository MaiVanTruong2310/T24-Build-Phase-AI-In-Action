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

    async def list_facilities(self, *, public_only: bool, offset: int, limit: int) -> list[Facility]:
        """List facilities with pagination."""
        statement = select(Facility).order_by(Facility.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Facility.status == "active")
        return list((await self.session.execute(statement)).scalars().all())
