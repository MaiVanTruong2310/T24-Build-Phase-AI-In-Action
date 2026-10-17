"""Catalog audit response schema."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CatalogAuditResponse(BaseModel):
    """Audit history entry for internal callers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    entity_type: str
    entity_id: UUID
    action: str
    payload: dict
    created_at: datetime
