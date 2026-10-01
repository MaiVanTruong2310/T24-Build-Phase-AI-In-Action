"""Kafka publisher/consumer for durable booking notifications."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.session import close_database, get_session_factory, initialize_database
from src.repositories.notification import NotificationRepository
from src.services.email import GmailEmailSender

logger = get_logger(__name__)


class NotificationWorker:
    """Publish pending rows to Kafka and complete them from one consumer group."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.email_sender = GmailEmailSender(settings)

    async def run(self) -> None:
        """Run the publisher and consumer until the process is cancelled."""
        producer = AIOKafkaProducer(bootstrap_servers=self.settings.kafka_bootstrap_servers)
        consumer = AIOKafkaConsumer(
            self.settings.notification_topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=self.settings.notification_consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await producer.start()
        await consumer.start()
        try:
            while True:
                await self.publish_pending(producer)
                await self.requeue_stale()
                records = await consumer.getmany(
                    timeout_ms=int(self.settings.notification_poll_interval_seconds * 1000)
                )
                for messages in records.values():
                    for message in messages:
                        await self.handle_message(message.value)
                if records:
                    await consumer.commit()
        finally:
            await consumer.stop()
            await producer.stop()
            await close_database()

    async def publish_pending(self, producer: AIOKafkaProducer, limit: int = 100) -> int:
        """Claim and publish due notification identifiers."""
        async with get_session_factory()() as session:
            async with session.begin():
                rows = await NotificationRepository(session).claim_pending(datetime.now(UTC), limit)
        published = 0
        for row in rows:
            payload = json.dumps({"notification_id": str(row.id)}).encode("utf-8")
            try:
                await producer.send_and_wait(
                    self.settings.notification_topic,
                    key=str(row.id).encode("utf-8"),
                    value=payload,
                )
                async with get_session_factory()() as session:
                    async with session.begin():
                        await NotificationRepository(session).mark_published(row.id, datetime.now(UTC))
                published += 1
            except Exception as exc:
                await self.mark_failed(row.id, exc)
                logger.exception("NotificationWorker.publish failed", extra={"notification_id": str(row.id)})
        return published

    async def handle_message(self, raw_value: bytes) -> None:
        """Deliver one Kafka notification message idempotently."""
        payload = json.loads(raw_value.decode("utf-8"))
        notification_id = UUID(payload["notification_id"])
        async with get_session_factory()() as session:
            notification = await NotificationRepository(session).get_processing(notification_id)
            if notification is None or notification.status in ("delivered", "discarded"):
                return
            recipient = notification.user.email if notification.user else None
            channel = notification.channel
            title = notification.title
            message = notification.message

        try:
            if channel == "email":
                if not recipient:
                    raise RuntimeError("Patient email address is missing")
                await self.email_sender.send(recipient, title, message)
            async with get_session_factory()() as session:
                async with session.begin():
                    await NotificationRepository(session).mark_delivered(notification_id, datetime.now(UTC))
        except Exception as exc:
            await self.mark_failed(notification_id, exc)
            logger.exception("NotificationWorker.delivery failed", extra={"notification_id": str(notification_id)})

    async def mark_failed(self, notification_id: UUID, error: Exception) -> None:
        """Persist retry/backoff state without exposing provider secrets."""
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

    async def requeue_stale(self) -> int:
        """Recover rows abandoned by a crashed worker."""
        async with get_session_factory()() as session:
            async with session.begin():
                return await NotificationRepository(session).requeue_stale_processing(
                    datetime.now(UTC), self.settings.notification_processing_timeout_seconds
                )


async def main() -> None:
    """Run the notification worker process."""
    settings = get_settings()
    if not settings.kafka_enabled:
        raise RuntimeError("KAFKA_ENABLED must be true for the notification worker")
    if settings.database_auto_create:
        await initialize_database()
    await NotificationWorker(settings).run()


if __name__ == "__main__":
    asyncio.run(main())
