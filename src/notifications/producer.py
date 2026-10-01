"""Kafka producer for durable notification records."""

from __future__ import annotations

from datetime import UTC, datetime

from src.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.session import get_session_factory
from src.notifications.schemas import NotificationEvent
from src.repositories.notification import NotificationRepository

logger = get_logger(__name__)


class NotificationProducer:
    """Publish notification events without owning a consumer loop."""

    def __init__(self, bootstrap_servers: str, topic: str, settings: Settings | None = None) -> None:
        from aiokafka import AIOKafkaProducer

        self.settings = settings or get_settings()
        self.topic = topic
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers, acks="all")
        self._started = False

    async def start(self) -> None:
        """Start the Kafka producer connection."""
        if not self._started:
            await self._producer.start()
            self._started = True

    async def stop(self) -> None:
        """Stop the Kafka producer connection."""
        if self._started:
            await self._producer.stop()
            self._started = False

    async def send(self, event: NotificationEvent) -> None:
        """Publish one event using its id as the Kafka key."""
        if not self._started:
            raise RuntimeError("NotificationProducer must be started before sending")
        await self._producer.send_and_wait(
            self.topic,
            key=str(event.event_id).encode("utf-8"),
            value=event.model_dump_json().encode("utf-8"),
        )

    async def publish_pending(self, limit: int = 100) -> int:
        """Claim and publish due database notifications."""
        if not self._started:
            raise RuntimeError("NotificationProducer must be started before publishing")

        async with get_session_factory()() as session:
            async with session.begin():
                await NotificationRepository(session).requeue_stale_processing(
                    datetime.now(UTC), self.settings.notification_processing_timeout_seconds
                )
                rows = await NotificationRepository(session).claim_pending(datetime.now(UTC), limit)

        published = 0
        for row in rows:
            event = NotificationEvent(
                event_id=row.id,
                notification_id=row.id,
                user_id=row.user_id,
                kind=row.kind,
                channel=row.channel,
                provider=row.provider,
                recipient=row.user.email if row.user else None,
                title=row.title,
                message=row.message,
            )
            try:
                await self.send(event)
                async with get_session_factory()() as session:
                    async with session.begin():
                        await NotificationRepository(session).mark_published(row.id, datetime.now(UTC))
                published += 1
            except Exception as exc:
                await self._mark_failed(row.id, exc)
                logger.exception("notification.producer publish failed", extra={"event_id": str(row.id)})
        return published

    async def _mark_failed(self, notification_id, error: Exception) -> None:
        """Persist publisher failures so the row can be retried later."""
        async with get_session_factory()() as session:
            async with session.begin():
                await NotificationRepository(session).mark_failed(
                    notification_id,
                    type(error).__name__,
                    datetime.now(UTC),
                    max_attempts=self.settings.notification_max_attempts,
                    retry_backoff_seconds=self.settings.notification_retry_backoff_seconds,
                    retry_backoff_max_seconds=self.settings.notification_retry_backoff_max_seconds,
                )
