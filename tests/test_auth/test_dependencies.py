"""Tests for authentication and role dependencies."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.dependencies import require_patient, require_staff
from src.core.exceptions import AuthorizationError


def _db(member):
    db = AsyncMock()
    db.get.return_value = member
    return db


def test_require_staff_accepts_staff_role():
    """Staff users with an enabled coordinator membership can access staff-only dependencies."""
    user = SimpleNamespace(id=uuid4(), role="staff")

    assert asyncio.run(require_staff(user, _db(SimpleNamespace(enabled=True)))) is user


def test_require_staff_rejects_patient_role():
    """Patient users cannot access staff-only dependencies."""
    user = SimpleNamespace(id=uuid4(), role="patient")

    with pytest.raises(AuthorizationError):
        asyncio.run(require_staff(user, _db(SimpleNamespace(enabled=True))))


@pytest.mark.parametrize("member", [None, SimpleNamespace(enabled=False)])
def test_require_staff_rejects_revoked_or_missing_coordinator(member):
    """Thu hồi quyền điều phối (role vẫn là staff) hoặc chưa được cấp: không gọi được API staff."""
    user = SimpleNamespace(id=uuid4(), role="staff")
    db = _db(member)

    with pytest.raises(AuthorizationError):
        asyncio.run(require_staff(user, db))
    db.commit.assert_awaited()  # transaction tự mở đã được đóng


def test_require_patient_accepts_patient_role():
    """Patients can use patient-owned booking endpoints."""
    user = SimpleNamespace(role="patient")

    assert asyncio.run(require_patient(user)) is user


def test_require_patient_rejects_staff_role():
    """Staff must use staff booking review endpoints instead."""
    user = SimpleNamespace(role="staff")

    with pytest.raises(AuthorizationError):
        asyncio.run(require_patient(user))
