"""Tests for authentication and role dependencies."""

import asyncio
from types import SimpleNamespace

import pytest

from src.api.dependencies import require_staff
from src.core.exceptions import AuthorizationError


def test_require_staff_accepts_staff_role():
    """Staff users can access staff-only dependencies."""
    user = SimpleNamespace(role="staff")

    assert asyncio.run(require_staff(user)) is user


def test_require_staff_rejects_patient_role():
    """Patient users cannot access staff-only dependencies."""
    user = SimpleNamespace(role="patient")

    with pytest.raises(AuthorizationError):
        asyncio.run(require_staff(user))
