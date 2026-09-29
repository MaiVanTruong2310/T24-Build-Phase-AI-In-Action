"""Specialty catalog business operations."""

from uuid import UUID

from src.core.exceptions import NotFoundError
from src.models.catalog import Specialty
from src.schemas.catalog import SpecialtyCreate, SpecialtyUpdate


class SpecialtyServiceMixin:
    """Specialty operations composed into the catalog service."""

    async def list_specialties(self, *, public_only: bool, offset: int, limit: int) -> list[Specialty]:
        """List specialties."""
        return await self.catalog.list_specialties(public_only=public_only, offset=offset, limit=limit)

    async def get_specialty(self, resource_id: UUID, *, public_only: bool) -> Specialty:
        """Get a specialty or raise a safe not-found error."""
        value = await self.catalog.get_specialty(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Specialty not found")
        return value

    async def create_specialty(self, request: SpecialtyCreate, actor_id: UUID) -> Specialty:
        """Create a specialty and audit the operation."""
        async with self.session.begin():
            await self._ensure_code_available(Specialty, request.code)
            value = Specialty(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "created", {"code": value.code})
        return value

    async def update_specialty(self, resource_id: UUID, request: SpecialtyUpdate, actor_id: UUID) -> Specialty:
        """Update a specialty without hard deletion."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_specialty(resource_id), "Specialty not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "updated", request.model_dump(exclude_unset=True))
        return value
