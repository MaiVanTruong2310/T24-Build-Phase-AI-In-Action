import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service


def test_clinical_negation_service_unit():
    neg = get_clinical_negation_service()

    # Tiếng Việt có dấu
    assert neg.is_phrase_negated("đau ngực", "Tôi bị đau bụng nhưng không đau ngực") is True
    assert neg.is_phrase_negated("đau ngực", "Tôi bị đau ngực dữ dội") is False
    assert neg.is_phrase_negated("khó thở", "Tôi không khó thở, chỉ ho nhẹ") is True
    assert neg.is_phrase_negated("ho", "Tôi không khó thở, chỉ ho nhẹ") is False
    assert neg.is_phrase_negated("sốt", "Bác sĩ ơi em hết sốt rồi") is True
    assert neg.is_phrase_negated("sốt", "Tôi chưa bị sốt bao giờ") is True

    # Tiếng Việt không dấu / teencode
    assert neg.is_phrase_negated("đau ngực", "tui ko dau nguc") is True
    assert neg.is_phrase_negated("dau nguc", "tui k dau nguc dau") is True
    assert neg.is_phrase_negated("đau ngực", "tui dau nguc lam") is False

    # Tiếng Anh
    assert neg.is_phrase_negated("chest pain", "Patient denies chest pain and fever") is True
    assert neg.is_phrase_negated("fever", "Patient denies chest pain and fever") is True
    assert neg.is_phrase_negated("chest pain", "Patient has severe chest pain without dyspnea") is False
    assert neg.is_phrase_negated("dyspnea", "Patient has severe chest pain without dyspnea") is True


def test_cache_gating_prevents_greeting_when_symptoms_present():
    cache = get_cache_service()

    # Chào hỏi thuần túy -> Vào cache
    assert cache.check_cache("Xin chào trợ lý") is not None
    assert cache.check_cache("Hi")[2] == "GREETING"

    # Chào hỏi kèm triệu chứng lâm sàng -> TUYỆT ĐỐI KHÔNG vào cache
    assert cache.check_cache("Xin chào, tôi bị đau thắt ngực dữ dội") is None
    assert cache.check_cache("Chào bác sĩ, em bị đau bụng 2 ngày nay") is None
    assert cache.check_cache("Tôi muốn đặt lịch vì tôi bị khó thở và sốt cao") is None

    # FAQ chính sách/giá không có triệu chứng -> Vào cache bình thường
    assert cache.check_cache("Bảng giá khám chuyên khoa bao nhiêu?") is not None
    assert cache.check_cache("Giờ làm việc bệnh viện thế nào?")[2] == "WORKING_HOURS_HOTLINE"


@pytest.mark.asyncio
async def test_acs_cardiac_emergency_trigger_with_accents_and_unaccented():
    # 1. Điển hình tiếng Việt có dấu
    res_vi = await agent.ainvoke(
        {"query": "Tôi đau ngực dữ dội lan ra cánh tay trái và vã mồ hôi lạnh"},
        config={"configurable": {"thread_id": "test_acs_1"}},
    )
    assert res_vi["is_emergency"] is True
    assert res_vi["ats_level"] in (1, 2)
    assert res_vi["max_booking_days"] == 0
    assert "115" in res_vi["response"]

    # 2. Tiếng Việt không dấu / gắng sức
    res_norm = await agent.ainvoke(
        {"query": "tui bi dau nguc de nang lan len ham khi leo cau thang"},
        config={"configurable": {"thread_id": "test_acs_2"}},
    )
    assert res_norm["is_emergency"] is True
    assert res_norm["ats_level"] in (1, 2)
    assert "115" in res_norm["response"]

    # 3. Chào hỏi kèm triệu chứng cấp cứu -> Không bị kẹt ở cache, phải kích hoạt cấp cứu ngay!
    res_mixed = await agent.ainvoke(
        {"query": "Xin chào bác sĩ, tôi đang bị thắt ngực dữ dội bóp nghẹt khó thở"},
        config={"configurable": {"thread_id": "test_acs_3"}},
    )
    assert res_mixed["is_emergency"] is True
    assert res_mixed["ats_level"] in (1, 2)
    assert res_mixed["workflow_status"] == "EMERGENCY"


@pytest.mark.asyncio
async def test_negation_prevents_false_emergency_over_triage():
    # Câu có từ "đau ngực" nhưng là PHỦ ĐỊNH -> Không được kích hoạt cấp cứu tim mạch!
    res = await agent.ainvoke(
        {"query": "Tôi bị đau quặn bụng vùng thượng vị và ợ chua, không đau ngực, không khó thở"},
        config={"configurable": {"thread_id": "test_negation_overtriage"}},
    )
    assert res["is_emergency"] is False
    assert res["ats_level"] != 1
    assert "Tiêu hóa" in (res.get("suggested_department_name") or "")
    # Nội dung chính không báo cấp cứu; lời dặn dự phòng của ca ATS 3 ("Trong lúc chờ khám… gọi 115") được phép.
    assert "115" not in res["response"].split("Trong lúc chờ khám")[0]
