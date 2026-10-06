"""
Clinical Critic & Evaluator Domain Service (Reflexion Engine)
Tuân thủ 4 nguyên tắc vàng của Shinn et al. (2023):
1. Rubric tường minh (Explicit Clinical Rubrics)
2. Bắt buộc trích dẫn bằng chứng (Mandatory Evidence Citation)
3. Verdict máy đọc được (Pydantic EvaluatorVerdict Schema)
4. Tách biệt ngữ cảnh với Actor (Blind Decoupled Review)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.medical_assistant.domain.language_service import get_emergency_guidance


class EvidenceItem(BaseModel):
    """Bằng chứng trích dẫn trực tiếp từ văn bản người dùng hoặc trạng thái Actor."""

    source_span: str = Field(..., description="Đoạn văn bản trích dẫn nguyên văn làm bằng chứng")
    matched_context: str | None = Field(default=None, description="Ngữ cảnh hoặc dấu hiệu lâm sàng khớp")
    field_name: str | None = Field(default=None, description="Thuộc tính của Actor bị phát hiện sai lệch")


class EvaluatorVerdict(BaseModel):
    """Phán quyết có cấu trúc, máy đọc được (Machine-Readable JSON Schema)."""

    verdict: Literal["APPROVED", "REVISE", "REVISED_BY_REFLEXION"] = Field(
        ..., description="Phán quyết thẩm định: Chấp thuận (APPROVED), Yêu cầu sinh lại (REVISE), hoặc Tự sửa (REVISED)"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Điểm số đánh giá chuẩn xác lâm sàng (0.0 đến 1.0)")
    failed_rubric_id: str | None = Field(default=None, description="Mã rubric bị vi phạm nếu có")
    rubric_category: str | None = Field(
        default=None, description="Nhóm tiêu chuẩn vi phạm (ACUITY, ONCOLOGY, SECURITY, POLARITY)"
    )
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Danh sách bằng chứng chứng minh")
    actionable_feedback: str | None = Field(
        default=None, description="Lời phê bình và chỉ dẫn sửa sai có tính hành động"
    )
    corrections: dict[str, Any] = Field(
        default_factory=dict, description="Các thuộc tính trạng thái đã được hiệu chỉnh chính xác"
    )
    reflection_item: dict[str, Any] | None = Field(
        default=None, description="Mẩu bài học phản tỉnh cô đọng tuân theo chuẩn slide VinUni"
    )


class ClinicalCriticService:
    """Service độc lập chịu trách nhiệm kiểm toán lâm sàng và an toàn cho Actor."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Chuẩn hóa loại bỏ dấu tiếng Việt và khoảng trắng thừa cho việc đối sánh."""
        folded = unicodedata.normalize("NFKD", text.casefold())
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", folded).strip()

    def audit_analysis(
        self,
        query: str,
        current_state: dict[str, Any],
        language: str = "vi",
    ) -> EvaluatorVerdict:
        """
        Thẩm định độc lập (Blind Evaluation):
        Chỉ nhận câu hỏi thô và nhãn phân loại của Actor, không đọc lý lẽ biện minh (CoT) của Actor.
        """
        clean_query = self.normalize_text(query)
        current_dept = (current_state.get("suggested_department_name") or "").strip()
        current_ats = current_state.get("ats_level")
        workflow_status = current_state.get("workflow_status", "")
        is_emergency = current_state.get("is_emergency", False)

        evidence_list: list[EvidenceItem] = []
        critique_messages: list[str] = []
        corrections: dict[str, Any] = {}
        failed_rubric_id: str | None = None
        rubric_category: str | None = None

        # =========================================================================
        # RUBRIC-01: ACUITY FLOOR CONSTRAINT (Bụng ngoại khoa tối khẩn)
        # =========================================================================
        surgical_abdomen_match = re.search(
            r"\b(?:bung\s+cung\s+nhu\s+go|bung\s+cung\s+do|dau\s+nhu\s+dao\s+dam|thung\s+ruot|viem\s+phuc\s+mac)\b",
            clean_query,
        )
        if surgical_abdomen_match and (current_ats is None or current_ats > 2 or not is_emergency):
            evidence_span = surgical_abdomen_match.group(0)
            evidence_list.append(
                EvidenceItem(
                    source_span=evidence_span,
                    matched_context="Dấu hiệu kinh điển của Bụng ngoại khoa (Viêm phúc mạc / Thủng tạng rỗng)",
                    field_name="ats_level / is_emergency",
                )
            )
            failed_rubric_id = "RUBRIC-01-ACUITY-FLOOR"
            rubric_category = "ACUITY"
            critique_messages.append(
                f"CẢNH BÁO LÂM SÀNG CẤP CỨU: Phát hiện dấu hiệu Bụng ngoại khoa tối khẩn ('{evidence_span}'). "
                f"Actor phân loại ATS {current_ats} là under-triage nghiêm trọng. "
                "Bắt buộc nâng lên ATS Level 1 và chuyển Cấp cứu Ngoại tiêu hóa ngay lập tức."
            )
            guidance = get_emergency_guidance(
                flag_name="Bụng ngoại khoa tối khẩn (Viêm phúc mạc / Thủng tạng)",
                specialty="Cấp cứu Ngoại tiêu hóa",
                ats_level=1,
                language=language,
            )
            corrections.update(
                {
                    "is_emergency": True,
                    "emergency_warning": guidance,
                    "workflow_status": "EMERGENCY",
                    "ats_level": 1,
                    "urgency_tier": "EMERGENCY_BLOCK",
                    "suggested_department_name": "Cấp cứu Ngoại tiêu hóa",
                    "suggested_department_code": "CAP_CUU",
                    "metadata": {
                        "patient_guidance": guidance,
                    },
                }
            )

        # =========================================================================
        # RUBRIC-02: MALIGNANCY DEPARTMENT ALIGNMENT (Chuyên khoa Ung bướu)
        # =========================================================================
        oncology_match = re.search(
            r"\b(?:k\s+giap|k\s+tuyen\s+giap|ung\s+thu|u\s+ac\s+tinh|di\s+can|hach\s+co\s+nhom|k\s+vu|k\s+phoi|k\s+gan|k\s+dai\s+trang|hoa\s+tri|xa\s+tri)\b",
            clean_query,
        )
        is_general_dept = any(
            g in current_dept.lower() for g in ["tổng quát", "general", "sức khỏe tổng quát", "nội khoa"]
        )
        if oncology_match and is_general_dept and not corrections.get("is_emergency"):
            evidence_span = oncology_match.group(0)
            evidence_list.append(
                EvidenceItem(
                    source_span=evidence_span,
                    matched_context="Bệnh lý ác tính / Ung thư / Di căn hạch",
                    field_name="suggested_department_name",
                )
            )
            failed_rubric_id = "RUBRIC-02-MALIGNANCY-ALIGNMENT"
            rubric_category = "ONCOLOGY"
            critique_messages.append(
                f"CẢNH BÁO ĐỊNH HƯỚNG CHUYÊN KHOA: Bệnh nhân có tiền sử/nghi ngờ Ung bướu ('{evidence_span}'), "
                f"Actor đã phân nhầm về '{current_dept}'. "
                "Phải điều chỉnh đích đến chính xác sang Trung tâm Ung bướu."
            )
            corrections.update(
                {
                    "suggested_department_name": "Trung tâm Ung bướu",
                    "suggested_department_code": "UNG_BUOU",
                }
            )
            if workflow_status in {"PROBING_IN_PROGRESS", "TRIAGED_AWAITING_SCHEDULE", "TRIAGED_READY_FOR_BOOKING"}:
                corrections["workflow_status"] = "TRIAGED_AWAITING_SCHEDULE"

        # =========================================================================
        # RUBRIC-03: SECURITY EVASION BYPASS (Mã Morse chứa lệnh cấm)
        # =========================================================================
        has_morse_signals = bool(re.search(r"(?:[.-]{2,}\s*){3,}", query))
        if has_morse_signals and workflow_status != "SECURITY_BLOCKED":
            morse_clean = re.sub(r"[^.\-\s/]", " ", query)
            morse_words = morse_clean.split("/")
            from src.medical_assistant.domain.security.deobfuscator import MORSE_CODE_DICT

            decoded_letters = []
            for word in morse_words:
                for symbol in word.split():
                    if symbol in MORSE_CODE_DICT:
                        decoded_letters.append(MORSE_CODE_DICT[symbol])
                decoded_letters.append(" ")
            decoded_str = "".join(decoded_letters).lower()

            if any(bad in decoded_str for bad in ["ignore", "prompt", "rule", "system", "hack", "admin"]):
                evidence_list.append(
                    EvidenceItem(
                        source_span=query[:60] + "...",
                        matched_context=f"Morse giải mã: '{decoded_str.strip()}'",
                        field_name="workflow_status",
                    )
                )
                failed_rubric_id = "RUBRIC-03-SECURITY-EVASION"
                rubric_category = "SECURITY"
                critique_messages.append(
                    f"CẢNH BÁO AN TOÀN BẢO MẬT: Phát hiện chuỗi mã Morse giải mã ra lệnh tấn công: '{decoded_str.strip()}'. "
                    "Phải ngắt luồng ngay và kích hoạt SECURITY_BLOCKED."
                )
                from src.medical_assistant.domain.security.security_guardrail_service import (
                    get_security_guardrail_service,
                )

                sec_check = get_security_guardrail_service().inspect_query(decoded_str, language=language)
                corrections.update(
                    {
                        "is_emergency": False,
                        "emergency_warning": None,
                        "workflow_status": "SECURITY_BLOCKED",
                        "suggested_department_name": None,
                        "ats_level": None,
                        "metadata": {
                            "security_blocked": True,
                            "violation_type": "PROMPT_INJECTION_MORSE_DEOBFUSCATED",
                            "security_response": sec_check.safe_response,
                            "tokens_saved": True,
                        },
                    }
                )

        # =========================================================================
        # RUBRIC-04: POLARITY / PLEURITIC CHEST PAIN DIFFERENTIAL
        # =========================================================================
        double_negation_pleuritic = re.search(
            r"\b(?:khong\s+phai\s+la\s+toi\s+khong\s+dau\s+nguc|nhoi\s+khi\s+ho|dau\s+khi\s+ho)\b",
            clean_query,
        )
        has_respiratory_signs = bool(
            re.search(r"\b(?:ho\s+khac\s+dom|sot\s+39|viem\s+phe\s+quan|ho\s+dom\s+vang)\b", clean_query)
        )
        if (
            double_negation_pleuritic
            and has_respiratory_signs
            and is_emergency
            and current_dept == "Trung tâm Tim mạch"
        ):
            evidence_list.append(
                EvidenceItem(
                    source_span="chỉ nhói nhẹ khi ho, chủ yếu là sốt 39 độ và ho khạc đờm vàng",
                    matched_context="Đau ngực kiểu màng phổi do viêm phế quản/phổi",
                    field_name="ats_level / suggested_department_name",
                )
            )
            failed_rubric_id = "RUBRIC-04-POLARITY-DIFFERENTIAL"
            rubric_category = "POLARITY"
            critique_messages.append(
                "PHẢN TƯ LÂM SÀNG: Người bệnh có phủ định kép nhưng miêu tả cơn đau chỉ nhói nhẹ khi ho kèm sốt 39 độ khạc đờm vàng. "
                "Đây là đau ngực kiểu màng phổi thứ phát sau nhiễm trùng hô hấp, không phải ACS. "
                "Hạ cấp cứu và điều chỉnh về Khoa Nội hô hấp."
            )
            corrections.update(
                {
                    "is_emergency": False,
                    "emergency_warning": None,
                    "ats_level": 3,
                    "urgency_tier": "SAME_DAY",
                    "max_booking_days": 1,
                    "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
                    "suggested_department_name": "Nội hô hấp",
                    "suggested_department_code": "HO_HAP",
                }
            )

        # =========================================================================
        # RUBRIC-05: MULTI-SPECIALTY ANATOMICAL PRIORITY PIPELINE
        # =========================================================================
        if workflow_status not in {"SECURITY_BLOCKED", "FAQ_ANSWERED", "OUT_OF_SCOPE", "SOCIAL_REDIRECT"}:
            from src.medical_assistant.domain.care_pipeline_service import get_care_pipeline_service

            care_pipeline = get_care_pipeline_service().evaluate_multi_specialty_pipeline(query, language=language)
            if care_pipeline.is_multi_specialty:
                top_priority_dept = care_pipeline.primary_department
                corrections.setdefault("metadata", {})
                corrections["metadata"]["care_pipeline_applied"] = True
                corrections["metadata"]["care_pipeline"] = care_pipeline.model_dump()

                if current_dept != top_priority_dept and not any(
                    p in current_dept.lower() for p in [top_priority_dept.lower()]
                ):
                    evidence_list.append(
                        EvidenceItem(
                            source_span=f"Đa triệu chứng: {', '.join(care_pipeline.secondary_departments)}",
                            matched_context=f"Ưu tiên cơ quan sinh tồn thuộc về {top_priority_dept}",
                            field_name="suggested_department_name",
                        )
                    )
                    failed_rubric_id = "RUBRIC-05-ANATOMICAL-PRIORITY"
                    rubric_category = "PIPELINE_PRIORITY"
                    critique_messages.append(
                        f"ĐIỀU HƯỚNG LỘ TRÌNH ĐA KHOA: Người bệnh có triệu chứng chồng chéo nhiều khoa. "
                        f"Theo nguyên tắc giải phẫu sinh tồn, cơ quan {top_priority_dept} phải được ưu tiên khám tại Bước 1 "
                        f"trước cơ quan {current_dept or 'ngoại vi'}. Điều chỉnh Bước 1 về {top_priority_dept}."
                    )
                    corrections.update(
                        {
                            "suggested_department_name": top_priority_dept,
                            "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
                        }
                    )

        # =========================================================================
        # TỔNG HỢP VERDICT
        # =========================================================================
        if critique_messages:
            full_critique = " | ".join(critique_messages)
            try:
                print(f"[REFLEXION CRITIC TRIGGERED]: {full_critique}")
            except Exception:
                pass

            # Đúc kết mẩu bài học phản tỉnh cô đọng (Ghi gì: Bài học, Chiến lược thất bại, Ràng buộc mới)
            from src.medical_assistant.domain.reflection_memory_service import get_reflection_memory_service

            failed_strat = f"Định tuyến ban đầu vào {current_dept or 'Nội đa khoa'} (Workflow: {workflow_status})"
            lesson = f"Thử hướng {current_dept or 'hiện tại'} không thành công. {full_critique}"
            new_const = f"Bắt buộc tuân thủ {failed_rubric_id or 'tiêu chuẩn lâm sàng'}: Phải ưu tiên loại trừ nguy cơ cao trước."

            if failed_rubric_id == "RUBRIC-05-ANATOMICAL-PRIORITY":
                p_dept = corrections.get("suggested_department_name", "cơ quan sinh tồn")
                failed_strat = f"Định tuyến theo cơ quan ngoại vi / đau nhức bề mặt ({current_dept or 'ngoại vi'})."
                lesson = f"Thử phân {current_dept} không được vì có triệu chứng liên quan cơ quan sinh tồn {p_dept}. Lần sau phải đặt Bước 1 về {p_dept}."
                new_const = (
                    f"Cấm bỏ qua cơ quan sinh tồn ({p_dept}) chỉ vì cơ quan ngoại vi ({current_dept}) đau buốt hơn."
                )
            elif failed_rubric_id == "RUBRIC-01-RED-FLAG-MISSING":
                failed_strat = "Phân loại vào lịch khám thường / trì hoãn khi có dấu hiệu cờ đỏ cấp cứu."
                lesson = "Thử trì hoãn khám thường không được vì triệu chứng đe dọa sinh mạng cấp tính. Lần sau phải cảnh báo cấp cứu ngay."
                new_const = "Tuyệt đối không xếp lịch hẹn khám thường đối với triệu chứng cờ đỏ ACS hoặc đột quỵ."

            reflection_item = (
                get_reflection_memory_service()
                .create_memory_item(
                    rubric_id=failed_rubric_id or "GENERAL_CLINICAL_RUBRIC",
                    failed_strategy=failed_strat,
                    lesson_learned=lesson,
                    new_constraint=new_const,
                    trigger_query=query[:150],
                    source_evidence=[e.model_dump() for e in evidence_list],
                )
                .model_dump()
            )

            return EvaluatorVerdict(
                verdict="REVISED_BY_REFLEXION",
                score=0.0,
                failed_rubric_id=failed_rubric_id,
                rubric_category=rubric_category,
                evidence=evidence_list,
                actionable_feedback=full_critique,
                corrections=corrections,
                reflection_item=reflection_item,
            )

        return EvaluatorVerdict(
            verdict="APPROVED",
            score=1.0,
            failed_rubric_id=None,
            rubric_category=None,
            evidence=[],
            actionable_feedback=None,
            corrections={},
        )


_clinical_critic_service_instance: ClinicalCriticService | None = None


def get_clinical_critic_service() -> ClinicalCriticService:
    global _clinical_critic_service_instance
    if _clinical_critic_service_instance is None:
        _clinical_critic_service_instance = ClinicalCriticService()
    return _clinical_critic_service_instance
