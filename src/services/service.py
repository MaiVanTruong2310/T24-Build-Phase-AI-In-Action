"""Medical service catalog business operations."""

from uuid import UUID

from src.core.exceptions import NotFoundError
from src.models.catalog import Service
from src.schemas.catalog import ServiceCreate, ServiceUpdate


class MedicalServiceMixin:
    """Medical service operations composed into the catalog service."""

    async def list_services(self, *, public_only: bool, offset: int, limit: int) -> list[Service]:
        """List medical services."""
        return await self.catalog.list_services(public_only=public_only, offset=offset, limit=limit)

    async def get_service(self, resource_id: UUID, *, public_only: bool) -> Service:
        """Get a medical service or raise a safe not-found error."""
        value = await self.catalog.get_service(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Service not found")
        return value

    async def create_service(self, request: ServiceCreate, actor_id: UUID) -> Service:
        """Create a medical service."""
        async with self.session.begin():
            await self._ensure_code_available(Service, request.code)
            value = Service(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "service", value.id, "created", {"code": value.code})
        return value

    async def update_service(self, resource_id: UUID, request: ServiceUpdate, actor_id: UUID) -> Service:
        """Update a medical service."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_service(resource_id), "Service not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "service", value.id, "updated", request.model_dump(exclude_unset=True))
        return value
