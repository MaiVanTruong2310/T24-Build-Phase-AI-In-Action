"""Small authentication value and time helpers."""

import hashlib
from datetime import UTC, datetime


def normalize_identity(email: str | None, phone: str | None) -> tuple[str | None, str | None]:
    """Normalize optional email and phone values for identity lookup."""
    return (email.strip().lower() if email else None, phone.strip() if phone else None)


def otp_target(email: str | None, phone: str | None) -> str:
    """Select the identity value used by an OTP challenge."""
    return email or phone or ""


def hash_otp(code: str) -> str:
    """Hash an OTP before storing or comparing it."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)
