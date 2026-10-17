"""
Unit & Integration Tests for Production Reflexion Features:
1. Action Space Pruning (Chặn đường chọn lại cách cũ)
2. Memory Conflict Resolution in Long-term Memory (Phân giải mâu thuẫn bài học)
"""

import pytest
from src.medical_assistant.domain.reflection_memory_service import (
    ReflectionMemoryItem,
    get_reflection_memory_service,
)
from src.medical_assistant.domain.clinical_critic_service import get_clinical_critic_service


def test_action_space_pruning():
    service = get_reflection_memory_service()
    
    allowed_actions = [
        "clarify_visit_purpose",
        "ask_clarifying_question",
        "suggest_specialty",
        "search_available_slot",
        "hold_slot",
    ]
    candidate_specialties = [
        {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
        {"code": "TIEU_HOA", "name": "Khoa Tiêu hóa - Gan mật"},
        {"code": "XUONG_KHOP", "name": "Khoa Chấn thương chỉnh hình"},
    ]
    
    # Giả lập: Critic đã reject Tiêu hóa và hành động search_available_slot
    pruned_actions = ["search_available_slot", "hold_slot"]
    pruned_departments = ["Khoa Tiêu hóa - Gan mật", "TIEU_HOA"]
    
    eff_actions, eff_specs = service.prune_action_space(
        allowed_actions=allowed_actions,
        candidate_specialties=candidate_specialties,
        pruned_actions=pruned_actions,
        pruned_departments=pruned_departments,
    )
    
    # 1. Action đã bị loại bỏ hoàn toàn khỏi allowed_actions
    assert "search_available_slot" not in eff_actions
    assert "hold_slot" not in eff_actions
    assert "suggest_specialty" in eff_actions
    
    # 2. Chuyên khoa đã trượt bị loại bỏ khỏi candidate_specialties
    remaining_codes = [s["code"] for s in eff_specs]
    assert "TIEU_HOA" not in remaining_codes
    assert "TIM_MACH" in remaining_codes
    assert "XUONG_KHOP" in remaining_codes
    print("\n[PASS] Test Action Space Pruning: Allowed actions & candidate specialties pruned successfully!")


def test_memory_conflict_resolution():
    service = get_reflection_memory_service()
    
    # Kịch bản 1: Mâu thuẫn định tuyến chuyên khoa (Tim mạch vs Tiêu hóa vs Cơ xương khớp)
    # Tim mạch (Weight 95) > Tiêu hóa (Weight 65) > Cơ xương khớp (Weight 35)
    lesson_tieu_hoa = ReflectionMemoryItem(
        rubric_id="RUBRIC-05-ANATOMICAL-PRIORITY",
        failed_strategy="Định tuyến khám Tiêu hóa trước",
        lesson_learned="Người bệnh đau thượng vị kèm tức ngực, nên ưu tiên khám Khoa Tiêu hóa - Gan mật",
        new_constraint="Ưu tiên Khoa Tiêu hóa - Gan mật",
        trigger_query="Tức ngực kèm ợ chua",
        created_at="2026-10-01T10:00:00Z",
    )
    
    lesson_tim_mach = ReflectionMemoryItem(
        rubric_id="RUBRIC-05-ANATOMICAL-PRIORITY",
        failed_strategy="Định tuyến khám Tiêu hóa",
        lesson_learned="Tức ngực đè nặng là dấu hiệu tim mạch sinh tồn, BẮT BUỘC ưu tiên Trung tâm Tim mạch trước Tiêu hóa",
        new_constraint="Bắt buộc ưu tiên Trung tâm Tim mạch",
        trigger_query="Tức ngực kèm ợ chua",
        created_at="2026-10-02T10:00:00Z",
    )
    
    lesson_safety_red_flag = ReflectionMemoryItem(
        rubric_id="RUBRIC-01-RED-FLAG-SAFETY",
        failed_strategy="Tư vấn đặt lịch thông thường khi có cờ đỏ",
        lesson_learned="Có cờ đỏ đau ngực lan vai trái, lập tức kích hoạt cấp cứu",
        new_constraint="Chặn đặt lịch, kích hoạt cấp cứu 115",
        trigger_query="Đau ngực lan vai trái",
        created_at="2026-10-02T11:00:00Z",
    )
    
    raw_memory = [lesson_tieu_hoa, lesson_tim_mach, lesson_safety_red_flag]
    resolved = service.resolve_memory_conflicts(raw_memory)
    
    # Kiểm tra phân giải mâu thuẫn:
    # 1. Ràng buộc an toàn đỏ luôn luôn được giữ
    assert any(it.rubric_id == "RUBRIC-01-RED-FLAG-SAFETY" for it in resolved)
    
    # 2. Xung đột giữa Tiêu hóa và Tim mạch: Tim mạch thắng vì trọng số sinh tồn 95 > 65
    specialty_lessons = [it for it in resolved if "RUBRIC-05" in it.rubric_id]
    assert len(specialty_lessons) == 1
    assert "Tim mạch" in specialty_lessons[0].new_constraint
    assert "Tiêu hóa" not in specialty_lessons[0].new_constraint
    
    # 3. Định dạng prompt không còn mâu thuẫn
    prompt_str = service.format_reflections_for_prompt(raw_memory)
    assert "Trung tâm Tim mạch" in prompt_str
    assert "Ưu tiên Khoa Tiêu hóa - Gan mật" not in prompt_str
    print("\n[PASS] Test Memory Conflict Resolution: Tim mạch won over Tiêu hóa based on Anatomical Vital Hierarchy!")


if __name__ == "__main__":
    test_action_space_pruning()
    test_memory_conflict_resolution()
    print("\nALL PRODUCTION REFLEXION TESTS PASSED!")
