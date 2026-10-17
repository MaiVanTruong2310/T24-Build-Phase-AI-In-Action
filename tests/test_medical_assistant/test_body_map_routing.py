"""Mỗi câu mẫu của hình cơ thể (frontend) phải định tuyến đúng khoa, hoặc được cổng cấp cứu chặn khi cho phép.

LLM tắt (fallback tất định) để test không phụ thuộc mạng; đây là đường tối thiểu mà câu mẫu phải tự đứng được.
"""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService

REGIONS = json.loads(
    (Path(__file__).parents[2] / "frontend/src/features/chat/bodyMap/bodyRegions.json").read_text(encoding="utf-8")
)["regions"]
OPTIONS = [(region["id"], option) for region in REGIONS for option in region["options"]]


async def _fallback(self, text, state, **kwargs):
    return HybridDialogueService._fallback_response(text, state), False


def test_every_region_has_at_most_four_options():
    assert all(1 <= len(region["options"]) <= 4 for region in REGIONS)


@pytest.mark.asyncio
@pytest.mark.parametrize(("region", "option"), OPTIONS, ids=[f"{r}:{o['label']}" for r, o in OPTIONS])
async def test_body_map_option_routes_to_expected_specialty(region, option):
    state = {
        "query": option["text"],
        "probing_turn": 0,
        "collected_details": [],
        "language": "vi",
        "clinical_facts": {},
        "messages": [],
        "is_authenticated": False,
        "workflow_status": "IDLE",
    }
    with patch.object(HybridDialogueService, "process_turn_async", _fallback):
        result = await analyze_node(state)

    # Cổng cấp cứu chặn hẳn, hoặc hỏi xác nhận mức độ ("khó thở") trước khi định tuyến khoa.
    if result.get("is_emergency") or result.get("workflow_status") == "EMERGENCY_CONFIRM":
        assert option.get("emergency_ok"), f"{option['text']!r} bị chặn cấp cứu ngoài dự kiến"
        return
    department = result.get("suggested_department_name") or ""
    assert any(expected in department for expected in option["expect"]), (
        f"{option['text']!r} → {department!r}, kỳ vọng một trong {option['expect']}"
    )
    assert result.get("workflow_status") != "VISIT_PURPOSE_CLARIFICATION"


ONSETS = json.loads(
    (Path(__file__).parents[2] / "frontend/src/features/chat/bodyMap/bodyRegions.json").read_text(encoding="utf-8")
)["onsets"]


def test_onset_phrases_are_read_as_duration():
    from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service

    days = {
        onset["text"]: get_clinical_fact_service().extract(f"Tôi bị đau gót chân, {onset['text']}", turn_index=1)[
            "duration_days"
        ]
        for onset in ONSETS
    }
    # "mới xuất hiện hôm nay" để bot hỏi tiếp; các mốc còn lại phải đọc được số ngày.
    assert days == {
        "mới xuất hiện hôm nay": None,
        "từ hôm qua": 1,
        "khoảng 3 ngày nay": 3,
        "khoảng 1 tuần nay": 7,
        "hơn 1 tháng nay": 30,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(("region", "option"), OPTIONS, ids=[f"{r}:{o['label']}" for r, o in OPTIONS])
async def test_body_map_option_with_onset_keeps_specialty(region, option):
    """Bước "bắt đầu từ khi nào" nối thêm mốc thời gian: không được làm đổi khoa."""
    await test_body_map_option_routes_to_expected_specialty(
        region, {**option, "text": f"{option['text']}, khoảng 3 ngày nay"}
    )


def test_every_drawn_region_is_configured():
    source = (Path(__file__).parents[2] / "frontend/src/features/chat/bodyMap/BodyMap.tsx").read_text(encoding="utf-8")
    drawn = set(re.findall(r"^\s+(\w+): ", source.split("const SHAPES")[1].split("const VIEW_BOX")[0], flags=re.M))
    drawn |= set(re.findall(r"^\s+(\w+): both\(", source.split("const LIMBS")[1].split("const SHAPES")[0], flags=re.M))
    drawn -= {"front", "back", "head", "abdomen"}
    assert drawn <= {region["id"] for region in REGIONS}
