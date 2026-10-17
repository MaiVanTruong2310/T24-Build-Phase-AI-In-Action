"""Safe, allowlisted staff assistant alert contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StaffAssistantAlert(BaseModel):
    event_id: UUID
    case_id: UUID
    event_type: str
    reason: str
    created_at: datetime
