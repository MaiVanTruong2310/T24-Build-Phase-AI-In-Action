import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.agent.state import AgentState


@pytest.mark.asyncio
class TestHybridDialogueV2ThreeTurns:
    async def test_3_turns_symptom_comparison_info(self):
        # 1. Turn 1: Symptom report + diagnosis concern
        state: AgentState = {
            "query": "Tôi tên Trường, tôi đang bị đau bụng bên trái, tôi nên làm gì? Bệnh của tôi có nặng không?",
            "probing_turn": 0,
            "collected_details": [],
            "language": "vi",
            "clinical_facts": {},
        }

        # We might hit OpenRouter limit so we can mock if needed, but we try real first
        res_analyze_1 = await analyze_node(state)
        state.update(res_analyze_1)

        # Should extract name and suggest asking clarifying question
        assert state.get("patient_name") == "Trường"

        res_respond_1 = await respond_node(state)
        # Verify it didn't ask about visit purpose
        resp1 = res_respond_1["response"].lower()
        assert "điều trị triệu chứng hay kiểm tra sức khỏe" not in resp1
        assert "đau ở vùng nào" not in resp1

        # 2. Turn 2: Comparison request
        state["query"] = "Thế khoa tiêu hóa của mình có ưu điểm gì hơn so với các bệnh viện khác"
        res_analyze_2 = await analyze_node(state)
        state.update(res_analyze_2)

        # Should be DEPARTMENT_INFO and comparison_requested True
        assert state["workflow_status"] == "DEPARTMENT_INFO"

        res_respond_2 = await respond_node(state)
        resp2 = res_respond_2["response"].lower()
        assert "chưa có dữ liệu đối chiếu" in resp2 or "chưa có dữ liệu so sánh" in resp2
        assert "tiêu hóa" in resp2

        # 3. Turn 3: Request detailed info
        state["query"] = "Thế cho tôi xin thông tin cụ thể của khoa tiêu hóa đi"
        res_analyze_3 = await analyze_node(state)
        state.update(res_analyze_3)

        assert state["workflow_status"] == "DEPARTMENT_INFO"

        res_respond_3 = await respond_node(state)
        resp3 = res_respond_3["response"].lower()
        assert "thông tin chuyên khoa" in resp3 or "thông tin chi tiết" in resp3
