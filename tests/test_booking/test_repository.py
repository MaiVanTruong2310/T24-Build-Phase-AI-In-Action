"""Staff booking repository query tests."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from src.repositories.booking import BookingRepository


class FakeResult:
    def __init__(self, rows=()):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows


class CapturingSession:
    def __init__(self):
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return 21

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult([("pending_approval", 21)]) if len(self.statements) == 2 else FakeResult()


def test_staff_booking_search_filters_and_pages_in_database():
    session = CapturingSession()
    service_id = uuid4()

    result = asyncio.run(
        BookingRepository(session).list_for_staff("pending_approval", None, 20, 20, "MED-abcd", service_id)
    )

    page_sql = str(session.statements[-1].compile(dialect=postgresql.dialect()))
    assert result[1:] == (21, {"all": 21, "pending_approval": 21, "confirmed": 0, "rejected": 0})
    assert "users.full_name" in page_sql
    assert "patient_profiles.full_name" in page_sql
    assert "left(CAST(bookings.id AS VARCHAR)," in page_sql
    assert "bookings.service_id" in page_sql
    assert "bookings.status" in page_sql
    assert "LIMIT" in page_sql and "OFFSET" in page_sql


def test_staff_scheduled_only_filter_requires_active_appointment_schedule():
    session = CapturingSession()

    asyncio.run(BookingRepository(session).list_for_staff("confirmed", None, 0, 20, scheduled_only=True))

    compiled = session.statements[-1].compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "EXISTS" in sql
    assert "doctor_schedules.id = bookings.appointment_schedule_id" in sql
    assert "doctor_schedules.status" in sql
    assert "available" in compiled.params.values()


def test_staff_ai_triage_prefers_booking_link_and_omits_ambiguous_mapping():
    booking_id, ambiguous_id = uuid4(), uuid4()
    cases = [
        SimpleNamespace(booking_id=None, source="booking", source_id=str(booking_id), ai_snapshot={"ats_level": 2}),
        SimpleNamespace(booking_id=booking_id, source="booking", source_id="legacy", ai_snapshot={"ats_level": 3}),
        SimpleNamespace(booking_id=None, source="booking", source_id=str(ambiguous_id), ai_snapshot={"ats_level": 1}),
        SimpleNamespace(booking_id=None, source="booking", source_id=str(ambiguous_id), ai_snapshot={"ats_level": 4}),
    ]

    class SnapshotSession:
        async def execute(self, _statement):
            return FakeResult(cases)

    result = asyncio.run(BookingRepository(SnapshotSession()).get_staff_ai_triage([booking_id, ambiguous_id]))
    assert result == {booking_id: {"ats_level": 3, "source": "booking"}}
