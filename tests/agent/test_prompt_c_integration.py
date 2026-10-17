"""Tests for Prompt C (P1): Info Agent Integration, Observability & Telemetry."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.info_agent_node import info_agent_node
from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.config import get_settings
from src.medical_assistant.infrastructure.telemetry_logger import (
    configure_telemetry_rotating_logger,
    get_daily_telemetry_metrics,
)


class TestPromptCIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_info_agent_simulated_db_unavailable_honest_answer(self):
        """Giả lập DB/tool báo data_unavailable -> Trả lời trung thực, cờ data_unavailable=True, có telemetry."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        # Lần 1 gọi tool search_doctors, tool trả data_unavailable
        call_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search_doctors", "args": {"specialty_name": "Tim mạch"}, "id": "call_1"}],
        )
        # Lần 2 model kết luận trung thực dựa trên kết quả tool
        final_msg = AIMessage(
            content="Dạ em chưa tìm thấy thông tin phù hợp trong hệ thống do kết nối cơ sở dữ liệu tạm thời gián đoạn. Bác vui lòng liên hệ tổng đài 1900 232 389 ạ."
        )
        mock_bound.ainvoke = AsyncMock(side_effect=[call_msg, final_msg])

        with patch("src.medical_assistant.agent.nodes.info_agent_node.ALL_TOOLS") as mock_tools:
            mock_tool = MagicMock()
            mock_tool.name = "search_doctors"
            mock_tool.invoke.return_value = {
                "found": False,
                "data_unavailable": True,
                "reason": "DATABASE_OFFLINE",
            }
            mock_tools.__iter__.return_value = [mock_tool]

            state = {
                "query": "Xem danh sách bác sĩ khoa Tim mạch",
                "metadata": {"session_id": "sess_101", "patient_profile": {"name": "Nguyễn Văn A"}},
            }

            res = await info_agent_node(state, llm=mock_llm)

            self.assertEqual(res["workflow_status"], "INFO_ANSWERED")
            meta = res["metadata"]
            # Kiểm tra gộp metadata (không ghi đè mất session_id, patient_profile)
            self.assertEqual(meta.get("session_id"), "sess_101")
            self.assertEqual(meta.get("patient_profile", {}).get("name"), "Nguyễn Văn A")
            # Kiểm tra cờ data_unavailable
            self.assertTrue(meta.get("data_unavailable"))
            self.assertEqual(meta.get("data_unavailable_reason"), "DATABASE_OFFLINE")
            # Kiểm tra structured telemetry
            telemetry = meta.get("structured_telemetry", {})
            self.assertEqual(telemetry.get("route"), "info_agent")
            self.assertTrue(telemetry.get("data_unavailable"))
            self.assertEqual(telemetry.get("data_unavailable_reason"), "DATABASE_OFFLINE")
            self.assertTrue(telemetry.get("llm_succeeded"))
            self.assertFalse(telemetry.get("fallback_used"))
            # Kiểm tra có messages compacted
            self.assertIn("messages", res)
            self.assertEqual(len(res["messages"]), 2)
            self.assertEqual(res["messages"][0]["role"], "user")
            self.assertEqual(res["messages"][1]["role"], "assistant")
            # Kiểm tra có quick_replies
            self.assertIn("quick_replies", meta)
            self.assertGreater(len(meta["quick_replies"]), 0)

    async def test_info_agent_simulated_llm_failure_telemetry(self):
        """Giả lập mất LLM/timeout -> trả về thông báo trung thực, fallback_used=True, llm_succeeded=False."""
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound
        mock_bound.ainvoke = AsyncMock(side_effect=RuntimeError("Provider connection reset by peer"))

        state = {
            "query": "Bệnh viện Vinmec Times City ở đâu?",
            "metadata": {"session_id": "sess_preserved"},
        }
        # Tra thẳng DB cũng không được → báo trung thực "trục trặc tạm thời".
        with patch("src.medical_assistant.agent.nodes.info_agent_node.answer_info_without_llm", return_value=None):
            res = await info_agent_node(state, llm=mock_llm)

        self.assertEqual(res["workflow_status"], "INFO_UNAVAILABLE")
        self.assertIn("trục trặc tạm thời", res["response"])
        meta = res["metadata"]
        self.assertEqual(meta.get("session_id"), "sess_preserved")
        self.assertFalse(meta.get("llm_succeeded"))
        self.assertTrue(meta.get("fallback_used"))
        self.assertTrue(meta.get("data_unavailable"))

        telemetry = meta.get("structured_telemetry", {})
        self.assertEqual(telemetry.get("route"), "info_agent")
        self.assertFalse(telemetry.get("llm_succeeded"))
        self.assertTrue(telemetry.get("fallback_used"))

    async def test_info_agent_two_turn_follow_up_preserves_context(self):
        """Kiểm tra lượt 1 lưu last_tool_results và messages, lượt 2 follow-up vẫn nhớ ngữ cảnh."""
        # Lượt 1
        mock_llm_1 = MagicMock()
        mock_bound_1 = MagicMock()
        mock_llm_1.bind_tools.return_value = mock_bound_1

        call_msg_1 = AIMessage(
            content="",
            tool_calls=[{"name": "search_doctors", "args": {"specialty_name": "Tai Mũi Họng"}, "id": "call_tmh"}],
        )
        final_msg_1 = AIMessage(content="Khoa Tai Mũi Họng có Bác sĩ Trần Văn Bình, 15 năm kinh nghiệm.")
        mock_bound_1.ainvoke = AsyncMock(side_effect=[call_msg_1, final_msg_1])

        tool_data = [
            {
                "full_name": "Trần Văn Bình",
                "title": "Bác sĩ Chuyên khoa II",
                "years_of_experience": 15,
                "specialties": ["Tai Mũi Họng"],
            }
        ]

        with patch("src.medical_assistant.agent.nodes.info_agent_node.ALL_TOOLS") as mock_tools:
            mock_tool = MagicMock()
            mock_tool.name = "search_doctors"
            mock_tool.invoke.return_value = {"found": True, "count": 1, "doctors": tool_data}
            mock_tools.__iter__.return_value = [mock_tool]

            state_turn1 = {
                "query": "Xem bác sĩ khoa Tai Mũi Họng",
                "messages": [],
            }
            res1 = await info_agent_node(state_turn1, llm=mock_llm_1)

            self.assertIn("last_tool_results", res1)
            self.assertGreater(len(res1["last_tool_results"]), 0)
            self.assertEqual(len(res1["messages"]), 2)

            # Lượt 2: Hỏi tiếp (Follow-up) "Bác sĩ đó có bao nhiêu năm kinh nghiệm?"
            mock_llm_2 = MagicMock()
            mock_bound_2 = MagicMock()
            mock_llm_2.bind_tools.return_value = mock_bound_2

            # Ở lượt 2, model trực tiếp trả lời từ ngữ cảnh mà không cần gọi tool lại
            final_msg_2 = AIMessage(
                content="Dạ, Bác sĩ Trần Văn Bình có 15 năm kinh nghiệm chuyên khoa Tai Mũi Họng ạ."
            )
            mock_bound_2.ainvoke = AsyncMock(return_value=final_msg_2)

            state_turn2 = {
                "query": "Bác sĩ đó có bao nhiêu năm kinh nghiệm?",
                "messages": res1["messages"],
                "last_tool_results": res1["last_tool_results"],
                "metadata": res1["metadata"],
            }

            res2 = await info_agent_node(state_turn2, llm=mock_llm_2)

            self.assertIn("15 năm kinh nghiệm", res2["response"])
            # Lịch sử hội thoại nối dài thành 4 tin nhắn (compaction window gần)
            self.assertEqual(len(res2["messages"]), 4)

    async def test_respond_node_data_unavailable_wording_and_hotline(self):
        """Kiểm tra respond_node: khi data_unavailable=True, bỏ khẳng định 'luôn có bác sĩ sẵn sàng' và lấy hotline từ config."""
        state = {
            "query": "Tôi muốn đặt hẹn khám Tiêu hóa",
            "workflow_status": "TRIAGED_READY_FOR_BOOKING",
            "suggested_department_name": "Tiêu hóa",
            "available_slots": [],
            "language": "vi",
            "metadata": {
                "data_unavailable": True,
                "data_unavailable_reason": "DATABASE_ERROR",
                "llm_invoked": False,
            },
        }

        res = await respond_node(state)
        resp_text = res["response"]

        # Bắt buộc không được chứa câu khẳng định cũ
        self.assertNotIn("luôn có đội ngũ bác sĩ chuyên khoa sẵn sàng tiếp nhận khám", resp_text)
        # Bắt buộc chứa thông tin gián đoạn và hotline từ config
        hotline = get_settings().hospital_hotline
        self.assertIn(hotline, resp_text)
        self.assertIn("tạm thời gián đoạn", resp_text)

        # Kiểm tra telemetry nhánh clinical/booking
        telemetry = res["metadata"].get("structured_telemetry", {})
        self.assertTrue(telemetry.get("data_unavailable"))
        self.assertIsNone(telemetry.get("llm_succeeded"))  # Không invoke LLM thì không mặc định True
        self.assertFalse(telemetry.get("fallback_used"))

    async def test_find_doctors_node_does_not_duplicate_queries_when_fetched_in_analyze(self):
        """Kiểm tra find_doctors_node tái sử dụng slot nếu analyze_node đã query trong cùng lượt."""
        state = {
            "suggested_department_name": "Tim mạch",
            "available_slots": [{"full_name": "Bác sĩ A"}],
            "metadata": {
                "slots_fetched_in_turn": True,
                "data_unavailable": False,
            },
        }
        res = await find_doctors_node(state)
        # Không được xóa hoặc query đè lên
        self.assertEqual(len(res["available_slots"]), 1)
        self.assertEqual(res["available_slots"][0]["full_name"], "Bác sĩ A")

    def test_daily_telemetry_metrics_aggregation(self):
        """Kiểm tra hàm get_daily_telemetry_metrics đọc log và tổng hợp chỉ số."""
        configure_telemetry_rotating_logger()
        metrics = get_daily_telemetry_metrics()
        self.assertIn("dates_available", metrics)
        self.assertIn("metrics_by_date", metrics)
