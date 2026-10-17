"""Doctor response mapping tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.api.endpoints.doctor import _doctor_response


def test_doctor_response_includes_resolved_catalog_resources():
    """Doctor responses expose full specialty, facility, and service data."""
    specialty = SimpleNamespace(
        id=uuid4(),
        code="CARDIOLOGY",
        name="Cardiology",
        description="Heart care",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    facility = SimpleNamespace(
        id=uuid4(),
        code="CENTRAL",
        name="Central Clinic",
        description=None,
        address="1 Main Street",
        phone="0900000000",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    service = SimpleNamespace(
        id=uuid4(),
        code="CONSULT",
        name="Specialist consultation",
        description="Consultation",
        duration_minutes=30,
        price=350000,
        original_price=None,
        category="consultation",
        booking_mode="doctor_visit",
        features=[],
        patient_count=0,
        satisfaction_rate=5.0,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    doctor = SimpleNamespace(
        id=uuid4(),
        code="DOC-001",
        full_name="Doctor One",
        bio=None,
        status="active",
        review_status="approved",
        booking_enabled=True,
        avatar_url=None,
        title="Specialist",
        specialties=[SimpleNamespace(specialty_id=specialty.id, is_primary=True, specialty=specialty)],
        facilities=[
            SimpleNamespace(
                facility_id=facility.id,
                department="Cardiology",
                room="A-01",
                active_from=None,
                active_to=None,
                facility=facility,
            )
        ],
        services=[SimpleNamespace(service_id=service.id, active=True, service=service)],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    response = _doctor_response(doctor)

    assert response.specialties[0].specialty is not None
    assert response.specialties[0].specialty.code == "CARDIOLOGY"
    assert response.facilities[0].facility is not None
    assert response.facilities[0].facility.code == "CENTRAL"
    assert response.services[0].service is not None
    assert response.services[0].service.code == "CONSULT"


def test_public_doctor_response_excludes_inactive_assignments():
    """Public doctor responses do not expose inactive assigned resources."""
    now = datetime.now(UTC)
    active_specialty = SimpleNamespace(
        id=uuid4(),
        code="ACTIVE",
        name="Active",
        description=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    inactive_specialty = SimpleNamespace(
        id=uuid4(),
        code="INACTIVE",
        name="Inactive",
        description=None,
        status="inactive",
        created_at=now,
        updated_at=now,
    )
    doctor = SimpleNamespace(
        id=uuid4(),
        code="DOC-002",
        full_name="Doctor Two",
        bio=None,
        status="active",
        review_status="approved",
        booking_enabled=True,
        avatar_url=None,
        title=None,
        specialties=[
            SimpleNamespace(specialty_id=active_specialty.id, is_primary=True, specialty=active_specialty),
            SimpleNamespace(specialty_id=inactive_specialty.id, is_primary=False, specialty=inactive_specialty),
        ],
        facilities=[],
        services=[],
        created_at=now,
        updated_at=now,
    )

    response = _doctor_response(doctor, public_only=True)

    assert response.specialty_ids == [active_specialty.id]
    assert len(response.specialties) == 1
