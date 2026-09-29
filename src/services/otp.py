"""OTP provider abstractions and development implementation."""

import secrets
from collections.abc import MutableMapping
from typing import Protocol

from src.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class OtpProvider(Protocol):
    """Port used by the auth service to deliver one-time passwords."""

    async def send(self, target: str, code: str, purpose: str) -> None:
        """Deliver an OTP to a target."""


class MockOtpProvider:
    """In-memory OTP provider for local development and tests."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the development provider with local OTP configuration."""
        self._settings = settings
        self.sent_codes: MutableMapping[tuple[str, str], str] = {}

    def generate_code(self) -> str:
        """Generate a six-digit code for local delivery and mock API responses."""
        if self._settings.mock_otp_code:
            return self._settings.mock_otp_code
        return f"{secrets.randbelow(1_000_000):06d}"

    async def send(self, target: str, code: str, purpose: str) -> None:
        """Store the code for test inspection instead of sending externally."""
        self.sent_codes[(target, purpose)] = code
        logger.debug("MockOtpProvider.send OTP delivery simulated", extra={"purpose": purpose})
