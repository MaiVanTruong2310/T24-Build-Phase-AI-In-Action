"""Booking expiry field and query contract regressions."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from src.repositories.booking import BookingRepository
from src.utils.response_mappers import booking_response


class EmptyScalars:
    def scalars(self):
        return self

    def all(self):
        return []


class CaptureSession:
    statement = None

    async def execute(self, statement):
        self.statement = statement
        return EmptyScalars()


def test_booking_response_maps_expired_at():
    deadline = datetime(2030, 1, 2, tzinfo=UTC)
    booking = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        schedule_id=None,
        service_id=uuid4(),
        specialty_id=uuid4(),
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=deadline,
        ends_at=deadline,
        service=SimpleNamespace(booking_mode="doctor_visit"),
        encounter_type="in_person",
        reason="Check-up",
        patient_note=None,
        status="pending_approval",
        expired_at=deadline,
        cancellation_reason=None,
        staff_note=None,
        reviewed_by=None,
        reviewed_at=None,
        created_at=deadline,
        updated_at=deadline,
    )

    assert booking_response(booking).expired_at == deadline


def test_expiry_query_uses_deadline_column_and_skip_locked():
    session = CaptureSession()
    now = datetime(2030, 1, 2, tzinfo=UTC)

    assert asyncio.run(BookingRepository(session).claim_expired_pending_bookings(now, 25)) == []
    compiled = session.statement.compile(dialect=postgresql.dialect())

    assert "bookings.expired_at <=" in str(compiled)
    assert "bookings.status =" in str(compiled)
    assert "pending_approval" in compiled.params.values()
    assert "FOR UPDATE SKIP LOCKED" in str(compiled)
    assert 25 in compiled.params.values()
