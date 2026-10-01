"""Validation tests for catalog requests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.schemas.catalog import (
    BulkScheduleImportRequest,
    DoctorFacilityUpdate,
    DoctorScheduleCreate,
    DoctorScheduleUpdate,
    DoctorUpdate,
    ScheduleCancellationRequest,
    ScheduleImportRecord,
)


def test_schedule_requires_positive_time_range():
    """A schedule cannot end at or before its start."""
    starts_at = datetime.now(UTC)
    with pytest.raises(ValidationError):
        DoctorScheduleCreate(
            doctor_id=uuid4(),
            facility_id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at,
            capacity=1,
        )


def test_schedule_update_accepts_version_and_capacity():
    """PUT updates require the complete mutable schedule representation."""
    starts_at = datetime.now(UTC)
    request = DoctorScheduleUpdate(
        expected_version=3,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        capacity=4,
        status="available",
    )

    assert request.expected_version == 3
    assert request.capacity == 4


def test_busy_schedule_is_global_and_does_not_use_capacity():
    """Busy schedules can apply to every facility and ignore consultation capacity."""
    starts_at = datetime.now(UTC)
    request = DoctorScheduleCreate(
        doctor_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        capacity=4,
        type="busy",
        note="  Clinical meeting  ",
    )

    assert request.facility_id is None
    assert request.capacity == 0
    assert request.status == "blocked"
    assert request.note == "Clinical meeting"


def test_schedule_cancellation_requires_non_blank_reason():
    """Cancellation requires a trimmed, non-empty reason."""
    request = ScheduleCancellationRequest(reason="  Doctor unavailable  ")

    assert request.reason == "Doctor unavailable"

    with pytest.raises(ValidationError):
        ScheduleCancellationRequest(reason="   ")


def test_schedule_import_requires_external_identity():
    """Imported records must carry both idempotency fields."""
    starts_at = datetime.now(UTC)
    record = ScheduleImportRecord(
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        capacity=2,
        source_system="hospital-feed",
        external_schedule_id="slot-001",
    )

    assert record.external_schedule_id == "slot-001"

    with pytest.raises(ValidationError):
        ScheduleImportRecord(
            doctor_id=uuid4(),
            facility_id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            capacity=2,
            source_system="hospital-feed",
            external_schedule_id="",
        )


def test_bulk_import_defers_record_validation_to_service_layer():
    """A malformed record does not reject the entire batch at request parsing."""
    request = BulkScheduleImportRequest(records=[{"external_schedule_id": "bad-row"}])

    assert request.records == [{"external_schedule_id": "bad-row"}]


def test_doctor_facility_assignment_rejects_invalid_date_range():
    """A facility assignment cannot end before it starts."""
    with pytest.raises(ValidationError):
        DoctorFacilityUpdate(active_from=datetime(2026, 9, 20).date(), active_to=datetime(2026, 9, 19).date())


def test_doctor_update_carries_all_catalog_assignments():
    """The single doctor update payload owns specialty, facility and service links."""
    specialty_id = uuid4()
    facility_id = uuid4()
    service_id = uuid4()

    request = DoctorUpdate(
        specialty_ids=[specialty_id],
        facility_ids=[facility_id],
        service_ids=[service_id],
    )

    assert request.specialty_ids == [specialty_id]
    assert request.facility_ids == [facility_id]
    assert request.facilities is not None
    assert request.facilities[0].facility_id == facility_id
    assert request.service_ids == [service_id]
