import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService


def test_extracts_colloquial_constipation_facts_and_negations():
    facts = ClinicalFactService().extract(
        "Mấy bữa nay bụng tui cứ ì ạch, ba bốn ngày mới đi cầu được, "
        "phân cứng ngắc, rặn mệt nghỉ mà bụng lại chướng. "
        "Tui vẫn đánh hơi được, không ói, không sốt."
    )

    assert facts["chief_complaint"] == "constipation"
    assert facts["bowel_interval_days"] == 4
    assert {"hard_stool", "straining", "abdominal_bloating", "passing_gas"} <= set(facts["positive_facts"])
    assert {"vomiting", "fever", "unable_to_pass_gas"} <= set(facts["negative_facts"])


@pytest.mark.asyncio
async def test_dialogue_does_not_repeat_already_known_constipation_facts_or_show_slots_early():
    config = {"configurable": {"thread_id": "test_fact_aware_colloquial_constipation"}}
    first = await agent.ainvoke(
        {
            "query": "Mấy bữa nay bụng tui cứ ì ạch, ba bốn ngày mới đi cầu được, phân cứng ngắc, rặn mệt nghỉ mà bụng lại chướng. Tui vẫn đánh hơi được, không ói, không sốt."
        },
        config=config,
    )

    assert first["workflow_status"] == "PROBING_IN_PROGRESS"
    assert "phân có khô cứng" not in first["response"]
    assert "còn trung tiện" not in first["response"]
    assert "có nôn ói" not in first["response"]
    assert "có sốt" not in first["response"]
    assert not first.get("available_slots")

    second = await agent.ainvoke(
        {
            "query": "Bị hơn tuần rồi đó, hôm qua tui thấy dính chút máu đỏ trên giấy, bụng chỉ đau lâm râm chứ không quặn dữ, ăn uống vẫn được."
        },
        config=config,
    )
    assert "có thấy máu" not in second["response"]
    assert "đau bụng có tăng" not in second["response"]

    third = await agent.ainvoke(
        {"query": "Không sụt cân đâu, ăn uống vẫn bình thường."},
        config=config,
    )
    assert third["workflow_status"] == "TRIAGED_AWAITING_SCHEDULE"
    assert third["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert not third.get("available_slots")
    assert "Anh/chị có muốn em tìm lịch khám" in third["response"]  # khách vãng lai


def test_colloquial_abdominal_word_order_is_still_a_symptom_report():
    facts = ClinicalFactService().extract("Mấy hôm nay bụng bên trái của tôi cứ đau âm ỉ, tầm 4 trên 10.")

    assert facts["chief_complaint"] == "abdominal_pain"
    assert "mild_abdominal_pain" in facts["positive_facts"]


def test_denied_diarrhea_and_blood_are_recorded_as_negative_facts():
    facts = ClinicalFactService().extract("Đã ba ngày rồi, không tiêu chảy và không đi ngoài ra máu.")

    assert {"diarrhea", "blood_in_stool"} <= set(facts["negative_facts"])
    assert not ({"diarrhea", "blood_in_stool"} & set(facts["positive_facts"]))


def test_thigh_pain_classified_as_musculoskeletal_not_abdominal():
    from src.medical_assistant.domain.probing_service import get_probing_service
    from src.medical_assistant.domain.triage_service import get_triage_service

    query = "Tôi thấy bị đau ở phần bắp đùi, đau âm ỉ khoảng 5 ngày nay rồi nó ảnh hưởng đến việc đi lại của tôi."
    facts = ClinicalFactService().extract(query)
    assert facts["chief_complaint"] == "muscle_pain"
    assert facts["complaints"][0]["system"] == "musculoskeletal"

    tree = get_probing_service().find_probing_tree(query)
    assert tree is not None
    assert tree.category_key == "CO_XUONG_KHOP"

    res = get_triage_service().evaluate_symptoms(query)
    assert res.suggested_specialty == "Chấn thương chỉnh hình - Y học thể thao"
