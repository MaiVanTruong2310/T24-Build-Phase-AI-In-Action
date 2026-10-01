"""Kafka consumer with bounded retry and dead-letter handling."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from src.config import Settings, get_settings
from src.core.logging import get_logger
from src.db.session import get_session_factory
from src.notifications.schemas import NotificationEvent
from src.repositories.notification import NotificationRepository
from src.services.email import GmailEmailSender

logger = get_logger(__name__)


async def deliver(event: NotificationEvent, settings: Settings | None = None) -> None:
    """Deliver one event idempotently and mark its durable row as delivered."""
    settings = settings or get_settings()
    if event.event_id != event.notification_id:
        raise ValueError("Notification event_id must match notification_id")

    async with get_session_factory()() as session:
        notification = await NotificationRepository(session).get_processing(event.event_id)
        if notification is None or notification.status in ("delivered", "discarded"):
            return
        recipient = event.recipient or (notification.user.email if notification.user else None)
        channel = notification.channel
        title = notification.title
        message = notification.message

    if channel == "email":
        if not recipient:
            raise RuntimeError("Notification recipient email is missing")
        await GmailEmailSender(settings).send(recipient, title, message)
    elif channel != "in_app":
        raise RuntimeError(f"Unsupported notification channel: {channel}")

    async with get_session_factory()() as session:
        async with session.begin():
            await NotificationRepository(session).mark_delivered(event.event_id, datetime.now(UTC))


async def _mark_dead_letter(event: NotificationEvent, error: Exception) -> None:
    """Make a failed event terminal after it has been copied to the DLT."""
    async with get_session_factory()() as session:
        async with session.begin():
            await NotificationRepository(session).mark_dead_letter(
                event.notification_id,
                type(error).__name__,
                datetime.now(UTC),
            )


async def run_consumer(
    bootstrap: str,
    topic: str,
    dlt: str,
    *,
    group_id: str | None = None,
    max_attempts: int | None = None,
    settings: Settings | None = None,
) -> None:
    """Consume notification events with manual commits and DLT fallback."""
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

    settings = settings or get_settings()
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group_id or settings.notification_consumer_group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    dlt_producer = AIOKafkaProducer(bootstrap_servers=bootstrap, acks="all")
    attempts = max_attempts or settings.notification_max_attempts

    await consumer.start()
    await dlt_producer.start()
    try:
        async for msg in consumer:
            try:
                event = NotificationEvent.model_validate_json(msg.value)
            except Exception as exc:
                logger.warning("notification.consumer invalid event", extra={"error": type(exc).__name__})
                await dlt_producer.send_and_wait(dlt, key=msg.key, value=msg.value)
                await consumer.commit()
                continue

            for attempt in range(1, attempts + 1):
                try:
                    await deliver(event, settings)
                    break
                except Exception as exc:
                    logger.warning(
                        "notification.consumer delivery attempt failed",
                        extra={"event_id": str(event.event_id), "attempt": attempt, "error": type(exc).__name__},
                    )
                    if attempt == attempts:
                        await dlt_producer.send_and_wait(
                            dlt,
                            key=msg.key or str(event.event_id).encode("utf-8"),
                            value=msg.value,
                        )
                        await _mark_dead_letter(event, exc)
                    else:
                        await asyncio.sleep(2**attempt)
            await consumer.commit()
    except asyncio.CancelledError:
        raise
    finally:
        await consumer.stop()
        await dlt_producer.stop()
