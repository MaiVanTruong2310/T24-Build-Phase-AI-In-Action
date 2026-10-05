"""Facility catalog business operations."""

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.core.errors import raise_integrity_conflict
from src.core.exceptions import NotFoundError
from src.core.logging import get_logger, log_event
from src.models.catalog import Facility
from src.schemas.catalog import FacilityCreate, FacilityUpdate

logger = get_logger(__name__)


class FacilityServiceMixin:
    """Facility operations composed into the catalog service."""

    async def list_facilities(self, *, public_only: bool, offset: int, limit: int) -> list[Facility]:
        """List facilities."""
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.list.start",
            description="Starting facility catalog query",
            public_only=public_only,
            offset=offset,
            limit=limit,
        )
        values = await self.catalog.list_facilities(public_only=public_only, offset=offset, limit=limit)
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.list.done",
            description="Facilities were listed using catalog visibility rules",
            count=len(values),
            public_only=public_only,
        )
        return values

    async def get_facility(self, resource_id: UUID, *, public_only: bool) -> Facility:
        """Get a facility or raise a safe not-found error."""
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.get.start",
            description="Starting facility lookup",
            resource_id=str(resource_id),
            public_only=public_only,
        )
        value = await self.catalog.get_facility(resource_id, public_only=public_only)
        if value is None:
            log_event(
                logger,
                logging.WARNING,
                "catalog.facility.get.not_found",
                description="Facility lookup returned no visible facility",
                resource_id=str(resource_id),
            )
            raise NotFoundError("Facility not found")
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.get.done",
            description="Facility was loaded",
            resource_id=str(resource_id),
        )
        return value

    async def create_facility(self, request: FacilityCreate, actor_id: UUID) -> Facility:
        """Create a facility."""
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.create.start",
            description="Starting facility creation and audit",
            actor_id=str(actor_id),
            facility_code=request.code,
        )
        try:
            async with self.session.begin():
                await self._ensure_code_available(Facility, request.code)
                value = Facility(**request.model_dump())
                self.session.add(value)
                await self.session.flush()
                await self._audit(actor_id, "facility", value.id, "created", {"code": value.code})
        except IntegrityError as exc:
            raise_integrity_conflict(
                exc,
                logger=logger,
                event="catalog.facility.create.persistence_conflict",
                code="FACILITY_CODE_EXISTS",
                message="Facility code already exists",
                log_description="Facility creation hit a duplicate code constraint",
                actor_id=str(actor_id),
                facility_code=request.code,
            )
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.create.done",
            description="Facility was created and audited",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        self._invalidate_catalog_cache()
        return value

    async def update_facility(self, resource_id: UUID, request: FacilityUpdate, actor_id: UUID) -> Facility:
        """Update a facility."""
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.update.start",
            description="Starting facility update and audit",
            resource_id=str(resource_id),
            actor_id=str(actor_id),
            changed_fields=list(request.model_dump(exclude_unset=True).keys()),
        )
        async with self.session.begin():
            value = await self._required(self.catalog.get_facility(resource_id), "Facility not found")
            for field, item in request.model_dump(exclude_unset=True).items():
                setattr(value, field, item)
            await self.session.flush()
            await self._audit(actor_id, "facility", value.id, "updated", request.model_dump(exclude_unset=True))
        log_event(
            logger,
            logging.INFO,
            "catalog.facility.update.done",
            description="Facility fields were updated and audited",
            resource_id=str(value.id),
            actor_id=str(actor_id),
        )
        self._invalidate_catalog_cache()
        return value
