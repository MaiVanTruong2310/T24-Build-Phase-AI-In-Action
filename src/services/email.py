"""Gmail SMTP App Password delivery for patient notifications."""

import asyncio
import smtplib
from email.message import EmailMessage

from src.config import Settings


class GmailEmailSender:
    """Send plain-text notification emails through Gmail SMTP."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, recipient: str, subject: str, message: str) -> None:
        """Send one email without blocking the async API event loop."""
        await asyncio.to_thread(self._send_sync, recipient, subject, message)

    def _send_sync(self, recipient: str, subject: str, message: str) -> None:
        """Perform the synchronous SMTP exchange in a worker thread."""
        if not self.settings.gmail_smtp_username or not self.settings.gmail_smtp_app_password:
            raise RuntimeError("Gmail SMTP credentials are not configured")
        sender = self.settings.gmail_from_email or self.settings.gmail_smtp_username
        email = EmailMessage()
        email["From"] = sender
        email["To"] = recipient
        email["Subject"] = subject
        email.set_content(message)
        with smtplib.SMTP(
            self.settings.gmail_smtp_host,
            self.settings.gmail_smtp_port,
            timeout=self.settings.database_connect_timeout_seconds,
        ) as client:
            client.starttls()
            client.login(self.settings.gmail_smtp_username, self.settings.gmail_smtp_app_password)
            client.send_message(email)
