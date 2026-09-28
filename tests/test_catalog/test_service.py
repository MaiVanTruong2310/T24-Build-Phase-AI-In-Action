"""Catalog service tests for partial bulk-import validation."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.core.exceptions import ConflictError
from src.models.catalog import DoctorSchedule
from src.schemas.catalog import BulkScheduleImportRequest, DoctorScheduleUpdate, ScheduleCancellationRequest
from src.services.catalog import CatalogService


class FakeTransaction:
    """Minimal transaction context for service tests that do not hit a database."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class FakeSession:
    """Minimal session exposing only the transaction API used by bulk import."""

    def begin(self):
        return FakeTransaction()

    async def flush(self):
        return None


class FakeCatalog:
    """Minimal catalog double for optimistic-lock service tests."""

    def __init__(self, schedule):
        self.schedule = schedule

    async def get_schedule(self, schedule_id):
        del schedule_id
        return self.schedule

    async def add_audit_event(self, event):
        del event


def test_bulk_import_keeps_valid_records_when_one_record_is_malformed():
    """One invalid row is reported while a valid row continues through upsert."""
    service = CatalogService(FakeSession())
    starts_at = datetime.now(UTC)

    async def fake_upsert(record, actor_id):
        del actor_id
        schedule = DoctorSchedule(
            id=uuid4(),
            doctor_id=record.doctor_id,
            facility_id=record.facility_id,
            starts_at=record.starts_at,
            ends_at=record.ends_at,
            capacity=record.capacity,
            status=record.status,
            version=1,
            source_system=record.source_system,
            external_schedule_id=record.external_schedule_id,
            created_at=starts_at,
            updated_at=starts_at,
        )
        return schedule, True

    service._upsert_schedule = fake_upsert
    valid = {
        "doctor_id": str(uuid4()),
        "facility_id": str(uuid4()),
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
        "capacity": 2,
        "source_system": "hospital-feed",
        "external_schedule_id": "slot-001",
    }
    malformed = {"external_schedule_id": "slot-002", "capacity": "not-a-number"}

    result = asyncio.run(
        service.bulk_import_schedules(
            BulkScheduleImportRequest(records=[valid, malformed]),
            uuid4(),
        )
    )

    assert result.created == 1
    assert result.updated == 0
    assert result.failed == 1
    assert result.items[0].schedule is not None
    assert result.items[1].external_schedule_id == "slot-002"
    assert result.items[1].error == "Invalid schedule record"


def test_schedule_update_rejects_stale_optimistic_lock_version():
    """A stale schedule version is rejected as a conflict before mutation."""
    starts_at = datetime.now(UTC)
    schedule = SimpleNamespace(
        version=3,
        status="available",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
    )
    service = CatalogService(FakeSession())
    service.catalog = FakeCatalog(schedule)

    with pytest.raises(ConflictError, match="Schedule version is stale"):
        asyncio.run(
            service.update_schedule(
                uuid4(),
                DoctorScheduleUpdate(
                    expected_version=2,
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=1),
                    capacity=4,
                    status="available",
                ),
                uuid4(),
            )
        )


def test_cancel_schedule_rejects_a_schedule_that_is_already_cancelled():
    """Cancellation is a terminal state and repeated requests conflict."""
    schedule = SimpleNamespace(status="cancelled")
    service = CatalogService(FakeSession())
    service.catalog = FakeCatalog(schedule)

    with pytest.raises(ConflictError, match="Schedule is already cancelled"):
        asyncio.run(
            service.cancel_schedule(
                uuid4(),
                ScheduleCancellationRequest(reason="Doctor unavailable"),
                uuid4(),
            )
        )
