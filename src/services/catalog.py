"""Compatibility facade composing the catalog domain service modules."""

import inspect
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import invalidate_catalog_cache
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
from src.models.catalog import CatalogAuditEvent, DoctorSchedule
from src.repositories.catalog import CatalogRepository
from src.schemas.catalog import DoctorFacilityAssignment
from src.services.doctor import DoctorServiceMixin
from src.services.facility import FacilityServiceMixin
from src.services.schedule import ScheduleServiceMixin
from src.services.service import MedicalServiceMixin
from src.services.specialty import SpecialtyServiceMixin
from src.utils.serialization import json_safe

logger = get_logger(__name__)


class CatalogService(
    SpecialtyServiceMixin,
    FacilityServiceMixin,
    MedicalServiceMixin,
    DoctorServiceMixin,
    ScheduleServiceMixin,
):
    """Compose catalog domain operations over one request-scoped session."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with one request-scoped session."""
        self.session = session
        self.catalog = CatalogRepository(session)

    @staticmethod
    def _invalidate_catalog_cache() -> None:
        """Invalidate public catalog reads after a committed catalog mutation."""
        invalidate_catalog_cache()

    async def _validate_assignments(
        self,
        specialty_ids: list[UUID] | None,
        facilities: list[DoctorFacilityAssignment] | None,
        service_ids: list[UUID] | None,
    ) -> None:
        """Ensure every supplied doctor assignment points to an active resource."""
        for resource_id in specialty_ids or []:
            value = await self.catalog.get_specialty(resource_id)
            if value is None or value.status != "active":
                raise NotFoundError("Specialty assignment not found")
        for assignment in facilities or []:
            value = await self.catalog.get_facility(assignment.facility_id)
            if value is None or value.status != "active":
                raise NotFoundError("Facility assignment not found")
        for resource_id in service_ids or []:
            value = await self.catalog.get_service(resource_id)
            if value is None or value.status != "active":
                raise NotFoundError("Service assignment not found")

    async def _ensure_code_available(self, model: type, code: str) -> None:
        """Reject duplicate natural identifiers before writing."""
        existing = (await self.session.execute(select(model).where(model.code == code))).scalar_one_or_none()
        if existing is not None:
            raise ConflictError("CODE_EXISTS", "Catalog code already exists")

    async def _audit(self, actor_id: UUID, entity_type: str, entity_id: UUID, action: str, payload: dict) -> None:
        """Write a durable audit record and a safe application log."""
        await self.catalog.add_audit_event(
            CatalogAuditEvent(
                actor_id=actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                payload=json_safe(payload),
            )
        )
        log_event(
            logger,
            logging.INFO,
            "catalog.audit.recorded",
            description="A catalog business change was recorded in the audit trail",
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
        )

    @staticmethod
    async def _required(value, message: str):
        """Return a value or raise a not-found error."""
        if inspect.isawaitable(value):
            value = await value
        if value is None:
            raise NotFoundError(message)
        return value

    @staticmethod
    def _schedule_is_public(value: DoctorSchedule) -> bool:
        """Check the non-query public availability rules for one slot."""
        return (
            value.status == "available"
            and value.capacity > 0
            and value.doctor.status == "active"
            and value.doctor.review_status == "approved"
            and value.doctor.booking_enabled
            and value.facility.status == "active"
        )
