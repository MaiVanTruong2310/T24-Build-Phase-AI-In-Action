"""Booking capacity and ownership business-rule tests."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.core.exceptions import ConflictError
from src.models.booking import Booking
from src.schemas.booking import BookingCreate
from src.services.booking import BookingService


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class FakeSession:
    def begin(self):
        return FakeTransaction()

    async def flush(self):
        return None


def make_schedule(capacity: int = 2):
    starts_at = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        capacity=capacity,
        status="available",
        doctor=SimpleNamespace(status="active", review_status="approved", booking_enabled=True),
        facility=SimpleNamespace(status="active"),
    )


class FakeBookingRepository:
    def __init__(self, schedule, service, active_count):
        self.schedule = schedule
        self.service = service
        self.active_count = active_count
        self.booking = None

    async def get_schedule_for_update(self, schedule_id):
        assert schedule_id == self.schedule.id
        return self.schedule

    async def get_service(self, service_id):
        assert service_id == self.service.id
        return self.service

    async def get_doctor(self, doctor_id):
        assert doctor_id == self.schedule.doctor_id
        return SimpleNamespace(
            id=doctor_id,
            status="active",
            review_status="approved",
            booking_enabled=True,
        )

    async def get_facility(self, facility_id):
        assert facility_id == self.schedule.facility_id
        return SimpleNamespace(id=facility_id, status="active")

    async def get_specialty(self, specialty_id):
        return SimpleNamespace(id=specialty_id, status="active")

    async def has_doctor_service(self, doctor_id, service_id):
        return doctor_id == self.schedule.doctor_id and service_id == self.service.id

    async def has_doctor_specialty(self, doctor_id, specialty_id):
        return doctor_id == self.schedule.doctor_id

    async def has_doctor_facility(self, doctor_id, facility_id):
        return doctor_id == self.schedule.doctor_id and facility_id == self.schedule.facility_id

    async def count_active_for_schedule(self, schedule_id):
        assert schedule_id == self.schedule.id
        return self.active_count

    async def add(self, booking):
        self.booking = booking

    async def get_for_user(self, booking_id, user_id, *, for_update=False):
        del booking_id, user_id, for_update
        return self.booking


def create_request(schedule, service):
    return BookingCreate(
        schedule_id=schedule.id,
        service_id=service.id,
        specialty_id=uuid4(),
        reason="Annual check-up",
    )


def test_group_booking_enters_staff_review_queue():
    """A group booking consumes capacity while awaiting staff review."""
    schedule = make_schedule(capacity=2)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=1)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository

    booking = asyncio.run(booking_service.create(uuid4(), create_request(schedule, service)))

    assert isinstance(booking, Booking)
    assert repository.booking.status == "pending_approval"


def test_group_booking_rejects_when_shared_capacity_is_full():
    """A group service cannot exceed the schedule capacity."""
    schedule = make_schedule(capacity=2)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=2)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository

    with pytest.raises(ConflictError, match="no remaining capacity"):
        asyncio.run(booking_service.create(uuid4(), create_request(schedule, service)))


def test_doctor_visit_allows_only_one_booking_per_schedule():
    """A doctor visit is exclusive even when the schedule capacity is larger."""
    schedule = make_schedule(capacity=5)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="doctor_visit")
    repository = FakeBookingRepository(schedule, service, active_count=1)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository

    with pytest.raises(ConflictError, match="already booked"):
        asyncio.run(booking_service.create(uuid4(), create_request(schedule, service)))


def test_requested_time_booking_does_not_require_published_schedule():
    """A patient can submit a requested time for staff to review and schedule."""
    schedule = make_schedule(capacity=0)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=0)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository
    starts_at = schedule.starts_at + timedelta(days=1)
    request = BookingCreate(
        doctor_id=schedule.doctor_id,
        facility_id=schedule.facility_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        service_id=service.id,
        specialty_id=uuid4(),
        reason="Requested consultation",
    )

    booking = asyncio.run(booking_service.create(uuid4(), request))

    assert booking.schedule_id is None
    assert booking.starts_at == starts_at
    assert repository.booking.status == "pending_approval"


def test_booking_request_normalizes_timezone_to_utc():
    """Requested times are normalized before business-rule validation."""
    local_start = datetime(2030, 1, 1, 9, 0, tzinfo=timezone(timedelta(hours=7)))
    request = BookingCreate(
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=local_start,
        ends_at=local_start + timedelta(minutes=30),
        service_id=uuid4(),
        specialty_id=uuid4(),
        reason="Timezone check",
    )

    assert request.starts_at == datetime(2030, 1, 1, 2, 0, tzinfo=UTC)
    assert request.starts_at.tzinfo == UTC


def test_booking_request_rejects_naive_requested_time():
    """Naive timestamps are rejected instead of being guessed as local time."""
    naive_start = datetime(2030, 1, 1, 9, 0)

    with pytest.raises(ValueError, match="timezone offset"):
        BookingCreate(
            doctor_id=uuid4(),
            facility_id=uuid4(),
            starts_at=naive_start,
            ends_at=naive_start + timedelta(minutes=30),
            service_id=uuid4(),
            specialty_id=uuid4(),
            reason="Timezone check",
        )
