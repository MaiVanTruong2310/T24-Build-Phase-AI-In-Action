"""Validation at chatbot booking boundaries, including direct API callers."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.api.endpoints.package import PackageRequestInput, create_package_request
from src.core.exceptions import ConflictError
from src.services.workbench import intake


def doctor_request(**overrides):
    values = {
        "patient_name": "Nguyễn Văn A",
        "patient_phone": "0912345678",
        "date_of_birth": date(1990, 1, 1),
        "preferred_date": date.today() + timedelta(days=1),
        "guardian_name": None,
        "guardian_phone": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"preferred_date": None},
        {"preferred_date": date(2000, 1, 1)},
        {"patient_name": "  "},
        {"date_of_birth": date(2100, 1, 1)},
        {"date_of_birth": date.today() - timedelta(days=10 * 365)},
        {
            "date_of_birth": date.today() - timedelta(days=10 * 365),
            "guardian_name": " ",
            "guardian_phone": "0912345678",
        },
    ],
)
async def test_doctor_intake_rejects_invalid_data_before_persistence(changes):
    with pytest.raises(HTTPException) as caught:
        await intake(None, doctor_request(**changes), None, None, {})
    assert caught.value.status_code == 422


class NoDatabaseWrites:
    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"consent_to_contact": False},
        {"patient_phone": "123456789"},
        {"date_of_birth": date(2100, 1, 1)},
        {"date_of_birth": date.today() - timedelta(days=10 * 365)},
        {
            "date_of_birth": date.today() - timedelta(days=10 * 365),
            "guardian_name": " ",
            "guardian_phone": "0912345678",
        },
        {"preferred_date": date(2000, 1, 1)},
    ],
)
async def test_package_intake_rejects_invalid_data_before_persistence(changes):
    from uuid import uuid4

    values = {
        "service_id": uuid4(),
        "facility_id": uuid4(),
        "preferred_date": date.today() + timedelta(days=1),
        "patient_name": "Nguyễn Văn A",
        "patient_phone": "0912345678",
        "date_of_birth": date(1990, 1, 1),
        "gender": "male",
        "consent_to_contact": True,
    }
    values.update(changes)
    with pytest.raises(ConflictError):
        await create_package_request(PackageRequestInput(**values), None, None, NoDatabaseWrites())


@pytest.mark.asyncio
async def test_package_request_keeps_edited_patient_contact(monkeypatch):
    from uuid import uuid4

    import src.services.workbench as workbench
    from src.models.facility import Facility
    from src.models.service import Service

    service_id, facility_id = uuid4(), uuid4()

    class RecordingDatabase(NoDatabaseWrites):
        saved = None

        async def get(self, model, key):
            if model is Service:
                return SimpleNamespace(id=service_id, status="active", name="Gói khám", price=None)
            if model is Facility:
                return SimpleNamespace(id=facility_id, status="active", name="Cơ sở")
            raise AssertionError(model)

        def add(self, item):
            self.saved = item

        async def flush(self):
            if self.saved.id is None:
                self.saved.id = uuid4()

    async def fake_source_case(*args):
        return None

    monkeypatch.setattr(workbench, "create_source_case", fake_source_case)
    db = RecordingDatabase()
    user = SimpleNamespace(
        id=uuid4(),
        full_name="Tên tài khoản",
        phone="0912345678",
        email=None,
        gender="male",
        date_of_birth=date(1990, 1, 1),
    )
    payload = PackageRequestInput(
        service_id=service_id,
        facility_id=facility_id,
        preferred_date=date.today() + timedelta(days=1),
        patient_name="Người được khám",
        patient_phone="0987654321",
        gender="female",
        date_of_birth=date(1995, 1, 1),
        consent_to_contact=True,
    )
    request = SimpleNamespace(state=SimpleNamespace(coordination_guest=None))
    await create_package_request(payload, request, user, db)
    assert db.saved.patient_name == "Người được khám"
    assert db.saved.patient_phone == "0987654321"
    assert db.saved.gender == "female"
    assert db.saved.date_of_birth == date(1995, 1, 1)
