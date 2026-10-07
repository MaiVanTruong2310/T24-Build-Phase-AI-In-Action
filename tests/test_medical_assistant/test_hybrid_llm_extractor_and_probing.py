import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.llm_clinical_extractor import get_llm_clinical_extractor


def test_clinical_fact_service_multi_domain_extraction():
    svc = get_clinical_fact_service()

    # 1. Thần kinh / Đau đầu
    facts_neuro = svc.extract("Tôi bị đau nửa đầu bên phải nhói nhói từ hôm qua, buồn nôn nhưng không sốt")
    assert facts_neuro["chief_complaint"] == "headache"
    assert facts_neuro["duration_days"] == 1
    assert "headache" in facts_neuro["positive_facts"]
    assert "one_sided_headache" in facts_neuro["positive_facts"]
    assert "nausea" in facts_neuro["positive_facts"]
    assert "fever" in facts_neuro["negative_facts"]

    # 2. Tiêu hóa / Đau bụng
    facts_gi = svc.extract("Em bị đau bụng thượng vị 2 ngày nay, ợ chua nhiều, không nôn ói không sốt")
    assert facts_gi["chief_complaint"] == "abdominal_pain"
    assert facts_gi["duration_days"] == 2
    assert "heartburn" in facts_gi["positive_facts"]
    assert "vomiting" in facts_gi["negative_facts"]
    assert "fever" in facts_gi["negative_facts"]

    # 3. Cơ xương khớp
    facts_ortho = svc.extract("Tôi bị đau vai gáy và tê tay 3 ngày nay")
    assert "neck_shoulder_pain" in facts_ortho["positive_facts"]
    assert "numbness_weakness" in facts_ortho["positive_facts"]
    assert facts_ortho["duration_days"] == 3


@pytest.mark.asyncio
async def test_llm_clinical_extractor_unit():
    extractor = get_llm_clinical_extractor()

    # Truy vấn đơn giản -> Router chọn RULE (tiết kiệm token)
    res_simple = await extractor.extract_async("Tôi bị đau đầu nhẹ")
    assert res_simple["extraction_method"] == "RULE"
    assert "headache" in res_simple["positive_facts"]

    # Truy vấn phức tạp có phủ định
    res_complex = await extractor.extract_async(
        "Bác sĩ ơi em đau nửa đầu dữ dội từ hôm kia, nhìn mờ nhưng không bị tê tay chân"
    )
    assert "headache" in res_complex["positive_facts"]
    assert "numbness_weakness" in res_complex["negative_facts"]


@pytest.mark.asyncio
async def test_fact_aware_probing_prevents_duplicate_questions_for_headache():
    config = {"configurable": {"thread_id": "test_fact_aware_headache_flow"}}

    # Turn 1: Bệnh nhân đã nói rõ vị trí (nửa đầu phải), thời gian (từ hôm qua), triệu chứng đi kèm (buồn nôn), phủ định (không sốt)
    first = await agent.ainvoke(
        {"query": "Em bị đau nửa đầu bên phải từ hôm qua tới giờ, buồn nôn nhưng không sốt"},
        config=config,
    )

    assert first["workflow_status"] == "PROBING_IN_PROGRESS"
    # KHÔNG được lặp lại câu hỏi turn 1 hỏi vị trí và thời gian!
    assert "vị trí nào" not in first["response"]
    assert "kéo dài bao lâu" not in first["response"]
    # Phải hỏi triệu chứng thần kinh còn thiếu (mắt mờ, nhìn đôi, tê yếu tay chân)
    assert any(term in first["response"] for term in ["nhìn mờ", "tê yếu", "nhìn đôi"])
    assert not first.get("available_slots")

    # Turn 2: Bệnh nhân trả lời không có nhìn mờ hay tê tay
    second = await agent.ainvoke(
        {"query": "Mắt em nhìn rõ bình thường, không tê yếu tay chân gì cả"},
        config=config,
    )

    # Đã thu thập đủ thông tin -> Chuyển sang chờ người dùng xem lịch, định hướng khoa Thần kinh
    assert second["workflow_status"] == "TRIAGED_AWAITING_SCHEDULE"
    assert "Thần kinh" in (second.get("suggested_department_name") or "")
    assert not second.get("available_slots")
    assert "tìm lịch khám" in second["response"] or "lịch khám" in second["response"]


@pytest.mark.asyncio
async def test_emergency_gate_overrides_llm_and_probing_immediately():
    config = {"configurable": {"thread_id": "test_emergency_override"}}
    res = await agent.ainvoke(
        {"query": "Tôi đau thắt ngực dữ dội lan lên cổ hàm và vã mồ hôi lạnh ngắt"},
        config=config,
    )
    assert res["is_emergency"] is True
    assert res["ats_level"] in (1, 2)
    assert res["workflow_status"] == "EMERGENCY"
    assert "115" in res["response"]
    # Không vào probing
    assert res.get("metadata", {}).get("needs_more_probing") is False
