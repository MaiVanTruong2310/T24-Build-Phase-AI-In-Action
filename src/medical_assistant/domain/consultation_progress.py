"""Thanh tiến trình 4 bước cho người bệnh: kể triệu chứng → làm rõ → gợi ý chuyên khoa → đặt lịch.

Tóm tắt chỉ dựng từ dữ kiện có cấu trúc trong state (luật trích xuất, khoa đã định tuyến, phiếu đặt lịch),
không lấy từ chữ LLM viết và không bao giờ nêu tên bệnh — chỉ nhắc lại triệu chứng người bệnh kể và tên khoa.
"""

from typing import Any

from src.medical_assistant.domain.booking_slot_service import slot_label

COMPLAINT_LABELS = {
    "headache": ("Đau đầu", "Headache"),
    "dizziness": ("Chóng mặt", "Dizziness"),
    "abdominal_pain": ("Đau bụng", "Abdominal pain"),
    "constipation": ("Táo bón", "Constipation"),
    "sore_throat": ("Đau họng", "Sore throat"),
    "chest_pain": ("Đau ngực", "Chest pain"),
    "shortness_of_breath": ("Khó thở", "Shortness of breath"),
    "cough": ("Ho", "Cough"),
    "fever": ("Sốt", "Fever"),
    "back_pain": ("Đau lưng", "Back pain"),
    "joint_pain": ("Đau khớp", "Joint pain"),
    "neck_shoulder_pain": ("Đau cổ, vai gáy", "Neck and shoulder pain"),
    "muscle_pain": ("Đau cơ", "Muscle pain"),
    "eye_symptoms": ("Khó chịu ở mắt", "Eye symptoms"),
    "ear_nose_symptoms": ("Khó chịu ở tai, mũi", "Ear or nose symptoms"),
    "dental_pain": ("Đau răng", "Toothache"),
    "palpitations": ("Hồi hộp, tim đập nhanh", "Palpitations"),
    "hoarseness": ("Khàn tiếng", "Hoarseness"),
    "mouth_ulcer": ("Nhiệt miệng", "Mouth ulcers"),
    "anorectal_symptoms": ("Khó chịu vùng hậu môn", "Anorectal symptoms"),
    "skin_lesion": ("Nổi mẩn, ngứa da", "Skin rash or itching"),
    "hair_loss": ("Rụng tóc", "Hair loss"),
    "insomnia": ("Mất ngủ", "Insomnia"),
    "urinary_symptoms": ("Khó chịu khi tiểu tiện", "Urinary symptoms"),
    "gynecologic_symptoms": ("Khó chịu vùng kín", "Intimate area symptoms"),
}

STEP_LABELS = {
    "symptom": ("Kể triệu chứng", "Describe symptoms"),
    "details": ("Làm rõ thêm", "A few details"),
    "specialty": ("Gợi ý chuyên khoa", "Suggested specialty"),
    "booking": ("Đặt lịch", "Book a visit"),
}

# Đã qua vòng hỏi thêm, đã có khoa định hướng.
TRIAGED_STATUSES = {
    "TRIAGED_AWAITING_SCHEDULE",
    "TRIAGED_READY_FOR_BOOKING",
    "DOCTOR_CHOICE_REQUIRED",
    "BOOKING_CONTACT_REQUIRED",
    "CONFIRM_BOOKING_CONVERSATIONALLY",
    "FACILITY_BOOKING_START",
    "FACILITY_CHOICE_REQUIRED",
    "SLOT_CHOICE_REQUIRED",
}
BOOKING_STATUSES = TRIAGED_STATUSES - {"TRIAGED_AWAITING_SCHEDULE"}
PERIOD_LABELS = {"morning": ("buổi sáng", "morning"), "afternoon": ("buổi chiều", "afternoon")}


def _vi(language: str) -> int:
    return 0 if language != "en" else 1


def _symptom_summary(facts: dict[str, Any], details: list[str], language: str) -> str | None:
    codes = list(facts.get("active_complaint_codes") or [])
    if facts.get("chief_complaint") and facts["chief_complaint"] not in codes:
        codes.insert(0, facts["chief_complaint"])
    labels = [COMPLAINT_LABELS[code][_vi(language)] for code in codes if code in COMPLAINT_LABELS][:2]
    if labels:
        summary = ", ".join(labels)
        location = facts.get("location")
        return f"{summary} ({location})" if location else summary
    if details:
        # Chưa nhận diện được triệu chứng chuẩn → nhắc lại đúng lời người bệnh, cắt gọn.
        text = details[0].strip()
        return f"“{text[:57]}…”" if len(text) > 60 else f"“{text}”"
    return None


def _details_summary(facts: dict[str, Any], language: str) -> str | None:
    parts: list[str] = []
    days = facts.get("duration_days")
    if isinstance(days, int | float) and days >= 0:
        if language == "en":
            parts.append("since today" if days == 0 else f"for {int(days)} day(s)")
        else:
            parts.append("mới hôm nay" if days == 0 else "từ hôm qua" if days == 1 else f"khoảng {int(days)} ngày nay")
    known = set(facts.get("positive_facts") or [])
    if "severe_abdominal_pain" in known:
        parts.append("pain is severe" if language == "en" else "đau nhiều")
    elif "mild_abdominal_pain" in known:
        parts.append("mild, dull pain" if language == "en" else "đau âm ỉ")
    return " · ".join(parts) or None


def _urgency_label(max_days: Any, language: str) -> str | None:
    if not isinstance(max_days, int) or max_days < 0:
        return None
    if language == "en":
        if max_days <= 1:
            return "see a doctor today"
        return "within the week" if max_days <= 7 else "when convenient"
    if max_days <= 1:
        return "nên khám trong ngày"
    if max_days <= 3:
        return f"nên khám trong {max_days} ngày tới"
    return "nên khám trong tuần" if max_days <= 7 else "khám khi thuận tiện"


def _booking_summary(intake: dict[str, Any], result: dict[str, Any], language: str) -> str | None:
    status = str(result.get("workflow_status") or "")
    facility = intake.get("facility_preference") or result.get("facility_preference") or result.get("facility_region")
    doctor = (result.get("chosen_doctor") or {}).get("full_name")
    parts = [facility, f"BS. {doctor}" if doctor else None]
    if result.get("chosen_slot"):
        parts.append(slot_label(result["chosen_slot"]))  # "08:30 sáng 16/10"
    else:
        date = str(intake.get("preferred_date") or "")
        parts.append(f"{date[8:10]}/{date[5:7]}" if len(date) == 10 else date or None)
        period = PERIOD_LABELS.get(str(intake.get("preferred_period") or ""))
        if period:
            parts.append(period[_vi(language)])
    if intake.get("request_code") or intake.get("confirmed"):
        parts.append("waiting for confirmation" if language == "en" else "chờ điều phối viên xác nhận")
    elif status == "BOOKING_CONTACT_REQUIRED":
        parts.append("contact details needed" if language == "en" else "cần thông tin liên hệ")
    elif status == "FACILITY_CHOICE_REQUIRED":
        parts.append("choosing a facility" if language == "en" else "đang chọn nơi khám")
    elif status == "TRIAGED_READY_FOR_BOOKING" and not doctor:
        parts.append("choosing a doctor" if language == "en" else "đang chọn bác sĩ")
    elif status == "SLOT_CHOICE_REQUIRED":
        parts.append("choosing a time" if language == "en" else "đang chọn giờ khám")
    return " · ".join(str(part) for part in parts if part) or None


def build_progress(result: dict[str, Any]) -> dict[str, Any]:
    """Trạng thái từng bước (done | current | todo | skipped) + tóm tắt ngắn cho người bệnh."""
    language = result.get("language") or "vi"
    facts = result.get("clinical_facts") or {}
    details = [str(item) for item in (result.get("collected_details") or []) if str(item).strip()]
    status = str(result.get("workflow_status") or "")
    intake = (result.get("metadata") or {}).get("booking_intake") or {}
    department = result.get("suggested_department_name")

    has_symptom = bool(facts.get("chief_complaint") or facts.get("active_complaint_codes") or details)
    # booking_intake luôn có sẵn để điền trước phiếu → chỉ tính là đã gửi khi có mã/đã xác nhận.
    booking_done = bool(intake.get("request_code") or intake.get("confirmed"))
    triaged = bool(department) and (status in TRIAGED_STATUSES or booking_done)
    booking_started = booking_done or status in BOOKING_STATUSES

    states = {
        "symptom": "done" if has_symptom else ("skipped" if triaged else "todo"),
        "details": "done" if has_symptom and triaged else ("skipped" if triaged else "todo"),
        "specialty": "done" if triaged else "todo",
        "booking": "done" if booking_done else "todo",
    }
    summaries = {
        "symptom": _symptom_summary(facts, details, language) if has_symptom else None,
        "details": _details_summary(facts, language) if has_symptom else None,
        "specialty": None,
        "booking": _booking_summary(intake, result, language) if booking_started else None,
    }
    if triaged:
        urgency = _urgency_label(result.get("max_booking_days"), language)
        summaries["specialty"] = f"{department} · {urgency}" if urgency else str(department)

    current = next((key for key, value in states.items() if value == "todo"), None)
    if current:
        states[current] = "current"
    steps = [
        {"key": key, "label": STEP_LABELS[key][_vi(language)], "status": states[key], "summary": summaries[key]}
        for key in STEP_LABELS
    ]
    return {
        "emergency": bool(result.get("is_emergency")),
        "current_step": (list(STEP_LABELS).index(current) + 1) if current else len(STEP_LABELS),
        "steps": steps,
    }
