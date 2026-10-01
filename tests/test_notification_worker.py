"""Notification worker and Gmail delivery tests."""

import asyncio
from unittest.mock import patch

from src.config import Settings
from src.services.email import GmailEmailSender


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
