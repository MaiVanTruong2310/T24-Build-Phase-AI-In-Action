"""Unit tests for the Supabase-backed profile service without a database.

Supabase Auth owns credentials, email confirmation and sessions. ``AuthService``
only reads and writes the application profile in ``public.users``, so these tests
exercise ``get_user_by_id``, ``update_profile`` and ``update_portrait`` against
lightweight in-memory fakes.
"""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, NotFoundError
from src.models.user import User
from src.schemas.auth import UpdateProfileRequest
from src.services.auth import AuthService


class FakeTransaction:
    """Minimal async transaction context used by service unit tests."""

    async def __aenter__(self) -> "FakeTransaction":
        """Enter the fake transaction."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Leave the fake transaction without committing external state."""


class FakeSession:
    """Minimal async session surface required by AuthService."""

    def __init__(self, *, refreshed_details: dict | None = None, flush_error: Exception | None = None) -> None:
        self.executed: list[object] = []
        self.flush_count = 0
        self.refresh_count = 0
        self.refreshed_details = refreshed_details
        self.flush_error = flush_error

    async def execute(self, statement):
        """Accept the per-row lock used when applying profile updates."""
        self.executed.append(statement)
        return None

    def begin(self) -> FakeTransaction:
        """Return a fake transaction context manager."""
        return FakeTransaction()

    async def flush(self) -> None:
        """Count flushes, or fail like the database would on a unique violation."""
        self.flush_count += 1
        if self.flush_error is not None:
            raise self.flush_error

    async def refresh(self, instance, attribute_names=None) -> None:
        """Simulate reloading a column from the database."""
        del attribute_names
        self.refresh_count += 1
        if self.refreshed_details is not None:
            instance.patient_details = self.refreshed_details


class FakeUserRepository:
    """In-memory user repository for isolated service tests."""

    def __init__(self, users: list[User] | None = None) -> None:
        self.users: list[User] = list(users or [])

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find a user by its identifier."""
        return next((user for user in self.users if user.id == user_id), None)

    async def get_by_citizen_id(self, citizen_id: str | None) -> User | None:
        """Find a user by citizen identifier."""
        if not citizen_id:
            return None
        return next((user for user in self.users if user.citizen_id == citizen_id), None)

    async def get_by_health_insurance_code(self, health_insurance_code: str | None) -> User | None:
        """Find a user by health-insurance card number."""
        if not health_insurance_code:
            return None
        return next((user for user in self.users if user.health_insurance_code == health_insurance_code), None)


def build_service(
    users: list[User] | None = None,
    session: FakeSession | None = None,
) -> tuple[AuthService, FakeUserRepository, FakeSession]:
    """Build an AuthService wired to in-memory dependencies."""
    session = session or FakeSession()
    service = AuthService(session)
    repository = FakeUserRepository(users)
    service.users = repository
    return service, repository, session


def test_get_user_by_id_returns_the_stored_profile():
    """Staff lookup flows return the persisted profile."""
    user = User(id=uuid4(), email="patient@example.com", role="patient", status="active")
    service, _, _ = build_service([user])

    assert asyncio.run(service.get_user_by_id(user.id)) is user


def test_get_user_by_id_raises_not_found_for_unknown_identifier():
    """Unknown identifiers surface the public not-found error."""
    service, _, _ = build_service()

    with pytest.raises(NotFoundError) as error:
        asyncio.run(service.get_user_by_id(uuid4()))

    assert error.value.code == "NOT_FOUND"


def test_update_profile_changes_only_patient_editable_fields():
    """Profile update persists the supplied demographic and insurance fields."""
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active")
    service, _, session = build_service([user])

    updated = asyncio.run(
        service.update_profile(
            user,
            UpdateProfileRequest(
                full_name="  Nguyen Van A ",
                phone="0900000000",
                gender="male",
                citizen_id="012345678901",
                health_insurance_code="BH1234567890",
            ),
        )
    )

    assert updated is user
    assert updated.full_name == "Nguyen Van A"
    assert updated.phone == "0900000000"
    assert updated.gender == "male"
    assert updated.citizen_id == "012345678901"
    assert updated.health_insurance_code == "BH1234567890"
    assert updated.role == "patient"
    assert session.flush_count == 1


def test_update_profile_leaves_unsupplied_fields_untouched():
    """A partial update never clears saved values that were not sent."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        full_name="Saved Name",
        phone="0900000001",
        role="patient",
        status="active",
    )
    service, _, _ = build_service([user])

    asyncio.run(service.update_profile(user, UpdateProfileRequest(gender="female")))

    assert user.full_name == "Saved Name"
    assert user.phone == "0900000001"
    assert user.gender == "female"


def test_update_profile_clears_a_whitespace_only_full_name():
    """A blank name is normalised to no name instead of an empty string."""
    user = User(id=uuid4(), email="user@example.com", full_name="Saved Name", role="patient", status="active")
    service, _, _ = build_service([user])

    asyncio.run(service.update_profile(user, UpdateProfileRequest(full_name="   ")))

    assert user.full_name is None


def test_update_profile_merges_patient_details_with_saved_values():
    """A partial patient_details payload preserves the other saved details."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        role="patient",
        status="active",
        patient_details={"blood_type": "O+", "emergency_name": "Contact Test"},
    )
    service, _, _ = build_service([user])

    asyncio.run(service.update_profile(user, UpdateProfileRequest(patient_details={"allergies": "Pollen"})))

    assert user.patient_details == {
        "blood_type": "O+",
        "emergency_name": "Contact Test",
        "allergies": "Pollen",
    }


def test_update_profile_merges_against_details_reloaded_from_database():
    """The merge uses the freshly locked row, not a stale in-memory copy."""
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active", patient_details={"stale": True})
    session = FakeSession(refreshed_details={"blood_type": "O+"})
    service, _, _ = build_service([user], session)

    asyncio.run(service.update_profile(user, UpdateProfileRequest(patient_details={"allergies": "Pollen"})))

    assert user.patient_details == {"blood_type": "O+", "allergies": "Pollen"}


def test_update_profile_rejects_citizen_id_owned_by_another_profile():
    """A citizen_id that belongs to somebody else is refused and not applied."""
    other = User(id=uuid4(), email="other@example.com", role="patient", status="active", citizen_id="012345678901")
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active")
    service, _, session = build_service([user, other])

    with pytest.raises(ConflictError) as error:
        asyncio.run(service.update_profile(user, UpdateProfileRequest(citizen_id="012345678901")))

    assert error.value.code == "CITIZEN_ID_EXISTS"
    assert user.citizen_id is None
    assert session.flush_count == 0


def test_update_profile_allows_resubmitting_the_same_citizen_id():
    """A profile may keep re-submitting its own citizen_id."""
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active", citizen_id="012345678901")
    service, _, session = build_service([user])

    asyncio.run(service.update_profile(user, UpdateProfileRequest(citizen_id="012345678901")))

    assert user.citizen_id == "012345678901"
    assert session.flush_count == 1


def test_update_profile_rejects_health_insurance_owned_by_another_profile():
    """A health-insurance number that belongs to somebody else is refused."""
    other = User(
        id=uuid4(),
        email="other@example.com",
        role="patient",
        status="active",
        health_insurance_code="BH1234567890",
    )
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active")
    service, _, session = build_service([user, other])

    with pytest.raises(ConflictError) as error:
        asyncio.run(service.update_profile(user, UpdateProfileRequest(health_insurance_code="BH1234567890")))

    assert error.value.code == "HEALTH_INSURANCE_EXISTS"
    assert user.health_insurance_code is None
    assert session.flush_count == 0


def test_update_profile_converts_integrity_error_to_public_conflict():
    """A database uniqueness violation becomes the stable public conflict error."""
    user = User(id=uuid4(), email="user@example.com", role="patient", status="active")
    session = FakeSession(flush_error=IntegrityError("UPDATE", {}, Exception("duplicate key value")))
    service, _, _ = build_service([user], session)

    with pytest.raises(ConflictError) as error:
        asyncio.run(service.update_profile(user, UpdateProfileRequest(phone="0900000000")))

    assert error.value.code == "PROFILE_CONFLICT"
    assert error.value.status_code == 409


def test_update_portrait_stores_the_image_and_keeps_other_details():
    """Portrait updates live inside patient_details and preserve the rest."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        role="patient",
        status="active",
        patient_details={"blood_type": "O+", "portrait_image": "data:image/jpeg;base64,old"},
    )
    service, _, session = build_service([user])

    asyncio.run(service.update_portrait(user, "data:image/jpeg;base64,new"))

    assert user.patient_details == {"blood_type": "O+", "portrait_image": "data:image/jpeg;base64,new"}
    assert session.refresh_count == 1
    assert session.flush_count == 1


def test_update_portrait_removes_the_image_when_none():
    """Clearing the portrait removes only the portrait key."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        role="patient",
        status="active",
        patient_details={"blood_type": "O+", "portrait_image": "data:image/jpeg;base64,old"},
    )
    service, _, session = build_service([user])

    asyncio.run(service.update_portrait(user, None))

    assert user.patient_details == {"blood_type": "O+"}
    assert session.flush_count == 1
