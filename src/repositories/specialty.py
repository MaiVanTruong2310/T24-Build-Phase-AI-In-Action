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

    async def list_specialties(self, *, public_only: bool, offset: int, limit: int) -> list[Specialty]:
        """List specialties with pagination."""
        statement = select(Specialty).order_by(Specialty.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Specialty.status == "active")
        return list((await self.session.execute(statement)).scalars().all())
