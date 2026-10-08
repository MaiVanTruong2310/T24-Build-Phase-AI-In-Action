from datetime import date

from src.medical_assistant.domain.booking_slot_service import (
    build_booking_guidance_text,
    extract_booking_entities,
    extract_clinical_details,
    generate_clinical_summary,
    parse_vietnamese_date,
)


def test_parse_vietnamese_relative_dates():
    ref = date(2026, 10, 3)  # Saturday (Thứ 7)

    # "thứ 2 tuần sau"
    d1 = parse_vietnamese_date(
        "Tôi muốn đi khám vào thứ 2 tuần sau và vào buổi sáng, bạn lên lịch hẹn giúp tôi", reference_date=ref
    )
    assert d1 == date(2026, 10, 5), f"Expected 2026-10-05, got {d1}"

    # "thứ hai tuần tới"
    d2 = parse_vietnamese_date("thứ hai tuần tới", reference_date=ref)
    assert d2 == date(2026, 10, 5), f"Expected 2026-10-05, got {d2}"

    # "thứ 3" (upcoming Tuesday)
    d3 = parse_vietnamese_date("thứ 3", reference_date=ref)
    assert d3 == date(2026, 10, 6), f"Expected 2026-10-06, got {d3}"

    # "ngày mai"
    d4 = parse_vietnamese_date("ngày mai", reference_date=ref)
    assert d4 == date(2026, 10, 4), f"Expected 2026-10-04, got {d4}"


def test_extract_booking_entities_date_and_period():
    text = "Tôi muốn đi khám vào thứ 2 tuần sau và vào buổi sáng, bạn lên lịch hẹn giúp tôi"
    entities = extract_booking_entities(text)
    assert entities.get("preferred_period") == "morning"
    assert entities.get("preferred_date") is not None
    assert entities.get("is_booking_intent") is True


def test_clinical_details_does_not_confuse_weekday_with_duration():
    text_turn1 = "Chào bạn, tôi đang bị đau khớp ở đầu gối chân phải, hiện tại tôi đang gặp vấn đề về đi lại thì không biết có bệnh viện nào ở gần khu vực Long biên - Hà nội để tôi có thể đi khám không?"
    text_turn2 = "Tôi muốn đi khám vào thứ 2 tuần sau và vào buổi sáng, bạn lên lịch hẹn giúp tôi"

    details = extract_clinical_details(text=text_turn2, history_texts=[text_turn1])

    # Duration should NOT be "2 tuần nay" because user said "thứ 2 tuần sau"!
    assert "2 tuần nay" not in (details.get("duration") or "")
    assert details.get("location") in {"Khớp gối phải", "Khớp gối"}
    assert any("đi lại" in item.lower() for item in details.get("associated", []))

    summary = generate_clinical_summary({}, current_text=text_turn2)
    assert "diễn tiến 2 tuần nay" not in summary["summary"]


def test_build_booking_guidance_text_displays_all_fields():
    intake = {
        "patient_name": "Mai Văn Trường",
        "patient_phone": "0364335411",
        "date_of_birth": "2005-10-23",
        "specialty_name": "Chấn thương chỉnh hình & Cột sống",
        "facility_preference": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
        "preferred_date": "2026-10-05",
        "preferred_period": "morning",
        "doctor_name": "",
        "clinical_summary": "Bệnh nhân có triệu chứng đau nhức khớp (Khớp gối phải). Triệu chứng đi kèm: Hạn chế vận động, khó đi lại.",
    }

    response = build_booking_guidance_text(
        is_authenticated=True,
        missing_fields=[],
        current_intake=intake,
        specialty_name="Chấn thương chỉnh hình & Cột sống",
        lang="vi",
    )

    # Must list all fields in chat
    assert "Mai Văn Trường" in response
    assert "0364335411" in response
    assert "Chấn thương chỉnh hình & Cột sống" in response
    assert "Vinmec Riverside" in response
    assert "05/10/2026" in response
    assert "Buổi sáng" in response
    assert "Điều phối viên" in response
    assert "Khớp gối phải" in response or "đau nhức khớp" in response


def test_doctor_inquiry_does_not_extract_false_doctor_name():
    # User asks to choose / list doctors on that day
    query = "Tôi muốn tự chọn bác sĩ được không? Bạn giúp tôi liệt kê tên bác sĩ rảnh trong ngày đấy"
    entities = extract_booking_entities(query)

    # Must NOT extract "BS. Rảnh Trong"
    assert entities.get("doctor_name") is None
    assert entities.get("doctor_preference") != "Rảnh Trong"
    assert entities.get("is_doctor_inquiry") is True
    assert entities.get("doctor_inquiry") is True


def test_conversational_booking_confirmation():
    confirm_phrases = [
        "Tôi thấy lịch này ổn, đặt cho tôi",
        "Tôi xác nhận đặt lịch",
        "Đặt lịch đi",
        "Chốt lịch này giúp tôi",
        "Tôi đồng ý đặt lịch",
    ]
    for phrase in confirm_phrases:
        entities = extract_booking_entities(phrase)
        assert entities.get("is_booking_confirmation") is True, f"Failed for {phrase}"


def test_cross_thread_appointment_lookup_detection():
    lookup_phrases = [
        "Tôi có lịch khám vào thứ 2 tuần tới tại Vinmec Riverside thì bạn cho tôi xem lại thông tin với",
        "Cho tôi xem lại thông tin lịch khám",
        "Kiểm tra lịch hẹn của tôi",
        "Tôi đã đặt lịch khám chưa?",
    ]
    for phrase in lookup_phrases:
        entities = extract_booking_entities(phrase)
        assert entities.get("is_appointment_query") is True, f"Failed for {phrase}"
