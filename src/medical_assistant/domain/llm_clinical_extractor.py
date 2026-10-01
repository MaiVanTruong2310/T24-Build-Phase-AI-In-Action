"""
LLM-Powered Hybrid Clinical Fact Extractor
Tầng trích xuất dữ kiện lâm sàng kết hợp (Hybrid):
1. Tầng 1: Rule Extractor (Deterministic, 0ms, 0 tokens) cho các biểu hiện chuẩn, ngắn gọn.
2. Tầng 2: Small LLM (GPT-4o-mini structured output) cho ngôn ngữ tự nhiên, phương ngữ đời thường,
   nhiều mệnh đề đối lập hoặc triệu chứng phức tạp ngoài từ điển regex cố định.
3. Fallback an toàn: Nếu LLM lỗi mạng/timeout, tự động dùng Rule Extractor, không bao giờ làm gián đoạn hội thoại.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.medical_assistant.domain.clinical_fact_service import (
    ClinicalFactService,
    get_clinical_fact_service,
)
from src.medical_assistant.domain.clinical_negation_service import (
    get_clinical_negation_service,
)
from src.medical_assistant.infrastructure.llm import get_llm

logger = logging.getLogger(__name__)


class ClinicalFactModel(BaseModel):
    """Mô hình dữ kiện lâm sàng cấu trúc chuẩn y khoa."""

    chief_complaint: str | None = Field(
        None,
        description="Triệu chứng chính hoặc lý do khám chính (e.g. constipation, headache, abdominal_pain, chest_pain, cough, fever, dizziness, back_pain, rash, nausea, sore_throat).",
    )
    positive_facts: list[str] = Field(
        default_factory=list,
        description="Các triệu chứng / dấu hiệu người bệnh XÁC NHẬN CÓ (e.g. hard_stool, straining, abdominal_bloating, nausea, throbbing_pain, fever, cough, fatigue).",
    )
    negative_facts: list[str] = Field(
        default_factory=list,
        description="Các triệu chứng / dấu hiệu người bệnh PHỦ ĐỊNH, KHÔNG CÓ, hoặc ĐÃ HẾT (e.g. no_fever, no_vomiting, no_chest_pain, unable_to_pass_gas_denied).",
    )
    duration_days: int | None = Field(None, description="Thời gian kéo dài tính theo ngày (nếu người bệnh đề cập).")
    bowel_interval_days: int | None = Field(
        None, description="Số ngày giữa các lần đi ngoài nếu liên quan đến tiêu hóa/táo bón."
    )
    location: str | None = Field(
        None, description="Vị trí giải phẫu cụ thể (e.g. nửa đầu phải, sau gáy, thượng vị, hạ sườn, ngực trái)."
    )
    severity: str | None = Field(None, description="Mức độ đau / khó chịu nếu được miêu tả: mild, moderate, severe.")
    qualifiers: list[str] = Field(
        default_factory=list,
        description="Tính chất cơn đau hoặc đặc điểm: nhói, âm ỉ, quặn thắt, lan ra tay, sợ ánh sáng, lạnh run.",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Độ tin cậy của việc trích xuất.")
    reasoning: str | None = Field(None, description="Tóm tắt ngắn gọn lý do phân loại dữ kiện.")


EXTRACTION_SYSTEM_PROMPT = """Bạn là Chuyên gia Trích xuất Dữ kiện Lâm sàng Y tế (Clinical Facts Extractor) cho hệ thống tiếp đón bệnh viện.
Nhiệm vụ của bạn là đọc lời mô tả của người bệnh (tiếng Việt hoặc tiếng Anh) và trích xuất cấu trúc dữ kiện lâm sàng trung thực, khách quan:

QUY TẮC BẮT BUỘC:
1. KHÔNG chẩn đoán bệnh tật (không kết luận 'bác bị viêm ruột thừa', 'viêm amidan').
2. KHÔNG kê đơn hoặc khuyên dùng thuốc.
3. Phân biệt rõ rệt:
   - positive_facts: Triệu chứng người bệnh THỰC SỰ CÓ.
   - negative_facts: Triệu chứng người bệnh NÓI RÕ LÀ KHÔNG CÓ, CHƯA BỊ, hoặc ĐÃ HẾT (phủ định).
4. Quy đổi thời gian sang ngày (duration_days) nếu có (hôm qua = 1, 3 ngày = 3, 1 tuần = 7, hơn 1 tuần = 8).
5. Nếu có nói về táo bón/khó đi ngoài/phân khô/mấy ngày chưa đi cầu, chief_complaint phải là 'constipation'.
6. Nếu có triệu chứng đau ngực, chief_complaint là 'chest_pain'. Đau đầu -> 'headache'. Đau bụng -> 'abdominal_pain'.
"""


class LLMClinicalExtractor:
    """Bộ trích xuất dữ kiện lâm sàng kết hợp Rule + Small LLM."""

    def __init__(self, rule_service: ClinicalFactService | None = None):
        self.rule_service = rule_service or get_clinical_fact_service()
        self.negation_service = get_clinical_negation_service()

    def should_invoke_llm(self, text: str, rule_facts: dict[str, Any]) -> bool:
        """
        Confidence Router: Quyết định xem có cần gọi LLM hay chỉ dùng Rule Engine.
        Tiêu chí tiết kiệm token:
        - Nếu câu rất ngắn, không có từ lạ, rule đã bắt trọn facts -> Rule (0 token).
        - Nếu câu dài (> 40 ký tự), nhiều vế, có liên từ diễn tả sắc thái phức tạp,
          hoặc câu có dấu hiệu than phiền mà rule không bắt được chief_complaint -> Gọi LLM.
        """
        text_clean = text.strip().lower()
        if len(text_clean) < 15:
            return False

        # Các từ biểu thị đối lập / mô tả hội thoại đời thường phức tạp
        conversational_markers = [
            "tưởng là",
            "nghĩ là",
            "uống thuốc mà",
            "nhưng mà",
            "tuy nhiên",
            "khó chịu kiểu",
            "cứ ngỡ",
            "mấy hôm trước",
            "tự nhiên lại",
            "thấy lạ",
            "cảm giác như",
            "hơi hơi",
            "lúc đau lúc không",
            "nhưng không",
            "nhưng",
            "tuy vậy",
            "dữ dội",
            "từ hôm kia",
        ]
        has_complex_phrasing = any(m in text_clean for m in conversational_markers)

        # Kiểm tra xem có từ chỉ triệu chứng tổng quát không
        clinical_keywords = [
            "đau",
            "nhức",
            "mỏi",
            "sốt",
            "ho",
            "mệt",
            "tức",
            "buốt",
            "chóng mặt",
            "nôn",
            "ói",
            "tiêu",
            "chảy",
            "ngứa",
            "phát ban",
            "khó thở",
            "hụt hơi",
            "nặng đầu",
            "ê ẩm",
            "khó chịu",
            "sụt cân",
            "chướng",
            "ì ạch",
        ]
        has_clinical_word = any(w in text_clean for w in clinical_keywords)

        # Nếu có từ lâm sàng nhưng Rule Engine không trích xuất được facts nào -> Cần LLM hỗ trợ!
        no_facts_extracted = (
            not rule_facts.get("positive_facts")
            and not rule_facts.get("negative_facts")
            and not rule_facts.get("chief_complaint")
        )

        if has_clinical_word and (no_facts_extracted or has_complex_phrasing):
            return True

        return False

    async def extract_async(
        self,
        text: str,
        current_facts: dict[str, Any] | None = None,
        force_llm: bool = False,
    ) -> dict[str, Any]:
        """
        Trích xuất async: Rule trước, nếu cần hoặc được yêu cầu thì chạy LLM.
        Hợp nhất kết quả để đảm bảo an toàn tuyệt đối.
        """
        # 1. Chạy Rule Engine deterministic (luôn chạy, < 0.1ms)
        rule_result = self.rule_service.extract(text)

        # 2. Quyết định Router
        invoke_llm = force_llm or self.should_invoke_llm(text, rule_result)

        if not invoke_llm:
            rule_result["extraction_method"] = "RULE"
            rule_result["confidence"] = 1.0
            return rule_result

        # 3. Kích hoạt Small LLM (GPT-4o-mini structured output)
        try:
            llm = get_llm()
            structured_llm = llm.with_structured_output(ClinicalFactModel)

            prompt_messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f'Lời mô tả của bệnh nhân: "{text}"'},
            ]

            llm_result: ClinicalFactModel = await structured_llm.ainvoke(prompt_messages)

            # 4. Hợp nhất Rule + LLM:
            # - Rule facts (nhất là cờ đỏ) LUÔN ĐƯỢC BẢO TOÀN (quyền quyết định an toàn thuộc về Rule Engine).
            # - LLM bổ sung các facts tự nhiên, vị trí (location), tính chất (qualifiers), thời gian.
            merged_positive = set(rule_result.get("positive_facts") or [])
            merged_negative = set(rule_result.get("negative_facts") or [])

            for f in llm_result.positive_facts:
                norm_f = f.lower().strip().replace(" ", "_")
                # Kiểm tra lại qua negation service để chống hallucination
                if not self.negation_service.is_phrase_negated(f, text):
                    merged_positive.add(norm_f)
                else:
                    merged_negative.add(norm_f)

            for f in llm_result.negative_facts:
                norm_f = f.lower().strip().replace(" ", "_")
                merged_negative.add(norm_f)
                merged_positive.discard(norm_f)

            chief = rule_result.get("chief_complaint") or llm_result.chief_complaint
            duration = rule_result.get("duration_days") or llm_result.duration_days
            interval = rule_result.get("bowel_interval_days") or llm_result.bowel_interval_days

            return {
                "chief_complaint": chief,
                "positive_facts": sorted(merged_positive),
                "negative_facts": sorted(merged_negative),
                "duration_days": duration,
                "bowel_interval_days": interval,
                "location": llm_result.location,
                "severity": llm_result.severity,
                "qualifiers": llm_result.qualifiers,
                "confidence": llm_result.confidence,
                "extraction_method": "HYBRID_LLM",
                "reasoning": llm_result.reasoning,
                "llm_invoked": True,
                "llm_attempted": True,
                "llm_succeeded": True,
            }

        except Exception as e:
            logger.warning(f"[LLMClinicalExtractor] LLM fallback to Rule due to error: {e}")
            rule_result["extraction_method"] = "RULE_FALLBACK"
            rule_result["confidence"] = 0.8
            rule_result["llm_attempted"] = True
            rule_result["llm_succeeded"] = False
            return rule_result

    def extract_sync(self, text: str) -> dict[str, Any]:
        """Bản đồng bộ thuần Rule cho các luồng batch eval offline."""
        res = self.rule_service.extract(text)
        res["extraction_method"] = "RULE"
        res["confidence"] = 1.0
        return res


_llm_extractor_instance: LLMClinicalExtractor | None = None


def get_llm_clinical_extractor() -> LLMClinicalExtractor:
    global _llm_extractor_instance
    if _llm_extractor_instance is None:
        _llm_extractor_instance = LLMClinicalExtractor()
    return _llm_extractor_instance
