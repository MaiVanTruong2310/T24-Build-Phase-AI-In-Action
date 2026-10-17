"""Specialty catalog business operations."""

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.core.errors import raise_integrity_conflict
from src.core.exceptions import NotFoundError
from src.core.logging import get_logger, log_event
from src.models.catalog import Specialty
from src.schemas.catalog import SpecialtyCreate, SpecialtyUpdate

logger = get_logger(__name__)


class SpecialtyServiceMixin:
    """Specialty operations composed into the catalog service."""

    async def list_specialties(
        self,
        *,
        public_only: bool,
        offset: int,
        limit: int,
        facility_id: UUID | None = None,
        search: str | None = None,
    ) -> list[Specialty]:
        """List specialties."""
        log_event(logger, logging.INFO, "catalog.specialty.list.start")
        values = await self.catalog.list_specialties(
            public_only=public_only, offset=offset, limit=limit, facility_id=facility_id, search=search
        )
        log_event(logger, logging.INFO, "catalog.specialty.list.done")
        return values

    async def get_specialty(self, resource_id: UUID, *, public_only: bool) -> Specialty:
        """Get a specialty or raise a safe not-found error."""
        log_event(logger, logging.INFO, "catalog.specialty.get.start", resource_id=str(resource_id))
        value = await self.catalog.get_specialty(resource_id, public_only=public_only)
        if value is None:
            log_event(logger, logging.WARNING, "catalog.specialty.get.not_found", resource_id=str(resource_id))
            raise NotFoundError("Specialty not found")
        log_event(logger, logging.INFO, "catalog.specialty.get.done", resource_id=str(resource_id))
        return value

    async def create_specialty(self, request: SpecialtyCreate, actor_id: UUID) -> Specialty:
        """Create a specialty and audit the operation."""
        log_event(logger, logging.INFO, "catalog.specialty.create.start")
        try:
            async with self.session.begin():
                await self._ensure_code_available(Specialty, request.code)
                value = Specialty(**request.model_dump())
                self.session.add(value)
                await self.session.flush()
                await self._audit(actor_id, "specialty", value.id, "created", {"code": value.code})
        except IntegrityError as exc:
            raise_integrity_conflict(
                exc,
                logger=logger,
                event="catalog.specialty.create.persistence_conflict",
                code="SPECIALTY_CODE_EXISTS",
                message="Specialty code already exists",
                log_description="Specialty creation hit a duplicate code constraint",
                actor_id=str(actor_id),
                specialty_code=request.code,
            )
        log_event(logger, logging.INFO, "catalog.specialty.create.done", resource_id=str(value.id))
        await self._invalidate_catalog_cache()
        return value

    async def update_specialty(self, resource_id: UUID, request: SpecialtyUpdate, actor_id: UUID) -> Specialty:
        """Update a specialty without hard deletion."""
        log_event(logger, logging.INFO, "catalog.specialty.update.start", resource_id=str(resource_id))
        async with self.session.begin():
            value = await self._required(self.catalog.get_specialty(resource_id), "Specialty not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "updated", request.model_dump(exclude_unset=True))
        log_event(logger, logging.INFO, "catalog.specialty.update.done", resource_id=str(value.id))
        await self._invalidate_catalog_cache()
        return value
