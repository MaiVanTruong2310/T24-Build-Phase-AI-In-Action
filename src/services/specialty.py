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
    ) -> list[Specialty]:
        """List specialties."""
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.list.start",
            description="Starting specialty catalog query",
            public_only=public_only,
            offset=offset,
            limit=limit,
        )
        values = await self.catalog.list_specialties(public_only=public_only, offset=offset, limit=limit)
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.list.done",
            description="Specialties were listed using catalog visibility rules",
            count=len(values),
            public_only=public_only,
        )
        return values

    async def get_specialty(self, resource_id: UUID, *, public_only: bool) -> Specialty:
        """Get a specialty or raise a safe not-found error."""
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.get.start",
            description="Starting specialty lookup",
            resource_id=str(resource_id),
            public_only=public_only,
        )
        value = await self.catalog.get_specialty(resource_id, public_only=public_only)
        if value is None:
            log_event(
                logger,
                logging.WARNING,
                "catalog.specialty.get.not_found",
                description="Specialty lookup returned no visible specialty",
                resource_id=str(resource_id),
            )
            raise NotFoundError("Specialty not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.get.done",
            description="Specialty was loaded",
            resource_id=str(resource_id),
        )
        return value

    async def create_specialty(self, request: SpecialtyCreate, actor_id: UUID) -> Specialty:
        """Create a specialty and audit the operation."""
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.create.start",
            description="Starting specialty creation and audit",
            actor_id=str(actor_id),
            specialty_code=request.code,
        )
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
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.create.done",
            description="Specialty was created and audited",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        self._invalidate_catalog_cache()
        return value

    async def update_specialty(self, resource_id: UUID, request: SpecialtyUpdate, actor_id: UUID) -> Specialty:
        """Update a specialty without hard deletion."""
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.update.start",
            description="Starting specialty update and audit",
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            changed_fields=list(request.model_dump(exclude_unset=True).keys()),
        )
        async with self.session.begin():
            value = await self._required(self.catalog.get_specialty(resource_id), "Specialty not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "specialty", value.id, "updated", request.model_dump(exclude_unset=True))
        log_event(
            logger,
            logging.INFO,
            "catalog.specialty.update.done",
            description="Specialty fields were updated and audited",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        self._invalidate_catalog_cache()
        return value
