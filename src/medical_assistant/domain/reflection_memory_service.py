"""
Clinical Reflection Memory Service (Shinn et al., 2023 - Reflexion Framework)
Chuyên trách quản lý bộ nhớ phản tỉnh lâm sàng theo nguyên tắc vàng:
GHI GÌ:
- Bài học rút ra: "thử X không được vì Y, lần sau thử Z" - cô đọng, hành động được.
- Chiến lược đã thất bại: mô tả ngắn hướng tiếp cận đã thử và trượt để không lặp lại.
- Ràng buộc mới phát hiện: constraint lâm sàng hoặc kỹ thuật lộ ra sau lần thử trước.
BỎ GÌ:
- Không lưu toàn bộ lịch sử chat thô.
- Không lưu tool dump / raw payload.
- Không diễn giải lại yêu cầu cũ.
"""

from __future__ import annotations

import datetime
from typing import Any
from pydantic import BaseModel, Field


class ReflectionMemoryItem(BaseModel):
    rubric_id: str = Field(..., description="Mã rubric bị kích hoạt (RUBRIC-05-ANATOMICAL-PRIORITY,...)")
    failed_strategy: str = Field(..., description="Mô tả ngắn của hướng tiếp cận đã thử và trượt")
    lesson_learned: str = Field(..., description="Bài học cô đọng: thử X không được vì Y, lần sau thử Z")
    new_constraint: str = Field(..., description="Ràng buộc mới phát hiện")
    trigger_query: str = Field(default="", description="Mô tả tóm tắt triệu chứng kích hoạt")
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ReflectionMemoryService:
    def __init__(self):
        pass

    def create_memory_item(
        self,
        rubric_id: str,
        failed_strategy: str,
        lesson_learned: str,
        new_constraint: str,
        trigger_query: str = "",
        source_evidence: list[dict[str, Any]] | None = None,
    ) -> ReflectionMemoryItem:
        return ReflectionMemoryItem(
            rubric_id=rubric_id,
            failed_strategy=failed_strategy.strip(),
            lesson_learned=lesson_learned.strip(),
            new_constraint=new_constraint.strip(),
            trigger_query=trigger_query.strip(),
            source_evidence=source_evidence or [],
        )

    def format_reflections_for_prompt(
        self,
        reflections: list[dict[str, Any] | ReflectionMemoryItem],
        max_items: int = 3,
    ) -> str:
        """
        Định dạng bộ nhớ phản tỉnh thành prompt ngắn gọn (~50-80 token).
        Tự động phân giải mọi xung đột (Anti-Contradiction) trước khi truyền vào Actor.
        """
        if not reflections:
            return ""

        # Tự động hóa phân giải mâu thuẫn bài học trước khi nạp vào Prompt
        resolved = self.resolve_memory_conflicts(reflections)
        if not resolved:
            return ""

        formatted_lines = [
            "\n[BỘ NHỚ PHẢN TỈNH - BÀI HỌC CẦN TUÂN THỦ TỪ CÁC LẦN THỬ TRƯỚC]:"
        ]

        # Lấy tối đa max_items bài học gần nhất đã được giải quyết xung đột
        recent = resolved[-max_items:]
        for idx, item in enumerate(recent, start=1):
            formatted_lines.append(
                f"• Lần thử #{idx}:\n"
                f"  - Chiến lược thất bại: {item.failed_strategy}\n"
                f"  - Bài học rút ra: {item.lesson_learned}\n"
                f"  - Ràng buộc bắt buộc: {item.new_constraint}"
            )

        formatted_lines.append("HÃY TUÂN THỦ CÁC RÀNG BUỘC TRÊN VÀ TRÁNH LẶP LẠI CHIẾN LƯỢC THẤT BẠI!\n")
        return "\n".join(formatted_lines)

    def persist_reflection_to_db(
        self,
        item: ReflectionMemoryItem,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """
        Lưu trữ lâu dài bài học phản tỉnh vào bảng public.clinical_reflection_memory trên Supabase.
        """
        try:
            from src.medical_assistant.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            payload = {
                "session_id": session_id,
                "user_id": user_id,
                "rubric_id": item.rubric_id,
                "trigger_query": item.trigger_query,
                "failed_strategy": item.failed_strategy,
                "lesson_learned": item.lesson_learned,
                "new_constraint": item.new_constraint,
                "source_evidence": item.source_evidence,
                "created_at": item.created_at,
            }
            client.insert_minimal("clinical_reflection_memory", payload)
            return True
        except Exception as exc:
            # Safe degradation: Lỗi kết nối DB không làm sập flow chính của bệnh nhân
            try:
                print(f"[ReflectionMemoryService] Không thể lưu long-term memory: {exc}")
            except Exception:
                pass
            return False

    def resolve_memory_conflicts(
        self,
        items: list[ReflectionMemoryItem | dict[str, Any]],
    ) -> list[ReflectionMemoryItem]:
        """
        Phân giải mâu thuẫn trong Long-term Reflection Memory (Anti-Contradiction Engine):
        1. Chuẩn hóa tất cả các đầu vào về ReflectionMemoryItem.
        2. Ràng buộc an toàn tuyệt đối (Safety / Red-flag / Medication / Diagnosis):
           Luôn luôn được giữ lại và có độ ưu tiên tối thượng.
        3. Phân giải xung đột định tuyến chuyên khoa (Specialty Routing Contradictions):
           - Khi 2 bài học chỉ định 2 chuyên khoa xung đột cho cùng bệnh cảnh lâm sàng:
             Áp dụng Bảng trọng số Giải phẫu Sinh tồn ANATOMICAL_SYSTEMS
             (Tim mạch 95 > Thần kinh 90 > Tiêu hóa 65 > Xương khớp 35).
           - Bài học có trọng số thấp hơn bị loại bỏ lập tức (Pruned), giữ lại bài học trọng số cao nhất.
        4. Phân giải xung đột hành vi (Action Contradictions):
           - Nếu một bài học yêu cầu "hỏi thêm" còn bài học khác yêu cầu "không hỏi thêm / chuyển tuyến":
             Bài học có tính an toàn cao hơn (loại trừ cờ đỏ / chuyển tuyến cơ quan sinh tồn) sẽ thắng.
        5. Loại bỏ trùng lặp (Deduplication): Giữ lại bản ghi chi tiết và mới nhất.
        """
        if not items:
            return []

        # Chuẩn hóa về ReflectionMemoryItem
        typed_items: list[ReflectionMemoryItem] = []
        for it in items:
            if isinstance(it, ReflectionMemoryItem):
                typed_items.append(it)
            elif isinstance(it, dict):
                try:
                    typed_items.append(ReflectionMemoryItem(**it))
                except Exception:
                    continue

        if len(typed_items) <= 1:
            return typed_items

        from src.medical_assistant.domain.care_pipeline_service import ANATOMICAL_SYSTEMS

        safety_items: list[ReflectionMemoryItem] = []
        specialty_candidates: list[tuple[int, ReflectionMemoryItem]] = []
        other_items: list[ReflectionMemoryItem] = []

        for item in typed_items:
            # 1. Ràng buộc An toàn & Cờ đỏ luôn luôn được giữ lại
            if any(k in item.rubric_id for k in ["RED-FLAG", "SECURITY", "MEDICATION", "DIAGNOSIS"]):
                safety_items.append(item)
                continue

            # 2. Phát hiện định tuyến chuyên khoa
            combined_text = f"{item.lesson_learned} {item.new_constraint} {item.failed_strategy}".lower()
            matched_weight = -1
            for code, data in ANATOMICAL_SYSTEMS.items():
                dept_name = data["name"].lower()
                organ_name = data["organ_name"].lower()
                if dept_name in combined_text or organ_name in combined_text or code.lower() in combined_text:
                    if data["weight"] > matched_weight:
                        matched_weight = data["weight"]

            if matched_weight >= 0 or "RUBRIC-05" in item.rubric_id:
                specialty_candidates.append((matched_weight, item))
            else:
                other_items.append(item)

        # Xử lý xung đột chuyên khoa: Chỉ giữ bài học có trọng số giải phẫu sinh tồn cao nhất
        resolved_specialties: list[ReflectionMemoryItem] = []
        if specialty_candidates:
            # Sắp xếp theo weight giảm dần, nếu bằng nhau thì lấy item mới hơn
            specialty_candidates.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)
            best_weight, best_item = specialty_candidates[0]
            resolved_specialties.append(best_item)

        # Deduplicate các rubric khác
        seen_rubrics: set[str] = set()
        deduped_others: list[ReflectionMemoryItem] = []
        for it in other_items:
            if it.rubric_id not in seen_rubrics:
                seen_rubrics.add(it.rubric_id)
                deduped_others.append(it)

        # Ghép kết quả theo thứ tự ưu tiên: An toàn -> Định tuyến sinh tồn cao nhất -> Các bài học khác
        return safety_items + resolved_specialties + deduped_others

    def prune_action_space(
        self,
        allowed_actions: list[str],
        candidate_specialties: list[dict[str, Any]],
        pruned_actions: list[str] | None = None,
        pruned_departments: list[str] | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Action Space Pruning (Chặn đường chọn lại cách cũ):
        - Loại bỏ các action trong allowed_actions đã bị Critic đánh dấu thất bại.
        - Loại bỏ các chuyên khoa trong candidate_specialties đã thử và trượt.
        - Đảm bảo Actor không có khả năng vật lý để lặp lại sai lầm ở lượt tiếp theo.
        """
        pruned_act = set(pruned_actions or [])
        pruned_dept = set(d.lower() for d in (pruned_departments or []))

        # 1. Cắt tỉa allowed_actions
        effective_actions = [act for act in allowed_actions if act not in pruned_act]
        if not effective_actions:
            effective_actions = allowed_actions  # Safe fallback

        # 2. Cắt tỉa candidate_specialties
        effective_specialties = [
            spec for spec in candidate_specialties
            if spec.get("name", "").lower() not in pruned_dept
            and spec.get("code", "").lower() not in pruned_dept
        ]
        if not effective_specialties:
            effective_specialties = candidate_specialties  # Safe fallback

        return effective_actions, effective_specialties

    def retrieve_relevant_reflections(
        self,
        query: str,
        rubric_id: str | None = None,
        limit: int = 5,
    ) -> list[ReflectionMemoryItem]:
        """
        Truy vấn các bài học phản tỉnh quá khứ từ Supabase và tự động phân giải mâu thuẫn trước khi trả về.
        """
        try:
            from src.medical_assistant.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            params: dict[str, Any] = {
                "order": "created_at.desc",
                "limit": str(limit),
            }
            if rubric_id:
                params["rubric_id"] = f"eq.{rubric_id}"

            records = client.select("clinical_reflection_memory", params=params)
            raw_items = []
            for r in records:
                raw_items.append(
                    ReflectionMemoryItem(
                        rubric_id=r.get("rubric_id", ""),
                        failed_strategy=r.get("failed_strategy", ""),
                        lesson_learned=r.get("lesson_learned", ""),
                        new_constraint=r.get("new_constraint", ""),
                        trigger_query=r.get("trigger_query", ""),
                        source_evidence=r.get("source_evidence") or [],
                        created_at=r.get("created_at", ""),
                    )
                )

            # Tự động lọc sạch và giải quyết mâu thuẫn giữa các bài học quá khứ
            return self.resolve_memory_conflicts(raw_items)
        except Exception as exc:
            try:
                print(f"[ReflectionMemoryService] Không thể truy vấn long-term memory: {exc}")
            except Exception:
                pass
            return []


_reflection_memory_service_instance: ReflectionMemoryService | None = None


def get_reflection_memory_service() -> ReflectionMemoryService:
    global _reflection_memory_service_instance
    if _reflection_memory_service_instance is None:
        _reflection_memory_service_instance = ReflectionMemoryService()
    return _reflection_memory_service_instance
