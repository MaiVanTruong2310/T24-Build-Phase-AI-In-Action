"""Notification delivery and Gmail tests."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from src.config import Settings
from src.services.email import GmailEmailSender
from src.services.notification import NotificationService


class FakeTransaction:
    """Small transaction context double for direct email delivery tests."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class FakeSession:
    """Small session double for direct email delivery tests."""

    def begin(self):
        return FakeTransaction()


class FakeSmtpClient:
    """Small SMTP context-manager double for the Gmail sender."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def starttls(self):
        return None

    def login(self, username, password):
        self.credentials = (username, password)

    def send_message(self, message):
        self.message = message


def test_gmail_sender_uses_smtp_app_password_without_logging_credentials():
    """Gmail delivery uses TLS, login and a plain-text message."""
    settings = Settings(
        gmail_smtp_username="clinic@gmail.com",
        gmail_smtp_app_password="app-password",
        gmail_from_email="noreply@clinic.example",
    )
    client = FakeSmtpClient()

    with patch("src.services.email.smtplib.SMTP", return_value=client) as smtp:
        asyncio.run(GmailEmailSender(settings).send("patient@example.com", "Reminder", "Please attend"))

    smtp.assert_called_once()
    assert client.credentials == ("clinic@gmail.com", "app-password")
    assert client.message["To"] == "patient@example.com"
    assert client.message["From"] == "noreply@clinic.example"
    assert client.message.get_content().strip() == "Please attend"


def test_pending_email_is_delivered_and_marked_after_smtp_accepts():
    """Successful SMTP delivery completes the claimed outbox row."""
    settings = Settings(gmail_smtp_username="clinic@gmail.com", gmail_smtp_app_password="app-password")
    service = NotificationService(FakeSession(), settings=settings)
    notification = SimpleNamespace(
        id=uuid4(),
        title="Lịch khám đã được duyệt",
        message="Lịch khám của bạn đã được xác nhận.",
        user=SimpleNamespace(email="patient@example.com"),
    )
    service.notifications.requeue_stale_email = _async_value(0)
    service.notifications.claim_email_pending = _async_value([notification])
    service.notifications.mark_email_delivered = _async_value(None)
    service.email_sender.send = _async_value(None)

    assert asyncio.run(service.deliver_pending_emails()) == 1
    assert service.email_sender.send.await_count == 1
    assert service.notifications.mark_email_delivered.await_count == 1


def test_pending_email_failure_is_scheduled_for_retry():
    """SMTP failure records a retry without raising into the booking loop."""
    settings = Settings(
        gmail_smtp_username="clinic@gmail.com",
        gmail_smtp_app_password="app-password",
        notification_max_attempts=3,
    )
    service = NotificationService(FakeSession(), settings=settings)
    notification = SimpleNamespace(
        id=uuid4(),
        title="Reminder",
        message="Please attend",
        user=SimpleNamespace(email="patient@example.com"),
    )
    service.notifications.requeue_stale_email = _async_value(0)
    service.notifications.claim_email_pending = _async_value([notification])
    service.notifications.mark_email_failed = _async_value(None)

    async def fail_send(*_args):
        raise TimeoutError("smtp timeout")

    service.email_sender.send = fail_send

    assert asyncio.run(service.deliver_pending_emails()) == 0
    assert service.notifications.mark_email_failed.await_count == 1
    assert service.notifications.mark_email_failed.await_args.args[1] == "TimeoutError"


def _async_value(value):
    """Build an awaitable mock without exposing SMTP details in the test."""
    from unittest.mock import AsyncMock

    return AsyncMock(return_value=value)
