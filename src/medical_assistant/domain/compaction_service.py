"""Clinical Compaction Service: Nén lịch sử hội thoại thành SOAP Durable Note.

Thực hiện nguyên tắc Compaction + Notes:
- Duy trì 3-4 tin nhắn gần nhất trong Recent Context để giữ văn phong và đại từ chỉ định.
- Nén toàn bộ phần lịch sử cũ hơn thành cấu trúc SOAP (Subjective, Objective, Assessment, Plan)
  đóng vai trò mỏ neo lâm sàng bền vững (Durable Clinical Note).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COMPACTION_THRESHOLD_MESSAGES = 4  # Khi tổng tin nhắn vượt quá 4 tin, kích hoạt compaction


class CompactionService:
    def __init__(self, threshold: int = COMPACTION_THRESHOLD_MESSAGES):
        self.threshold = threshold

    def compact_conversation(
        self,
        messages: list[dict[str, Any]],
        state: dict[str, Any],
        recent_window_size: int = 4,
    ) -> dict[str, Any]:
        """
        Nén danh sách messages và cập nhật durable_soap_note.
        Trả về dict gồm:
        - recent_messages: 3-4 tin nhắn gần nhất
        - durable_soap_note: Tóm tắt SOAP tích lũy
        - compaction_performed: bool
        """
        if not messages or len(messages) <= self.threshold:
            return {
                "recent_messages": messages,
                "durable_soap_note": state.get("durable_soap_note") or "",
                "compaction_performed": False,
            }

        # Tách tin nhắn cũ cần nén và tin nhắn gần nhất
        older_messages = messages[:-recent_window_size]
        recent_messages = messages[-recent_window_size:]

        # Thu thập dữ liệu lâm sàng từ state để lập bản ghi SOAP bền vững
        clinical_facts = state.get("clinical_facts") or {}
        chief_complaint = (
            clinical_facts.get("chief_complaint")
            or " ".join(state.get("collected_details") or [])
            or (state.get("symptoms")[0] if state.get("symptoms") else "Chưa ghi nhận rõ triệu chứng")
        )
        positive_facts = clinical_facts.get("positive_facts") or []
        facts_str = ", ".join(positive_facts) if positive_facts else "Không có dấu hiệu bất thường cấp tính kèm theo"

        dept_name = state.get("suggested_department_name") or "Đang định hướng chuyên khoa"
        ats_level = state.get("ats_level") or 4
        urgency_tier = state.get("urgency_tier") or "STANDARD"
        facility = state.get("facility_preference") or "Chưa chọn cơ sở"
        pref_date = state.get("preferred_date") or "Linh hoạt"
        workflow_status = state.get("workflow_status") or "IN_PROGRESS"

        # Tổng hợp các yêu cầu từ tin nhắn cũ của người dùng
        user_queries_summary = []
        for msg in older_messages:
            role = msg.get("role") or msg.get("type")
            content = msg.get("content") or msg.get("text") or ""
            if role in ("user", "human") and content:
                # Cắt ngắn dòng để tránh phình token
                clean_c = content.strip().replace("\n", " ")
                if len(clean_c) > 100:
                    clean_c = clean_c[:97] + "..."
                user_queries_summary.append(clean_c)

        queries_bullet = " | ".join(user_queries_summary) if user_queries_summary else "Hội thoại ban đầu"

        # Soạn thảo SOAP Note
        soap_lines = [
            "📋 **[DURABLE CLINICAL NOTE - TÓM TẮT LÂM SÀNG BỀN VỮNG]**",
            f"• **S (Subjective - Triệu chứng):** {chief_complaint}. Ghi nhận các yêu cầu trước: [{queries_bullet}]",
            f"• **O (Objective - Định hướng):** Chuyên khoa: **{dept_name}** | ATS Level: {ats_level} ({urgency_tier}) | Dấu hiệu: {facts_str}",
            f"• **A (Assessment - Sở thích khám):** Cơ sở: **{facility}** | Thời gian mong muốn: **{pref_date}**",
            f"• **P (Plan - Kế hoạch):** Tiến trình: {workflow_status}. Tiếp tục xử lý yêu cầu ở lượt gần nhất.",
        ]

        new_soap_note = "\n".join(soap_lines)
        logger.info("Compacted %d messages into SOAP durable note. Preserved %d recent messages.", len(older_messages), len(recent_messages))

        return {
            "recent_messages": recent_messages,
            "durable_soap_note": new_soap_note,
            "compaction_performed": True,
        }


_compaction_service: CompactionService | None = None


def get_compaction_service() -> CompactionService:
    global _compaction_service
    if _compaction_service is None:
        _compaction_service = CompactionService()
    return _compaction_service
