"""
Token Counter Service sử dụng thư viện tiktoken
Tính toán chính xác:
- Số token đầu vào (Prompt Tokens)
- Số token đầu ra (Completion Tokens)
- Tổng token thực tế sử dụng (Total Tokens)
- Số token tiết kiệm được (Tokens Saved) khi đi qua Zero-Token Cache hoặc Fast-Path
- Ước tính chi phí theo bảng giá mô hình chuẩn (USD & VNĐ)
"""

from typing import Any

import tiktoken

from src.medical_assistant.config import get_settings


class TokenCounter:
    """Đếm token chuẩn hóa cho các mô hình ngôn ngữ lớn (OpenAI / LangChain / Gemini)"""

    def __init__(self, model_name: str | None = None):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.model_name or "gpt-4o-mini"
        try:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        except Exception:
            # Fallback sang cl100k_base nếu tên model không có trong bảng mapping trực tiếp
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str | None) -> int:
        """Đếm số token của một chuỗi văn bản bất kỳ"""
        if not text:
            return 0
        try:
            return len(self.encoding.encode(str(text)))
        except Exception:
            # Fallback ước tính đơn giản (1 từ tiếng Việt ~ 1.5 token)
            return int(len(str(text).split()) * 1.5)

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        """Đếm token cho định dạng hội thoại nhiều lượt (ChatML / OpenAI format)"""
        num_tokens = 0
        for message in messages:
            # 3 tokens overhead cho mỗi role/message envelope
            num_tokens += 3
            for key, value in message.items():
                num_tokens += self.count_tokens(value)
        num_tokens += 3  # overhead bắt đầu phản hồi của trợ lý
        return num_tokens

    def calculate_turn_metrics(
        self,
        user_query: str,
        response_text: str,
        context_text: str | None = None,
        is_zero_token: bool = False,
    ) -> dict[str, Any]:
        """
        Tính toán chi tiết các chỉ số token cho một lượt hội thoại.
        - user_query: câu hỏi từ bệnh nhân
        - response_text: câu trả lời từ hệ thống
        - context_text: ngữ cảnh bác sĩ/lịch khám hoặc triệu chứng bổ sung
        - is_zero_token: True nếu được giải quyết bởi Zero-Token Cache hoặc Fast Rules
        """
        prompt_content = f"{user_query} {context_text or ''}".strip()
        raw_prompt_tokens = self.count_tokens(prompt_content)
        raw_completion_tokens = self.count_tokens(response_text)
        potential_total = raw_prompt_tokens + raw_completion_tokens

        if is_zero_token:
            actual_prompt = 0
            actual_completion = 0
            actual_total = 0
            tokens_saved = potential_total
        else:
            actual_prompt = raw_prompt_tokens
            actual_completion = raw_completion_tokens
            actual_total = potential_total
            tokens_saved = 0

        # Ước tính chi phí theo giá gpt-4o-mini ($0.15/1M prompt, $0.60/1M completion)
        cost_usd = (actual_prompt * 0.15 + actual_completion * 0.60) / 1_000_000
        cost_saved_usd = (raw_prompt_tokens * 0.15 + raw_completion_tokens * 0.60) / 1_000_000 if is_zero_token else 0.0

        return {
            "prompt_tokens": actual_prompt,
            "completion_tokens": actual_completion,
            "total_tokens": actual_total,
            "tokens_saved": tokens_saved,
            "model": "rule-engine" if is_zero_token else self.model_name,
            "execution_mode": "deterministic_rule" if is_zero_token else "llm_or_estimated",
            "estimated_cost_usd": round(cost_usd, 6),
            "estimated_cost_saved_usd": round(cost_saved_usd, 6),
        }


_token_counter: TokenCounter | None = None


def get_token_counter() -> TokenCounter:
    """Singleton provider cho TokenCounter"""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
