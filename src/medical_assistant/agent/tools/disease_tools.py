"""Read-only tool for searching disease pathology and educational clinical knowledge."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.medical_assistant.agent.tools.base import ToolExecutionError, normalize_fold
from src.medical_assistant.domain.triage_service import get_triage_service
from src.medical_assistant.rag.store_cache import get_global_rag_store

logger = logging.getLogger(__name__)


class SearchDiseaseKnowledgeInput(BaseModel):
    query: str = Field(
        ...,
        description="Từ khóa triệu chứng hoặc tên mặt bệnh cần tra cứu (VD: 'viêm loét dạ dày', 'sốt xuất huyết', 'đau nửa đầu', 'hen phế quản')",
    )
    limit: int = Field(
        default=3,
        ge=1,
        le=3,
        description="Số lượng mặt bệnh tối đa cần tìm (từ 1 đến 3)",
    )


@tool("search_disease_knowledge", args_schema=SearchDiseaseKnowledgeInput)
def search_disease_knowledge(
    query: str,
    limit: int = 3,
) -> dict[str, Any]:
    """Tra cứu kiến thức bệnh học, triệu chứng phân tầng và chuyên khoa tiếp nhận từ cơ sở dữ liệu lâm sàng 741 mặt bệnh và Datalake y khoa.

    Dùng khi người dùng hỏi về thông tin một căn bệnh, triệu chứng điển hình, dấu hiệu cảnh báo của bệnh.
    Lưu ý: Chỉ cung cấp thông tin định hướng tham khảo giáo dục y tế, không dùng để khẳng định chẩn đoán.
    """
    try:
        query_raw = str(query or "").strip()
        limit = max(1, min(limit, 3))

        if not query_raw:
            return {
                "found": False,
                "query": "",
                "diseases": [],
                "reason": "Từ khóa tra cứu bệnh học không được để trống.",
                "source": "disease_triage",
            }

        q_fold = normalize_fold(query_raw)
        q_tokens = [t for t in q_fold.split() if len(t) >= 2]

        triage_service = get_triage_service()
        scored_diseases: list[tuple[int, Any]] = []

        # 1. Tra cứu trên kho 741 mặt bệnh đã chuẩn hóa (Supabase + Datalake)
        for _, rec in triage_service.diseases.items():
            name_fold = normalize_fold(rec.name)
            score = 0

            # So khớp chính xác hoặc chứa toàn bộ cụm từ
            if q_fold in name_fold:
                score += 15
            elif name_fold in q_fold:
                score += 10

            # So khớp từng từ khóa trong tên bệnh
            token_matches = sum(1 for t in q_tokens if t in name_fold)
            score += token_matches * 3

            # So khớp trong triệu chứng điển hình & dấu hiệu cảnh báo
            symptoms_text = normalize_fold(
                " ".join(
                    [
                        *rec.symptom_hierarchy.typical_or_mild,
                        *rec.symptom_hierarchy.warning_signs,
                        *rec.symptom_hierarchy.red_flags,
                    ]
                )
            )
            if q_fold in symptoms_text:
                score += 5
            score += sum(1 for t in q_tokens if t in symptoms_text)

            if score > 0:
                scored_diseases.append((score, rec))

        scored_diseases.sort(key=lambda item: item[0], reverse=True)

        matched_records = []
        for _, rec in scored_diseases[:limit]:
            matched_records.append(
                {
                    "disease_key": rec.disease_key,
                    "disease_name": rec.name,
                    "primary_specialty_name": rec.primary_specialty_name,
                    "primary_specialty_code": rec.primary_specialty_code,
                    "ats_level": rec.acuity.ats_level.value,
                    "urgency_tier": rec.acuity.urgency_tier.value,
                    "max_booking_days": rec.acuity.max_booking_days,
                    "typical_symptoms": rec.symptom_hierarchy.typical_or_mild[:5],
                    "warning_signs": rec.symptom_hierarchy.warning_signs[:3],
                    "red_flags": rec.symptom_hierarchy.red_flags[:3],
                    "probing_questions": rec.probing_questions[:2],
                    "source": "supabase.disease_triage / datalake.diseases_triaged.jsonl",
                }
            )

        # 2. Bổ sung từ RAG store nếu chưa đủ
        rag_passages = []
        try:
            rag_store = get_global_rag_store()
            rag_passages = rag_store.search(query_raw, limit=limit, categories={"disease_education"})
        except Exception as exc:
            logger.debug("RAG disease search optional fallback notice: %s", exc)

        rag_snippets = [
            {
                "title": p.title,
                "summary": p.text[:400] + ("..." if len(p.text) > 400 else ""),
                "source": p.source_url or "datalake.disease_education",
            }
            for p in rag_passages[:limit]
            if p.text.strip()
        ]

        if not matched_records and not rag_snippets:
            return {
                "found": False,
                "query": query_raw,
                "diseases": [],
                "reason": f"Không tìm thấy thông tin bệnh học phù hợp với từ khóa '{query_raw}' trong cơ sở dữ liệu 741 mặt bệnh.",
                "source": "supabase.disease_triage / datalake",
            }

        return {
            "found": True,
            "query": query_raw,
            "count": len(matched_records),
            "diseases": matched_records,
            "educational_references": rag_snippets,
            "disclaimer": (
                "Khuyến cáo y tế: Thông tin chỉ mang tính chất định hướng và hỗ trợ đặt lịch khám, "
                "không thay thế cho chẩn đoán hoặc chỉ định điều trị của bác sĩ chuyên khoa."
            ),
            "source": "supabase.disease_triage / datalake.diseases_triaged.jsonl",
        }
    except Exception as exc:
        logger.error("Error in search_disease_knowledge tool: %s", exc, exc_info=True)
        return {
            "found": False,
            "query": str(query or "").strip() if "query" in locals() else "",
            "diseases": [],
            "data_unavailable": True,
            "reason": f"Lỗi kết nối hoặc không thể tra cứu kiến thức bệnh học: {exc}",
            "source": "supabase.disease_triage / datalake.diseases_triaged.jsonl",
        }
