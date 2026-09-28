"""Medical service persistence queries."""

from uuid import UUID

from sqlalchemy import select

from src.models.catalog import Service


class MedicalServiceRepositoryMixin:
    """Medical service queries composed into the catalog repository."""

    async def get_service(self, resource_id: UUID, *, public_only: bool = False) -> Service | None:
        """Fetch one medical service."""
        statement = select(Service).where(Service.id == resource_id)
        if public_only:
            statement = statement.where(Service.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_services(self, *, public_only: bool, offset: int, limit: int) -> list[Service]:
        """List medical services with pagination."""
        statement = select(Service).order_by(Service.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Service.status == "active")
        return list((await self.session.execute(statement)).scalars().all())
