"""Catalog audit persistence queries."""

from uuid import UUID

from sqlalchemy import select

from src.models.catalog import CatalogAuditEvent


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

    async def add_audit_event(self, event: CatalogAuditEvent) -> CatalogAuditEvent:
        """Persist an audit event."""
        self.session.add(event)
        await self.session.flush()
        return event
