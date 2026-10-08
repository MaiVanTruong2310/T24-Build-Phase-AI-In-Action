"""Unit tests for info_agent_node using fake tool-calling LLMs."""

from __future__ import annotations

import unittest
from typing import Any

from langchain_core.messages import AIMessage

from src.medical_assistant.agent.nodes.info_agent_node import info_agent_node


class FakeToolCallingModel:
    """Mock LLM simulates tool call generation and final conversational answers."""

    def __init__(self, responses: list[AIMessage]):
        self.responses = list(responses)
        self.invoked_calls: list[Any] = []

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> Any:
        return self

    async def ainvoke(self, messages: list[Any], **kwargs: Any) -> AIMessage:
        self.invoked_calls.append(messages)
        if self.responses:
            return self.responses.pop(0)
        return AIMessage(content="Dạ, em xin hết thông tin ạ.")


class TestInfoAgentNode(unittest.IsolatedAsyncioTestCase):
    async def test_info_agent_calls_tool_and_answers(self):
        # Lượt 1: LLM quyết định gọi tool search_doctors
        tool_call_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_doctors",
                    "args": {"specialty": "Tim mạch", "limit": 2},
                    "id": "call_123",
                }
            ],
        )
        # Lượt 2: LLM nhận kết quả tool và trả lời grounded
        final_answer_msg = AIMessage(
            content="Dạ, em gửi bác thông tin bác sĩ chuyên khoa Tim mạch tại Vinmec ạ. Bác sĩ giàu kinh nghiệm có thể thăm khám cho bác."
        )

        fake_llm = FakeToolCallingModel([tool_call_msg, final_answer_msg])

        state = {
            "query": "Cho tôi hỏi có bác sĩ tim mạch nào giỏi không?",
            "language": "vi",
        }

        result = await info_agent_node(state, llm=fake_llm)

        self.assertEqual(result["workflow_status"], "INFO_ANSWERED")
        self.assertIn("Dạ, em gửi bác", result["response"])
        self.assertNotIn(
            "Khuyến cáo y tế", result["response"]
        )  # Prompt F4: Chỉ gắn cho bệnh học, không gắn cho tra cứu bác sĩ
        self.assertEqual(result["metadata"]["route"], "info_agent")
        self.assertEqual(result["metadata"]["tools_called"], ["search_doctors"])
        self.assertEqual(len(result["last_tool_results"]), 1)
        self.assertEqual(result["last_tool_results"][0]["tool"], "search_doctors")

    async def test_info_agent_direct_answer_no_tool(self):
        # LLM trả lời trực tiếp mà không cần gọi tool
        direct_msg = AIMessage(content="Dạ, em chào bác! Bác cần em hỗ trợ thông tin gì ạ?")
        fake_llm = FakeToolCallingModel([direct_msg])

        state = {
            "query": "Xin chào em",
            "language": "vi",
        }

        result = await info_agent_node(state, llm=fake_llm)

        self.assertEqual(result["workflow_status"], "INFO_ANSWERED")
        self.assertEqual(result["metadata"]["tools_called"], [])
        self.assertEqual(result["last_tool_results"], [])

    async def test_info_agent_unknown_tool_handling(self):
        # LLM gọi tool không tồn tại trong danh mục
        unknown_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "non_existent_tool",
                    "args": {"foo": "bar"},
                    "id": "call_unknown",
                }
            ],
        )
        fallback_msg = AIMessage(content="Dạ, em chưa tìm thấy dữ liệu này ạ.")
        fake_llm = FakeToolCallingModel([unknown_call, fallback_msg])

        state = {"query": "Tra cứu gì đó kỳ lạ"}
        result = await info_agent_node(state, llm=fake_llm)

        self.assertEqual(result["workflow_status"], "INFO_ANSWERED")
        self.assertIn("Tool 'non_existent_tool' không tồn tại.", result["metadata"]["tool_errors"][0])

    async def test_info_agent_dlp_sanitizes_leak(self):
        # LLM vô tình in ra secret key hoặc thông tin nhạy cảm
        leak_msg = AIMessage(content="Dạ thông tin kết nối hệ thống là sk-proj-1234567890abcdef1234567890abcdef12 ạ.")
        fake_llm = FakeToolCallingModel([leak_msg])

        state = {"query": "Mã bí mật là gì?"}
        result = await info_agent_node(state, llm=fake_llm)

        self.assertNotIn("sk-proj-1234567890abcdef1234567890abcdef12", result["response"])
        self.assertIn("[REDACTED", result["response"])

    async def test_info_agent_follow_up_with_previous_results(self):
        # Mô phỏng câu hỏi tiếp nối có ngữ cảnh từ lượt trước
        answer_msg = AIMessage(content="Dạ, cơ sở Times City nằm ở quận Hai Bà Trưng, Hà Nội ạ.")
        fake_llm = FakeToolCallingModel([answer_msg])

        state = {
            "query": "Bệnh viện đó nằm ở quận nào?",
            "last_tool_results": [{"tool": "list_facilities", "data": {"name": "Times City"}}],
        }

        result = await info_agent_node(state, llm=fake_llm)
        self.assertEqual(result["workflow_status"], "INFO_ANSWERED")
        # Kiểm tra ngữ cảnh trước được truyền vào model
        first_call_messages = fake_llm.invoked_calls[0]
        context_msg_content = "".join(str(m.content) for m in first_call_messages)
        self.assertIn("Times City", context_msg_content)


if __name__ == "__main__":
    unittest.main()
