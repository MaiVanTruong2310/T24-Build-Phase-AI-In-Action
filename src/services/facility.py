"""Facility catalog business operations."""

from uuid import UUID

from src.core.exceptions import NotFoundError
from src.models.catalog import Facility
from src.schemas.catalog import FacilityCreate, FacilityUpdate


class FacilityServiceMixin:
    """Facility operations composed into the catalog service."""

    async def list_facilities(
        self,
        *,
        public_only: bool,
        offset: int,
        limit: int,
        specialty_id: UUID | None = None,
    ) -> list[Facility]:
        """List facilities."""
        return await self.catalog.list_facilities(
            public_only=public_only, offset=offset, limit=limit, specialty_id=specialty_id
        )

    async def get_facility(self, resource_id: UUID, *, public_only: bool) -> Facility:
        """Get a facility or raise a safe not-found error."""
        value = await self.catalog.get_facility(resource_id, public_only=public_only)
        if value is None:
            raise NotFoundError("Facility not found")
        return value

    async def create_facility(self, request: FacilityCreate, actor_id: UUID) -> Facility:
        """Create a facility."""
        async with self.session.begin():
            await self._ensure_code_available(Facility, request.code)
            value = Facility(**request.model_dump())
            self.session.add(value)
            await self.session.flush()
            await self._audit(actor_id, "facility", value.id, "created", {"code": value.code})
        return value

    async def update_facility(self, resource_id: UUID, request: FacilityUpdate, actor_id: UUID) -> Facility:
        """Update a facility."""
        async with self.session.begin():
            value = await self._required(self.catalog.get_facility(resource_id), "Facility not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "facility", value.id, "updated", request.model_dump(exclude_unset=True))
        return value
