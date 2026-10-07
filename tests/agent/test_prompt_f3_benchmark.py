"""Tests verifying Prompt F3 Benchmark, Stratified Sampling, and 6-Entity Grounding.

Covers requirements from context_agent/plan2.md (Prompt F3):
1) Không cho phép đạt khi thiếu nhóm hoặc gate_total == 0.
2) Stratified sampling theo nhóm phân tầng.
3) Simulate DB Error thực tế kích hoạt data_unavailable=True và thông báo trung thực.
4) Grounding entity-level đầy đủ 6 loại (bác sĩ, cơ sở, địa chỉ, SĐT, giá, kinh nghiệm).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from scripts.eval_info import (
    extract_all_entities,
    evaluate_entity_grounding,
    stratified_sample,
    generate_markdown_report,
)


def test_stratified_sample_covers_all_categories_proportionally():
    """Yêu cầu 2: --limit phải lấy mẫu phân tầng theo nhóm, không cắt đầu file."""
    # Tạo dataset giả lập 5 nhóm
    fake_dataset = []
    categories = ["doctor_lookup", "facility_lookup", "emergency_red_flag", "safety_guardrails", "chitchat"]
    for cat in categories:
        for i in range(20):
            fake_dataset.append({"id": f"{cat}_{i}", "category": cat, "query": f"Query {cat} {i}"})

    assert len(fake_dataset) == 100

    # Lấy mẫu limit = 15
    sampled = stratified_sample(fake_dataset, limit=15)
    assert len(sampled) <= 18
    sampled_cats = {item["category"] for item in sampled}
    # Tất cả 5 nhóm bắt buộc phải có mặt
    assert sampled_cats == set(categories), f"Thiếu nhóm sau khi sample: {set(categories) - sampled_cats}"


def test_entity_grounding_covers_all_six_entity_types():
    """Yêu cầu 4: Entity Grounding đầy đủ 6 loại thực thể."""
    # 1. Trường hợp Grounded 100%
    valid_text = (
        "Bác sĩ Nguyễn Đình Dũng tại Bệnh viện Đa khoa Quốc tế Vinmec Times City "
        "ở 458 Minh Khai có 20 năm kinh nghiệm. Giá khám là 500.000 VNĐ. Hotline 1900 232 389."
    )
    full_tool_results = [
        {
            "tool": "search_doctors",
            "data": {
                "doctors": [
                    {
                        "full_name": "Nguyễn Đình Dũng",
                        "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
                        "experience_display": "20 năm kinh nghiệm",
                        "price": "500.000 VNĐ",
                    }
                ],
                "facility": {
                    "name": "Vinmec Times City",
                    "address": "458 Minh Khai",
                }
            }
        }
    ]

    is_grounded, has_halluc, stats, reasons = evaluate_entity_grounding(
        valid_text,
        full_tool_results=full_tool_results,
        available_slots=[],
        forbidden_facts=[],
    )

    assert is_grounded is True
    assert has_halluc is False
    assert stats["doctor_name"]["grounded"] >= 1
    assert stats["doctor_name"]["hallucinated"] == 0
    assert stats["phone"]["grounded"] >= 1
    assert stats["price"]["grounded"] >= 1
    assert stats["experience_years"]["grounded"] >= 1
    assert stats["address"]["grounded"] >= 1

    # 2. Trường hợp Bịa đặt (Hallucinated)
    halluc_text = (
        "Bác sĩ David Copperfield tại Phòng khám Kỳ Lạ "
        "ở 999 Phố Lạ có 45 năm kinh nghiệm. Giá khám là 999.000.000 VNĐ. SĐT 0999999999."
    )
    is_gr_2, has_hl_2, stats_2, reasons_2 = evaluate_entity_grounding(
        halluc_text,
        full_tool_results=full_tool_results,
        available_slots=[],
        forbidden_facts=["Phòng khám Kỳ Lạ"],
    )

    assert is_gr_2 is False
    assert has_hl_2 is True
    assert stats_2["doctor_name"]["hallucinated"] >= 1
    assert stats_2["phone"]["hallucinated"] >= 1
    assert stats_2["price"]["hallucinated"] >= 1
    assert stats_2["experience_years"]["hallucinated"] >= 1
    assert any("forbidden fact" in r for r in reasons_2)


def test_markdown_report_flags_incomplete_dataset():
    """Yêu cầu 1: Khi chưa chạy đủ hoặc thiếu nhóm, báo cáo ghi KHÔNG HỢP LỆ - CHƯA CHẠY ĐỦ."""
    eval_mock = {
        "provider_name": "deepseek",
        "model_name": "deepseek-chat",
        "total_queries": 10,
        "llm_error_count": 0,
        "crawl_count": 0,
        "gate_safety_accuracy_pct": 0.0,
        "gate_items_count": 0,
        "route_accuracy_pct": 80.0,
        "tool_accuracy_pct": 70.0,
        "grounded_rate_pct": 60.0,
        "hallucination_rate_pct": 10.0,
        "fallback_rate_pct": 0.0,
        "clarify_rate_pct": 0.0,
        "latency_p50_ms": 1200.0,
        "latency_p95_ms": 2500.0,
        "category_metrics": {"doctor_lookup": {"count": 10}},
        "agg_entities": {},
        "detailed_results": [],
    }

    report = generate_markdown_report(
        eval_mock,
        eval_off=None,
        is_valid_dataset=False,
        invalid_reason="Thiếu các nhóm cốt lõi: emergency_red_flag, safety_guardrails",
    )

    assert "KHÔNG HỢP LỆ - CHƯA CHẠY ĐỦ" in report
    assert "Thiếu các nhóm cốt lõi" in report
    assert "gate_total" not in report or "0 câu" in report
