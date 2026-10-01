"""Booking capacity and ownership business-rule tests."""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.core.exceptions import ConflictError
from src.models.booking import Booking
from src.schemas.booking import BookingCreate, BookingRescheduleCreate, StaffBookingStatusUpdate
from src.services.booking import BookingService
from src.services.notification import NotificationService


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


class FakeSession:
    def __init__(self):
        self.added = []

    def begin(self):
        return FakeTransaction()

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def execute(self, _statement):
        return FakeResult()


class FakeResult:
    rowcount = 0

    def scalars(self):
        return self

    def all(self):
        return []

    def scalar_one_or_none(self):
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
        self.staff_booking = None
        self.expired_bookings = []

    async def get_schedule_for_update(self, schedule_id):
        assert schedule_id == self.schedule.id
        return self.schedule

    async def get_schedules_for_update(self, schedule_ids):
        return {schedule_id: self.schedule for schedule_id in schedule_ids}

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

    async def count_reservations_for_schedule(self, schedule_id, *, exclude_booking_id=None):
        del schedule_id, exclude_booking_id
        return self.active_count

    async def get_booking_by_idempotency(self, user_id, key):
        if self.booking and self.booking.user_id == user_id and self.booking.idempotency_key == key:
            return self.booking
        return None

    async def get_for_staff(self, booking_id, *, for_update=False):
        del booking_id, for_update
        return self.staff_booking

    async def claim_expired_pending_bookings(self, now, limit):
        del now
        return self.expired_bookings[:limit]

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
    assert repository.booking.expired_at > datetime.now(UTC) + timedelta(hours=23)


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


def test_booking_reserves_capacity_and_idempotent_retry_replays_same_booking():
    """A pending booking reserves capacity and duplicate submits replay it."""
    schedule = make_schedule(capacity=1)
    schedule.starts_at = datetime.now(UTC) + timedelta(days=1)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=0)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository
    user_id = uuid4()
    request = BookingCreate(
        schedule_id=schedule.id,
        service_id=service.id,
        specialty_id=uuid4(),
        reason="Pending consultation",
    )

    first, replayed_first = asyncio.run(booking_service.create_idempotent(user_id, request, "booking-1"))
    second, replayed_second = asyncio.run(booking_service.create_idempotent(user_id, request, "booking-1"))

    assert replayed_first is False
    assert replayed_second is True
    assert first.id == second.id
    assert first.status == "pending_approval"


def test_idempotency_key_rejects_a_different_retry_payload():
    """A key cannot be reused to create a different booking request."""
    schedule = make_schedule(capacity=1)
    schedule.starts_at = datetime.now(UTC) + timedelta(days=1)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=0)
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository
    user_id = uuid4()
    first_request = create_request(schedule, service)

    asyncio.run(booking_service.create_idempotent(user_id, first_request, "booking-1"))

    changed_request = first_request.model_copy(update={"reason": "Different consultation"})
    with pytest.raises(ConflictError, match="different request"):
        asyncio.run(booking_service.create_idempotent(user_id, changed_request, "booking-1"))


def test_staff_approval_rechecks_capacity_before_confirmation():
    """Approval must reject a slot consumed by another reservation after submission."""
    schedule = make_schedule(capacity=1)
    schedule.starts_at = datetime.now(UTC) + timedelta(days=1)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=1)
    repository.staff_booking = SimpleNamespace(
        id=uuid4(),
        status="pending_approval",
        expired_at=datetime.now(UTC) + timedelta(hours=1),
        schedule_id=schedule.id,
        service=service,
        staff_note=None,
        reviewed_by=None,
        reviewed_at=None,
    )
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository

    with pytest.raises(ConflictError, match="no remaining capacity"):
        asyncio.run(
            booking_service.review(
                repository.staff_booking.id,
                uuid4(),
                StaffBookingStatusUpdate(status="confirmed"),
            )
        )

    assert repository.staff_booking.status == "pending_approval"


def test_confirmed_review_creates_patient_in_app_and_email_notifications():
    """A confirmed booking produces one notification per patient channel."""
    session = FakeSession()
    notification_service = NotificationService(session)
    booking = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        starts_at=datetime.now(UTC) + timedelta(days=2),
        staff_note=None,
    )

    asyncio.run(notification_service.create_for_booking_review(booking, "confirmed"))

    assert [item.kind for item in session.added] == ["booking_confirmed", "booking_confirmed"]
    assert all(item.user_id == booking.user_id for item in session.added)
    assert [item.channel for item in session.added] == ["in_app", "email"]
    assert all(item.status == "pending" for item in session.added)


def test_expired_pending_booking_releases_capacity_and_notifies_patient():
    """The periodic expiry transition is idempotent and creates both channels."""
    session = FakeSession()
    repository = FakeBookingRepository(make_schedule(), SimpleNamespace(id=uuid4()), active_count=0)
    booking = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        status="pending_approval",
        expired_at=datetime.now(UTC) - timedelta(minutes=1),
        staff_note=None,
    )
    repository.expired_bookings = [booking]
    service = BookingService(session)
    service.bookings = repository

    assert asyncio.run(service.expire_pending_bookings()) == 1
    assert booking.status == "expired"
    assert [item.channel for item in session.added] == ["in_app", "email"]


def test_confirmed_booking_in_reminder_window_gets_two_deduplicated_channels():
    """The cron scan creates the two-day reminder exactly once per channel."""
    session = FakeSession()
    booking = SimpleNamespace(id=uuid4(), user_id=uuid4(), starts_at=datetime.now(UTC) + timedelta(days=1))
    notification_service = NotificationService(session)

    async def candidates(_now, _deadline, _limit):
        return [booking]

    notification_service.bookings = SimpleNamespace(list_confirmed_reminder_candidates=candidates)

    assert asyncio.run(notification_service.create_due_reminders()) == 1
    assert [item.kind for item in session.added] == ["appointment_reminder", "appointment_reminder"]
    assert [item.channel for item in session.added] == ["in_app", "email"]
    assert len({item.dedupe_key for item in session.added}) == 2


def test_reschedule_releases_old_slot_and_records_audit_event():
    """Rescheduling moves the booking back to approval without a hold."""
    schedule = make_schedule(capacity=2)
    schedule.starts_at = datetime.now(UTC) + timedelta(days=3)
    service = SimpleNamespace(id=uuid4(), status="active", booking_mode="group")
    repository = FakeBookingRepository(schedule, service, active_count=0)
    old_schedule_id = uuid4()
    booking_id = uuid4()
    patient_id = uuid4()
    specialty_id = uuid4()
    repository.booking = SimpleNamespace(
        id=booking_id,
        user_id=patient_id,
        status="confirmed",
        schedule_id=old_schedule_id,
        doctor_id=uuid4(),
        facility_id=uuid4(),
        starts_at=datetime.now(UTC) + timedelta(days=1),
        ends_at=datetime.now(UTC) + timedelta(days=1, minutes=30),
        service_id=service.id,
        specialty_id=specialty_id,
        service=service,
        specialty=SimpleNamespace(id=specialty_id),
        staff_note="previous note",
        reviewed_by=uuid4(),
        reviewed_at=datetime.now(UTC),
    )
    booking_service = BookingService(FakeSession())
    booking_service.bookings = repository

    result = asyncio.run(
        booking_service.reschedule(
            patient_id,
            booking_id,
            BookingRescheduleCreate(schedule_id=schedule.id),
        )
    )

    assert result is repository.booking
    assert result.status == "pending_approval"
    assert result.schedule_id == schedule.id
    assert any(event.action == "rescheduled" for event in booking_service.session.added)
