"""Medical service catalog business operations."""

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.core.errors import raise_integrity_conflict
from src.core.exceptions import NotFoundError
from src.core.logging import get_logger, log_event
from src.models.catalog import Service
from src.schemas.catalog import ServiceCreate, ServiceUpdate

logger = get_logger(__name__)


class MedicalServiceMixin:
    """Medical service operations composed into the catalog service."""

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
        """List medical services."""
        log_event(logger, logging.INFO, "catalog.service.list.start")
        values = await self.catalog.list_services(
            public_only=public_only,
            offset=offset,
            limit=limit,
            name=name,
            category=category,
            specialty_id=specialty_id,
            facility_id=facility_id,
        )
        log_event(logger, logging.INFO, "catalog.service.list.done")
        return values

    async def get_service(self, resource_id: UUID, *, public_only: bool) -> Service:
        """Get a medical service or raise a safe not-found error."""
        log_event(logger, logging.INFO, "catalog.service.get.start", resource_id=str(resource_id))
        value = await self.catalog.get_service(resource_id, public_only=public_only)
        if value is None:
            log_event(logger, logging.WARNING, "catalog.service.get.not_found", resource_id=str(resource_id))
            raise NotFoundError("Service not found")
        log_event(logger, logging.INFO, "catalog.service.get.done", resource_id=str(resource_id))
        return value

    async def create_service(self, request: ServiceCreate, actor_id: UUID) -> Service:
        """Create a medical service."""
        log_event(logger, logging.INFO, "catalog.service.create.start")
        try:
            async with self.session.begin():
                await self._ensure_code_available(Service, request.code)
                value = Service(**request.model_dump())
                self.session.add(value)
                await self.session.flush()
                await self._audit(actor_id, "service", value.id, "created", {"code": value.code})
        except IntegrityError as exc:
            raise_integrity_conflict(
                exc,
                logger=logger,
                event="catalog.service.create.persistence_conflict",
                code="SERVICE_CODE_EXISTS",
                message="Service code already exists",
                log_description="Medical service creation hit a duplicate code constraint",
                actor_id=str(actor_id),
                service_code=request.code,
            )
        log_event(logger, logging.INFO, "catalog.service.create.done", resource_id=str(value.id))
        await self._invalidate_catalog_cache()
        return value

    async def update_service(self, resource_id: UUID, request: ServiceUpdate, actor_id: UUID) -> Service:
        """Update a medical service."""
        log_event(logger, logging.INFO, "catalog.service.update.start", resource_id=str(resource_id))
        async with self.session.begin():
            value = await self._required(self.catalog.get_service(resource_id), "Service not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "service", value.id, "updated", request.model_dump(exclude_unset=True))
        log_event(logger, logging.INFO, "catalog.service.update.done", resource_id=str(value.id))
        await self._invalidate_catalog_cache()
        return value
