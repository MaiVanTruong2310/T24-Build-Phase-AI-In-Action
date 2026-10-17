"""Persist guest booking requests for human-in-the-loop follow-up."""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any

from src.medical_assistant.db.supabase_client import get_supabase_admin_client

PHONE_PATTERN = re.compile(r"^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$")


class BookingPersistenceError(RuntimeError):
    """Raised when a request was not durably written to the HITL queue."""


def _is_minor(date_of_birth: date, today: date | None = None) -> bool:
    today = today or date.today()
    try:
        eighteenth_birthday = date_of_birth.replace(year=date_of_birth.year + 18)
    except ValueError:  # 29 February in a non-leap eighteenth year.
        eighteenth_birthday = date(date_of_birth.year + 18, 2, 28)
    return eighteenth_birthday > today


def _uuid_or_none(value: Any) -> str | None:
    try:
        return str(uuid.UUID(str(value))) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


class BookingRequestService:
    def __init__(self, client: Any | None = None):
        try:
            self.client = client or get_supabase_admin_client()
        except ValueError as exc:
            raise BookingPersistenceError(
                "Backend chưa được cấu hình khóa ghi Supabase dành riêng cho máy chủ."
            ) from exc

    def submit(self, intake: Any, context: dict[str, Any]) -> dict[str, str]:
        phone = re.sub(r"[\s.()-]", "", intake.patient_phone)
        guardian_phone = re.sub(r"[\s.()-]", "", intake.guardian_phone or "") or None
        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Số điện thoại chưa đúng định dạng Việt Nam.")
        if intake.date_of_birth > date.today():
            raise ValueError("Ngày sinh không thể nằm trong tương lai.")
        if _is_minor(intake.date_of_birth):
            if not (intake.guardian_name and guardian_phone and PHONE_PATTERN.fullmatch(guardian_phone)):
                raise ValueError("Người dưới 18 tuổi cần họ tên và số điện thoại người giám hộ.")

        request_id = str(uuid.uuid4())
        request_code = f"YC-{request_id.split('-')[0].upper()}"
        payload = {
            "id": request_id,
            "request_code": request_code,
            "session_id": intake.session_id,
            "auth_user_id": _uuid_or_none(context.get("user_id")),
            "patient_name": intake.patient_name.strip(),
            "patient_phone": phone,
            "patient_email": str(intake.patient_email or "").strip() or None,
            "date_of_birth": intake.date_of_birth.isoformat(),
            "gender": intake.gender,
            "guardian_name": str(intake.guardian_name or "").strip() or None,
            "guardian_phone": guardian_phone,
            "specialty_code": context.get("specialty_code"),
            "specialty_name": context.get("specialty_name") or "Chuyên khoa phù hợp",
            "doctor_id": _uuid_or_none(context.get("doctor_id")),
            "preferred_doctor_name": context.get("doctor_name"),
            "schedule_id": _uuid_or_none(context.get("schedule_id")),
            "preferred_date": intake.preferred_date.isoformat() if intake.preferred_date else None,
            "preferred_period": intake.preferred_period,
            "facility_preference": str(intake.facility_preference or "").strip() or None,
            "contact_time_preference": str(intake.contact_time_preference or "").strip() or None,
            "symptoms_summary": context.get("symptoms_summary"),
            "patient_notes": str(intake.patient_notes or "").strip() or None,
            "consent_to_contact": True,
            "status": "PENDING_CONTACT",
            "source": "chatbot_guest" if not context.get("user_id") else "chatbot_authenticated",
        }
        try:
            self.client.insert_minimal("booking_requests", payload)
        except Exception as exc:
            raise BookingPersistenceError("Không thể lưu yêu cầu vào hàng đợi điều phối.") from exc
        return {"request_id": request_id, "request_code": request_code, "status": "PENDING_CONTACT"}
