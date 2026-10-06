"""Helpers for serializing domain values into persistence-safe payloads."""

from datetime import date, datetime
from uuid import UUID


def json_safe(values: dict) -> dict:
    """Convert UUID and date-like values to JSON-safe values."""
    return {
        key: value.isoformat() if isinstance(value, (UUID, date, datetime)) else value for key, value in values.items()
    }
