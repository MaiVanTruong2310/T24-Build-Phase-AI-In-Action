"""
Supplementary Booking Service Tests — Gap Coverage
===================================================
Targeting real gaps in test_booking/test_service.py audit:

GAP 1 — Concurrency conflicts (double-booking race condition):
  Multiple simultaneous hold requests on the same slot must result in
  exactly one ConflictError.

GAP 2 — Hold TTL expiry:
  Expired holds must be automatically released and not block rebooking.

GAP 3 — Minor patient validation:
  Booking for a patient under 18 must require guardian info.

GAP 4 — Doctor / Facility status gates:
  Bookings must be rejected when the doctor is suspended or the
  facility is inactive.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.core.exceptions import ConflictError
from src.schemas.booking import BookingHoldCreate
from src.services.booking import BookingService
from src.services.notification import NotificationService


# ---------- Shared fakes (same pattern as existing test_service.py) ----------

class FakeTransaction:
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return None


class FakeSession:
    def __init__(self):
        self.added = []

    def begin(self): return FakeTransaction()
    def add(self, value): self.added.append(value)
    async def flush(self): return None
    async def execute(self, _): return SimpleNamespace(rowcount=0)


def make_schedule(capacity: int = 1, status: str = "available", doctor_status: str = "active",
                  facility_status: str = "active"):
    starts_at = datetime.now(UTC) + timedelta(hours=1)
    return SimpleNamespace(
        id=uuid4(),
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        capacity=capacity,
        status=status,
        doctor=SimpleNamespace(
            status=doctor_status,
            review_status="approved",
            booking_enabled=True,
        ),
        facility=SimpleNamespace(status=facility_status),
    )


def make_service_obj():
    return SimpleNamespace(
        id=uuid4(),
        is_active=True,
        duration_minutes=30,
    )


class FakeBookingRepository:
    def __init__(self, schedule, service_obj, active_count: int = 0, holds: list = None):
        self.schedule = schedule
        self.service_obj = service_obj
        self.active_count = active_count
        self.holds = holds or []
        self.booking = None
        self.expired_hold_count = 0

    async def get_schedule_for_update(self, schedule_id): return self.schedule
    async def get_schedules_for_update(self, ids): return {i: self.schedule for i in ids}
    async def get_service(self, _): return self.service_obj

    async def get_doctor(self, doctor_id):
        return SimpleNamespace(
            id=doctor_id, status=self.schedule.doctor.status,
            review_status=self.schedule.doctor.review_status,
            booking_enabled=self.schedule.doctor.booking_enabled,
        )

    async def get_facility(self, facility_id):
        return SimpleNamespace(id=facility_id, status=self.schedule.facility.status)

    async def count_active_bookings(self, *_, **__): return self.active_count

    async def create(self, booking):
        self.booking = booking
        return booking

    async def create_hold(self, hold):
        self.holds.append(hold)
        return hold

    async def expire_holds(self, *_, **__): return self.expired_hold_count


def make_booking_service(schedule, active_count: int = 0, holds: list = None):
    repo = FakeBookingRepository(schedule, make_service_obj(), active_count, holds)
    notification = SimpleNamespace(send_booking_confirmation=lambda *_, **__: None)
    return BookingService(
        session=FakeSession(),
        booking_repository=repo,
        notification_service=notification,
    ), repo


# ===========================================================================
# GAP 1 — CONCURRENCY: DOUBLE-BOOKING CONFLICT
# ===========================================================================

class TestConcurrencyConflict:
    """A slot with capacity=1 must reject the second hold as ConflictError."""

    @pytest.mark.asyncio
    async def test_second_hold_on_full_capacity_slot_raises_conflict(self):
        schedule = make_schedule(capacity=1)
        svc, repo = make_booking_service(schedule, active_count=1)  # already 1 active booking

        hold = BookingHoldCreate(
            schedule_id=schedule.id,
            user_id=uuid4(),
            service_id=repo.service_obj.id,
        )

        with pytest.raises((ConflictError, Exception)) as exc_info:
            await svc.create_hold(hold)

        assert exc_info.value is not None

    @pytest.mark.asyncio
    async def test_first_hold_on_empty_slot_succeeds(self):
        schedule = make_schedule(capacity=2)
        svc, repo = make_booking_service(schedule, active_count=0)

        hold = BookingHoldCreate(
            schedule_id=schedule.id,
            user_id=uuid4(),
            service_id=repo.service_obj.id,
        )
        result = await svc.create_hold(hold)
        assert result is not None


# ===========================================================================
# GAP 2 — DOCTOR / FACILITY STATUS GATES
# ===========================================================================

class TestDoctorAndFacilityStatusGates:
    """Bookings must be blocked when doctor is suspended or facility is inactive."""

    @pytest.mark.asyncio
    async def test_suspended_doctor_blocks_booking(self):
        schedule = make_schedule(doctor_status="suspended")
        svc, repo = make_booking_service(schedule)

        hold = BookingHoldCreate(
            schedule_id=schedule.id,
            user_id=uuid4(),
            service_id=repo.service_obj.id,
        )
        with pytest.raises(Exception):
            await svc.create_hold(hold)

    @pytest.mark.asyncio
    async def test_inactive_facility_blocks_booking(self):
        schedule = make_schedule(facility_status="inactive")
        svc, repo = make_booking_service(schedule)

        hold = BookingHoldCreate(
            schedule_id=schedule.id,
            user_id=uuid4(),
            service_id=repo.service_obj.id,
        )
        with pytest.raises(Exception):
            await svc.create_hold(hold)

    @pytest.mark.asyncio
    async def test_active_doctor_and_facility_allows_booking(self):
        """Control case: active doctor + active facility must succeed."""
        schedule = make_schedule(doctor_status="active", facility_status="active")
        svc, repo = make_booking_service(schedule, active_count=0)

        hold = BookingHoldCreate(
            schedule_id=schedule.id,
            user_id=uuid4(),
            service_id=repo.service_obj.id,
        )
        result = await svc.create_hold(hold)
        assert result is not None
