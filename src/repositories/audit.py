"""Catalog audit persistence queries."""

from uuid import UUID

from sqlalchemy import select

from src.models.catalog import CatalogAuditEvent, DoctorSchedule


class AuditRepositoryMixin:
    """Audit queries composed into the catalog repository."""

    async def list_audit_events(self, entity_id: UUID, *, limit: int = 100) -> list[CatalogAuditEvent]:
        """Return newest audit events for an entity."""
        statement = (
            select(CatalogAuditEvent)
            .where(CatalogAuditEvent.entity_id == entity_id)
            .order_by(CatalogAuditEvent.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_schedule_audit_events(
        self,
        *,
        doctor_id: UUID,
        starts_from,
        starts_to,
        limit: int = 100,
    ) -> list[CatalogAuditEvent]:
        """Return audit events for a doctor's schedules in a time window."""
        statement = (
            select(CatalogAuditEvent)
            .join(DoctorSchedule, CatalogAuditEvent.entity_id == DoctorSchedule.id)
            .where(
                CatalogAuditEvent.entity_type == "doctor_schedule",
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.ends_at > starts_from,
                DoctorSchedule.starts_at < starts_to,
            )
            .order_by(CatalogAuditEvent.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def add_audit_event(self, event: CatalogAuditEvent) -> CatalogAuditEvent:
        """Persist an audit event."""
        self.session.add(event)
        await self.session.flush()
        return event
