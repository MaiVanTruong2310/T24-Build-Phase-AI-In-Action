import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.agent.nodes.router_node import route_intent_node
from src.medical_assistant.domain.guardrail_service import get_guardrail_service


def test_f1_social_statement_reproduction_table():
    """Kiểm tra đúng 7 câu hỏi tái hiện trong bảng bước 1 của Prompt F1."""
    guard = get_guardrail_service()

    # 4 câu y tế / tra cứu có từ gây nhiễu ('yêu cầu', 'thích khám', 'thời tiết đau đầu')
    # -> KHÔNG được trả SOCIAL_STATEMENT (phải trả None để đi tiếp vào Router/Analyze/Info)
    assert guard.check_intent("Tôi yêu cầu xem danh sách bác sĩ tim mạch") is None
    assert guard.check_intent("Em yêu cầu thông tin khoa Nhi") is None
    assert guard.check_intent("Tôi thích khám buổi sáng") is None
    assert guard.check_intent("Thời tiết hôm nay đau đầu quá") is None

    # 3 câu xã giao thuần túy -> Phải trả SOCIAL_STATEMENT
    res_ghet = guard.check_intent("Tôi ghét anh Thành")
    assert res_ghet is not None and res_ghet.get("intent") == "SOCIAL_STATEMENT"

    res_ai = guard.check_intent("Bạn là ai")
    assert res_ai is not None and res_ai.get("intent") == "SOCIAL_STATEMENT"

    res_ngu = guard.check_intent("Chúc ngủ ngon")
    assert res_ngu is not None and res_ngu.get("intent") == "SOCIAL_STATEMENT"


def test_f1_negative_cases_medical_requests_with_social_words():
    """Ít nhất 15 câu âm tính: câu chứa chữ yêu/thích/thời tiết nhưng mang ý nghĩa y tế/tra cứu/đặt lịch."""
    guard = get_guardrail_service()

    negative_queries = [
        "Tôi yêu cầu xem danh sách bác sĩ tim mạch",
        "Em yêu cầu thông tin khoa Nhi",
        "Tôi thích khám buổi sáng",
        "Thời tiết hôm nay đau đầu quá",
        "Tôi yêu cầu tư vấn giá khám tổng quát",
        "Tôi thích đặt lịch với bác sĩ Dũng",
        "Tôi yêu cầu hỗ trợ đặt lịch khám tiêu hóa",
        "Tôi thích khám ở cơ sở Times City",
        "Em yêu cầu cung cấp thông tin phòng khám",
        "Tôi yêu cầu gặp bác sĩ khoa mắt",
        "Thời tiết lạnh làm tôi bị ho và sốt",
        "Tôi thích được bác sĩ chuyên khoa nội khám",
        "Tôi yêu cầu đổi lịch hẹn khám sang ngày mai",
        "Tôi rất thích dịch vụ khám tại Vinmec Central Park",
        "Tôi yêu cầu kiểm tra lịch trống khoa tim mạch",
        "Tôi thích chọn slot khám lúc 9 giờ sáng",
        "Thời tiết oi bức khiến tôi bị tức ngực khó thở",
    ]

    for q in negative_queries:
        res = guard.check_intent(q)
        intent = res.get("intent") if res else None
        assert intent != "SOCIAL_STATEMENT", f"Câu y tế '{q}' bị bắt nhầm thành SOCIAL_STATEMENT!"


def test_f1_positive_cases_pure_social_statements():
    """Ít nhất 10 câu dương tính: câu xã giao thuần túy, không có triệu chứng hay yêu cầu y tế."""
    guard = get_guardrail_service()

    positive_queries = [
        "Tôi ghét anh Thành",
        "Bạn là ai",
        "Chúc ngủ ngon",
        "Tui rất ghét người kia",
        "Bạn có người yêu chưa",
        "Làm quen được không",
        "Trời mưa to quá",
        "Thời tiết hôm nay đẹp thật đấy",
        "Tôi yêu bạn bot này",
        "Tôi rất thích bạn",
        "Em ghét sự chờ đợi",
        "Bạn mấy tuổi rồi",
    ]

    for q in positive_queries:
        res = guard.check_intent(q)
        assert res is not None, f"Câu xã giao '{q}' không được nhận diện!"
        assert res.get("intent") == "SOCIAL_STATEMENT", f"Câu '{q}' không khớp SOCIAL_STATEMENT, kết quả: {res}"


@pytest.mark.asyncio
async def test_f1_router_preserves_clinical_episode_on_social_statement():
    """Khi có active clinical episode, SOCIAL_STATEMENT chuyển sang analyze để bảo toàn episode."""
    seeded_state = {
        "query": "Tôi ghét anh Thành",
        "ats_level": 4,
        "urgency_tier": "WITHIN_WEEK",
        "max_booking_days": 7,
        "suggested_department_code": "TIEU_HOA",
        "suggested_department_name": "Tiêu hóa - Gan mật",
        "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
        "probing_turn": 2,
        "active_probing_category": "DAU_BUNG",
        "collected_details": ["Bụng đau âm ỉ 3 ngày"],
        "clinical_facts": {
            "chief_complaint": "abdominal_pain",
            "positive_facts": ["mild_abdominal_pain"],
            "negative_facts": [],
        },
    }

    # Router node không được short-circuit chitchat đóng khuôn, phải điều hướng sang analyze
    router_res = await route_intent_node(seeded_state)
    assert router_res["route_destination"] == "analyze"

    # Chạy qua full graph để xác minh episode được bảo toàn và có SOCIAL_REDIRECT
    config = {"configurable": {"thread_id": "test_f1_episode_isolation_thread"}}
    res = await agent.ainvoke(seeded_state, config=config)
    assert res["workflow_status"] == "SOCIAL_REDIRECT"
    assert res["ats_level"] == 4
    assert res["collected_details"] == ["Bụng đau âm ỉ 3 ngày"]
    assert "không đánh giá" in res["response"]


@pytest.mark.asyncio
async def test_f1_router_short_circuits_chitchat_when_no_clinical_episode():
    """Khi chưa có episode lâm sàng nào, câu xã giao được trả lời nhanh (chitchat)."""
    initial_state = {"query": "Tôi ghét anh Thành"}
    router_res = await route_intent_node(initial_state)
    assert router_res["route_destination"] == "chitchat"
    assert router_res["workflow_status"] == "SOCIAL_REDIRECT"
    assert "không đánh giá" in router_res["response"]
