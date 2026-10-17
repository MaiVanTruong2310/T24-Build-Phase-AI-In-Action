"""Câu trả lời info_agent chạm trần token (finish_reason=length) không được hiển thị cụt giữa chừng."""

import pytest

from src.medical_assistant.agent.nodes.info_agent_node import _trim_truncated


@pytest.mark.parametrize(
    ("text", "expected_end"),
    [
        (
            "Dạ, em xin gửi.\n\n1. **Times City** – 458 Minh Khai.\n2. **Royal City** – 72A Nguyễn Trãi, KĐ",
            "458 Minh Khai.",
        ),
        ("Dạ, có các cơ sở sau.\n- Times City\n- Smart City\nDạ, em lưu ý: chưa rõ cơ sở nào có **Tr", "- Smart City"),
        (
            "Dạ, trung tâm có nhiều bác sĩ giỏi. Anh có thể đặt lịch qua ứng dụng. Ngoài ra còn có dịch vụ tư vấn trực",
            "qua ứng dụng.",
        ),
    ],
)
def test_trim_truncated_ends_on_complete_line_or_sentence(text, expected_end):
    out = _trim_truncated(text)
    assert out.endswith(expected_end) and out.count("**") % 2 == 0
