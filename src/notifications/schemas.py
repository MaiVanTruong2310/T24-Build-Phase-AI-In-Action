"""Events exchanged by the notification producer and consumer."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationEvent(BaseModel):
    """Serializable notification event.

    ``event_id`` is the durable notification id.  Keeping it in the Kafka
    payload lets the consumer perform an idempotency check before delivery.
    """

    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    notification_id: UUID
    user_id: UUID
    kind: str
    channel: str
    provider: str
    recipient: str | None = None
    title: str
    message: str
