from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.medical_assistant.domain.booking_request_service import BookingRequestService


class RecordingClient:
    def __init__(self):
        self.table = None
        self.payload = None

    def insert_minimal(self, table, payload):
        self.table = table
        self.payload = payload


def intake(**overrides):
    values = {
        "session_id": "sess-booking-test",
        "patient_name": "Nguyễn Văn A",
        "patient_phone": "0912345678",
        "patient_email": None,
        "date_of_birth": date(1990, 1, 1),
        "gender": None,
        "guardian_name": None,
        "guardian_phone": None,
        "preferred_date": None,
        "preferred_period": "any",
        "facility_preference": None,
        "contact_time_preference": None,
        "patient_notes": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_guest_request_is_written_as_pending_contact_without_fake_confirmation():
    client = RecordingClient()
    result = BookingRequestService(client=client).submit(
        intake(),
        {
            "specialty_code": "TIEU_HOA",
            "specialty_name": "Tiêu hóa - Gan mật",
            "doctor_id": "crawl-51797",
            "doctor_name": "Bùi Minh Thanh",
            "schedule_id": None,
            "symptoms_summary": "đau bụng bên trái",
        },
    )

    assert client.table == "booking_requests"
    assert client.payload["status"] == "PENDING_CONTACT"
    assert client.payload["doctor_id"] is None
    assert client.payload["preferred_doctor_name"] == "Bùi Minh Thanh"
    assert client.payload["schedule_id"] is None
    assert result["request_code"].startswith("YC-")


def test_minor_requires_guardian_contact():
    minor_birth_date = date.today() - timedelta(days=17 * 365)
    with pytest.raises(ValueError, match="người giám hộ"):
        BookingRequestService(client=RecordingClient()).submit(
            intake(date_of_birth=minor_birth_date),
            {"specialty_name": "Tiêu hóa - Gan mật"},
        )
