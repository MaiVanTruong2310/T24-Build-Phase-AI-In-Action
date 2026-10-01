from src.medical_assistant.domain.guardrail_service import get_guardrail_service


def test_abdominal_diagnosis_request_asks_concrete_followup_before_booking():
    response, replies = get_guardrail_service().get_diagnosis_guardrail_response(
        "Tôi bị đau bụng thì tôi bị bệnh gì", "Tiêu hóa - Gan mật", "vi"
    )
    assert "vùng nào của bụng" in response
    assert "bắt đầu từ khi nào" in response
    assert "0–10" in response
    assert "buồn nôn/nôn" in response
    assert "chưa thể xác định" in response
    assert not any("Xem lịch" in reply for reply in replies)


def test_other_symptoms_do_not_receive_abdominal_questions():
    response, _ = get_guardrail_service().get_diagnosis_guardrail_response("đau đầu", "Thần kinh", "vi")
    assert "vị trí nào" in response
    assert "vùng nào của bụng" not in response


def test_english_followup_keeps_questions_and_does_not_offer_booking():
    response, replies = get_guardrail_service().get_diagnosis_guardrail_response("abdominal pain", "Tiêu hóa", "en")
    assert "Where in your abdomen" in response
    assert "0 to 10" in response
    assert not any("schedule" in reply.lower() for reply in replies)
