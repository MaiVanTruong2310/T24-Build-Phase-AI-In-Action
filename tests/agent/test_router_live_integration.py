"""Test End-to-End Live Integration cho Router Node (Prompt E - P2).

Không sử dụng Mock LLM. Chạy thực nghiệm qua chuỗi `route_intent_node` thật
với ít nhất 40 câu hỏi trải dài trên 4 nhóm ý định cốt lõi:
- 10 câu clinical_triage
- 10 câu info_lookup
- 10 câu booking
- 10 câu chitchat
Đánh dấu @pytest.mark.integration.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict

import pytest

from src.medical_assistant.agent.nodes.router_node import route_intent_node

logger = logging.getLogger(__name__)

# 40 câu hỏi kiểm thử e2e chuẩn hóa theo thực tế người dùng
E2E_ROUTER_DATASET = [
    # --- NHÓM 1: CLINICAL TRIAGE (10 CÂU) -> dest "analyze" ---
    {
        "query": "Tôi bị đau đầu vùng thái dương hai bên và buồn nôn",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Bụng dưới của tôi bị đau quặn từng cơn kèm đi ngoài lỏng",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Con tôi bị sốt cao 39 độ liên tục 2 ngày nay chưa hạ",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Tôi bị ho khan kéo dài hơn 2 tuần, họng rát và khàn tiếng",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Khớp gối của tôi bị sưng đau, đi lại nghe tiếng lục cục",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Tôi bị mẩn ngứa nổi mề đay khắp người sau khi ăn tôm",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Dạo này tôi hay bị chóng mặt hoa mắt khi đứng lên đột ngột",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Bệnh nhân bị đau thắt ngực dữ dội vã mồ hôi lạnh",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Tôi bị trào ngược dạ dày, ợ chua và tức ngực sau khi ăn",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    {
        "query": "Tôi bị tê bì cánh tay trái kéo dài 3 hôm nay",
        "expected_dest": "analyze",
        "expected_route": "clinical_triage",
    },
    # --- NHÓM 2: INFO LOOKUP (10 CÂU) -> dest "info_agent" ---
    {
        "query": "Bác sĩ Nguyễn Đình Dũng chuyên khoa nào vậy bạn?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Bệnh viện Vinmec Times City có địa chỉ ở đâu?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Khoa Tiêu hóa Vinmec khám những bệnh gì và có kỹ thuật gì nổi bật?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Có bác sĩ tim mạch nào giỏi ở Vinmec Central Park không?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Cho tôi xem danh sách các bệnh viện Vinmec tại Hà Nội",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Bệnh sốt xuất huyết có những triệu chứng điển hình gì?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Bác sĩ chuyên khoa xương khớp nào có trên 15 năm kinh nghiệm?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Khoa Nhi của Vinmec điều trị những vấn đề sức khỏe nào?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Bệnh viện Vinmec Smart City nằm ở tòa nhà nào?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    {
        "query": "Nguyên nhân và cách phòng ngừa bệnh sỏi thận là gì?",
        "expected_dest": "info_agent",
        "expected_route": "info_lookup",
    },
    # --- NHÓM 3: BOOKING (10 CÂU) -> dest "analyze" ---
    {
        "query": "Tôi muốn đặt lịch khám vào sáng mai được không?",
        "expected_dest": "analyze",
        "expected_route": "booking",
    },
    {
        "query": "Có khung giờ khám nào còn trống cho thứ Hai tuần tới không?",
        "expected_dest": "analyze",
        "expected_route": "booking",
    },
    {"query": "Hẹn lịch khám với bác sĩ vào lúc 9 giờ sáng", "expected_dest": "analyze", "expected_route": "booking"},
    {"query": "Tôi muốn đăng ký khám tại cơ sở Times City", "expected_dest": "analyze", "expected_route": "booking"},
    {"query": "Cho tôi đặt slot ca chiều ngày mai", "expected_dest": "analyze", "expected_route": "booking"},
    {
        "query": "Kiểm tra phiếu hẹn khám của tôi đã được xếp chưa",
        "expected_dest": "analyze",
        "expected_route": "booking",
    },
    {
        "query": "Tôi muốn đặt lịch khám tổng quát định kỳ tuần này",
        "expected_dest": "analyze",
        "expected_route": "booking",
    },
    {
        "query": "Xem các ca khám còn trống của khoa Cơ xương khớp",
        "expected_dest": "analyze",
        "expected_route": "booking",
    },
    {"query": "Đăng ký hẹn bác sĩ vào chiều thứ Sáu", "expected_dest": "analyze", "expected_route": "booking"},
    {"query": "Đặt lịch tái khám theo chỉ định", "expected_dest": "analyze", "expected_route": "booking"},
    # --- NHÓM 4: CHITCHAT (10 CÂU) -> dest "chitchat" ---
    {"query": "Xin chào trợ lý y tế", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Chào em, em tên là gì thế?", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {
        "query": "Hello bạn, chúc bạn một ngày làm việc vui vẻ",
        "expected_dest": "chitchat",
        "expected_route": "chitchat",
    },
    {"query": "Bạn là ai và có thể giúp gì cho tôi?", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Cảm ơn em nhiều nhé, em dễ thương quá", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Tạm biệt bạn, hẹn gặp lại lần sau", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Hi bot, bạn mấy tuổi rồi?", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Chào buổi sáng trợ lý", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Cảm ơn bạn đã hỗ trợ nhiệt tình", "expected_dest": "chitchat", "expected_route": "chitchat"},
    {"query": "Bye bye trợ lý ảo", "expected_dest": "chitchat", "expected_route": "chitchat"},
]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_router_e2e_40_queries():
    """Chạy toàn bộ 40 câu hỏi qua route_intent_node trực tiếp không mock."""
    # Yêu cầu 8: Điều kiện chạy rõ ràng cho Integration Test
    run_live = os.getenv("RUN_LIVE_LLM", "").lower() in ("true", "1", "yes")
    has_key = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENROUTER_API_KEY"))
    if not (run_live or has_key):
        pytest.skip("Bỏ qua Live Integration Test: RUN_LIVE_LLM hoặc API Key chưa được cấu hình rõ ràng.")

    assert len(E2E_ROUTER_DATASET) >= 40, "Dataset phải có ít nhất 40 câu hỏi"

    correct_dest_count = 0
    correct_route_count = 0
    llm_answered_count = 0
    results = []

    group_stats = defaultdict(lambda: {"total": 0, "dest_correct": 0, "route_correct": 0})

    for item in E2E_ROUTER_DATASET:
        query = item["query"]
        expected_dest = item["expected_dest"]
        expected_route = item["expected_route"]

        state = {
            "query": query,
            "language": "vi",
            "probing_turn": 0,
            "collected_details": [],
        }

        output = await route_intent_node(state)
        actual_dest = output.get("route_destination")
        actual_route = output.get("intent_route")
        meta = output.get("metadata", {})

        # Yêu cầu 9: Kiểm tra xem có phải LLM thật trả lời không (không phải rule-based fallback)
        is_fallback = bool(meta.get("fallback_used") or meta.get("rule_based"))
        if not is_fallback:
            llm_answered_count += 1

        dest_match = actual_dest == expected_dest
        route_match = actual_route == expected_route

        group_stats[expected_route]["total"] += 1
        if dest_match:
            correct_dest_count += 1
            group_stats[expected_route]["dest_correct"] += 1
        if route_match:
            correct_route_count += 1
            group_stats[expected_route]["route_correct"] += 1

        results.append(
            {
                "query": query,
                "expected_dest": expected_dest,
                "actual_dest": actual_dest,
                "dest_match": dest_match,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "route_match": route_match,
                "is_fallback": is_fallback,
            }
        )

    tot_queries = len(E2E_ROUTER_DATASET)
    dest_accuracy = (correct_dest_count / tot_queries) * 100.0
    route_accuracy = (correct_route_count / tot_queries) * 100.0
    llm_ratio = (llm_answered_count / tot_queries) * 100.0

    logger.info(
        "Live Router Benchmark (40 queries): Dest Acc=%.1f%%, Route Acc=%.1f%%, LLM Real Ratio=%.1f%%",
        dest_accuracy,
        route_accuracy,
        llm_ratio,
    )

    # Yêu cầu 9: Assert được LLM thật đã trả lời phần lớn, assert route_accuracy >= 90%
    assert llm_ratio >= 75.0, (
        f"Tỷ lệ LLM thật trả lời ({llm_ratio:.1f}%) quá thấp, đang bị phụ thuộc vào rule-based fallback!"
    )
    assert route_accuracy >= 90.0, (
        f"Route accuracy ({route_accuracy:.1f}%) dưới ngưỡng 90.0%. "
        f"Chi tiết ca sai: {[r for r in results if not r['route_match']]}"
    )
    assert dest_accuracy >= 90.0, (
        f"Destination accuracy ({dest_accuracy:.1f}%) dưới ngưỡng 90.0%. "
        f"Chi tiết: {[r for r in results if not r['dest_match']]}"
    )

    # Yêu cầu 9: Assert accuracy theo từng nhóm
    for grp_name, g_info in group_stats.items():
        g_acc = (g_info["route_correct"] / g_info["total"]) * 100.0
        assert g_acc >= 80.0, f"Nhóm '{grp_name}' chỉ đạt {g_acc:.1f}% (< 80.0%)!"
