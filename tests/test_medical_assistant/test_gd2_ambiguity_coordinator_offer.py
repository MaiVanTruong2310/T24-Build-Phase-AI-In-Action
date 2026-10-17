"""GĐ2: cấp cứu khớp MƠ HỒ (thiếu dấu) + phương án cuối gợi ý gặp điều phối viên khi AI bế tắc nhiều lượt."""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.medical_assistant.domain.ambiguity_resolution import (
    STUCK_THRESHOLD,
    is_stuck_turn,
    next_stuck_streak,
    parse_yes_no,
    resolve_ambiguous_emergency,
    restoration_is_faithful,
    restore_diacritics,
)
from src.medical_assistant.domain.triage_service import get_triage_service


class FakeLLM:
    """Trả lần lượt các câu trong `replies` (lần 1: khôi phục dấu, lần 2: trả lời có loại trừ cấp cứu không)."""

    def __init__(self, *replies, error=None):
        self.replies, self.error = list(replies), error

    async def ainvoke(self, _messages):
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.replies.pop(0) if self.replies else "KHONG_CHAC")


# ------------------------------------------------------------------ khôi phục dấu: chỉ được THÊM dấu
def test_restoration_must_only_add_marks():
    assert restoration_is_faithful("toi ho nhieu cung voi mat ngu", "tôi ho nhiều cùng với mất ngủ")
    assert not restoration_is_faithful("toi ho nhieu", "tôi ho nhiều và sốt")  # thêm từ
    assert not restoration_is_faithful("toi ho nhieu", "tôi bị ho")  # đổi từ
    assert not restoration_is_faithful("toi ho", "")


@pytest.mark.asyncio
async def test_restore_rejects_unfaithful_or_failed_llm():
    assert await restore_diacritics("toi ho", FakeLLM("tôi ho")) == "tôi ho"
    assert await restore_diacritics("toi ho", FakeLLM("tôi ho và đau ngực")) is None
    assert await restore_diacritics("toi ho", FakeLLM(error=RuntimeError("down"))) is None


# ------------------------------------------------------------------ quyết định cho lần khớp mơ hồ
@pytest.mark.asyncio
async def test_ambiguous_benign_is_cleared_only_with_two_evidences():
    llm = FakeLLM("tôi ho nhiều cùng với mất ngủ", "KHONG")
    d = await resolve_ambiguous_emergency(get_triage_service(), "toi ho nhieu cung voi mat ngu", [], "vi", llm)
    assert d.kind == "clear" and d.restored == "tôi ho nhiều cùng với mất ngủ"


@pytest.mark.asyncio
@pytest.mark.parametrize("second", ["CO", "KHONG_CHAC", "không chắc lắm"])
async def test_benign_restoration_alone_does_not_clear(second):
    llm = FakeLLM("tôi ho nhiều cùng với mất ngủ", second)
    d = await resolve_ambiguous_emergency(get_triage_service(), "toi ho nhieu cung voi mat ngu", [], "vi", llm)
    assert d.kind == "confirm"


@pytest.mark.asyncio
async def test_wrong_restoration_of_anaphylaxis_is_not_cleared():
    # LLM thật từng khôi phục "sưng mới" thay vì "sưng môi": lần hỏi thứ hai phải chặn việc gỡ cảnh báo
    llm = FakeLLM("tôi bị ong đốt sưng mới khó thở", "CO")
    d = await resolve_ambiguous_emergency(get_triage_service(), "toi bi ong dot sung moi kho tho", [], "vi", llm)
    assert d.kind in {"confirm", "emergency"}


class _StubTriage:
    """Tin gốc: ATS 1 mơ hồ; bản LLM khôi phục (đọc sai): không cấp cứu."""

    def evaluate_with_recent_context(self, text, _messages, language="vi"):
        if text == "goc":
            return SimpleNamespace(
                is_emergency=True,
                ats_level=1,
                match_confidence="ambiguous",
                triggered_red_flags=["Trẻ sơ sinh tím"],
                triggered_rule_ids=["ATS1_INFANT_CRITICAL"],
            )
        return SimpleNamespace(
            is_emergency=False, ats_level=4, match_confidence="certain", triggered_red_flags=[], triggered_rule_ids=[]
        )


@pytest.mark.asyncio
async def test_ambiguous_ats1_is_never_cleared_by_llm():
    # ETEK-038 (eval GĐ2): trẻ 10 tuần sốc bị LLM đọc sai + trả lời KHONG → đã bị gỡ cảnh báo. ATS 1 phải hỏi xác nhận.
    with patch("src.medical_assistant.domain.ambiguity_resolution.restore_diacritics", return_value="gốc"):
        d = await resolve_ambiguous_emergency(_StubTriage(), "goc", [], "vi", FakeLLM("KHONG"))
    assert d.kind == "confirm"


def test_certain_rule_wins_over_ambiguous_hook_tilde_match():
    r = get_triage_service().evaluate_symptoms("Bà tôi bất tĩnh rồi, gọi không dậy")
    assert r.is_emergency and r.match_confidence != "ambiguous"


@pytest.mark.asyncio
async def test_ambiguous_real_emergency_is_confirmed_by_restoration():
    d = await resolve_ambiguous_emergency(
        get_triage_service(), "con toi bi voi bot ban vao mat", [], "vi", FakeLLM("con tôi bị vôi bột bắn vào mắt")
    )
    assert d.kind == "emergency" and d.result.is_emergency


@pytest.mark.asyncio
async def test_ambiguous_without_llm_asks_confirmation_never_silently_clears():
    d = await resolve_ambiguous_emergency(
        get_triage_service(), "toi ho nhieu cung voi mat ngu", [], "vi", FakeLLM(error=TimeoutError())
    )
    assert d.kind == "confirm"


# ------------------------------------------------------------------ Có / Không
@pytest.mark.parametrize("text", ["Có", "có", "Có, đang bị như vậy", "đúng rồi", "ok", "Yêu cầu hỗ trợ", "co"])
def test_yes(text):
    assert parse_yes_no(text) == "yes"


@pytest.mark.parametrize("text", ["Không", "không phải", "Không phải", "ko", "thôi", "không cần"])
def test_no(text):
    assert parse_yes_no(text) == "no"


@pytest.mark.parametrize("text", ["khám mắt ở đâu", "con tôi bị ho", "có lẽ là không", ""])
def test_unclear(text):
    assert parse_yes_no(text) is None


# ------------------------------------------------------------------ đếm lượt bế tắc
def test_stuck_turns():
    assert is_stuck_turn("", {"off_topic": "gibberish"}, False, False)
    assert is_stuck_turn("VISIT_PURPOSE_CLARIFICATION", {}, False, False)
    assert is_stuck_turn("PROBING_IN_PROGRESS", {}, True, False)  # hỏi lại y nguyên câu cũ
    assert not is_stuck_turn("", {"off_topic": "off_topic"}, False, False)  # lạc đề không phải bế tắc
    assert not is_stuck_turn("TRIAGED_AWAITING_SCHEDULE", {}, False, False)
    assert next_stuck_streak(2, True) == 3 and next_stuck_streak(2, False) == 0


# ------------------------------------------------------------------ qua graph thật, LLM tắt (luồng dự phòng tất định)
def _offline():
    off = RuntimeError("offline test")
    return [
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=off),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=off),
    ]


async def _chat(turns):
    from src.medical_assistant.agent.graph import agent
    from src.services.chat_history import STATE_FIELDS

    cfg = {"configurable": {"thread_id": f"gd2-{uuid.uuid4().hex}"}}
    carry, outs = {}, []
    patches = _offline()
    for p in patches:
        p.start()
    try:
        for q in turns:
            s = await agent.ainvoke({**carry, "query": q, "is_authenticated": False}, config=cfg)
            outs.append(s)
            carry = {k: s[k] for k in STATE_FIELDS if k in s}
    finally:
        for p in patches:
            p.stop()
    return outs


@pytest.mark.asyncio
async def test_graph_ambiguous_then_yes_is_full_emergency():
    first, second = await _chat(["toi ho nhieu cung voi mat ngu", "Có, đang bị như vậy"])
    assert first["workflow_status"] == "EMERGENCY_CONFIRM" and not first.get("is_emergency")
    assert "115" in first["response"] and first["response"].count("?") == 1
    assert second["is_emergency"] and second["workflow_status"] == "EMERGENCY"


@pytest.mark.asyncio
async def test_graph_ambiguous_then_no_continues_consultation():
    _first, second = await _chat(["toi ho nhieu cung voi mat ngu", "Không phải"])
    assert not second.get("is_emergency") and second["workflow_status"] != "EMERGENCY_CONFIRM"
    assert not second.get("pending_emergency")


@pytest.mark.asyncio
async def test_graph_stuck_turns_offer_coordinator_then_yes_escalates():
    outs = await _chat(["asdkjh qwe zxc", "jjjjj kkkk", "qpwoei rutyty", "Có"])
    offer = outs[STUCK_THRESHOLD - 1]
    assert offer["workflow_status"] == "HITL_AWAITING_CONFIRMATION"
    assert "điều phối viên" in offer["response"] and offer["metadata"]["quick_replies"] == ["Có", "Không"]
    assert outs[-1]["workflow_status"] == "HITL_ESCALATED_COORDINATOR"


@pytest.mark.asyncio
async def test_graph_stuck_turns_offer_then_no_keeps_session():
    outs = await _chat(["asdkjh qwe zxc", "jjjjj kkkk", "qpwoei rutyty", "Không"])
    assert outs[-1]["workflow_status"] == "HITL_DECLINED_CONVERSATIONAL"
    assert "câu hỏi nào khác" in outs[-1]["response"]


# ------------------------------------------------------------------ ETEK-038: định tuyến đúng khoa cho ca cấp cứu
_ETEK_038 = (
    "con toi 10 tuan tuoi, 2 hom nay bu kem, li bi dan, tu hom qua sot, dem phai danh thuc moi bu. Gio be tai nhot, "
    "2 chan noi van tim den dau goi, nguoi hoi lanh, goi rat kho tinh."
)


def test_infant_shock_is_not_routed_to_cardiology():
    # "vân tim (tím) … hơi lanh (lạnh)" từng khớp STEMI "tim … lan" → thêm Tim mạch cho trẻ 10 tuần
    r = get_triage_service().evaluate_symptoms(_ETEK_038)
    assert r.is_emergency and "STEMI_ACS_CRUSHING" not in r.triggered_rule_ids
    assert r.suggested_specialty == "Cấp cứu"


@pytest.mark.asyncio
async def test_graph_offline_infant_shock_stays_on_emergency_path():
    (out,) = await _chat([_ETEK_038])
    assert out["workflow_status"] in {"EMERGENCY", "EMERGENCY_CONFIRM"} and "115" in out["response"]


@pytest.mark.parametrize(("emergency", "status"), [(True, "EMERGENCY"), (False, "EMERGENCY_CONFIRM")])
def test_critic_multi_specialty_pipeline_never_overrides_emergency(emergency, status):
    from src.medical_assistant.domain.clinical_critic_service import ClinicalCriticService

    state = {
        "is_emergency": emergency,
        "workflow_status": status,
        "ats_level": 1,
        "suggested_department_name": "Cấp cứu",
    }
    verdict = ClinicalCriticService().audit_analysis(_ETEK_038 + " Đau ngực lan ra tay trái, đau gối", state)
    assert verdict.corrections.get("workflow_status") in (None, status)
    assert verdict.corrections.get("suggested_department_name") in (None, "Cấp cứu")


# ------------------------------------------------------------------ [BS duyệt mục 9] câu quá ngắn, thiếu dữ kiện
@pytest.mark.parametrize("text", ["con tôi bị co giật", "bé đang co giật", "tôi bị co giật"])
def test_clearly_stated_seizure_is_emergency_without_asking(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence != "ambiguous"


@pytest.mark.parametrize("text", ["co giật", "co giat", "co giật là gì"])
def test_bare_seizure_word_asks_once(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence == "ambiguous"


@pytest.mark.parametrize("text", ["khó thở", "tôi bị khó thở", "kho tho qua", "hơi khó thở"])
def test_bare_dyspnea_asks_severity_and_stays_respiratory(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence == "ambiguous" and r.suggested_specialty == "Nội hô hấp"
    assert "115" in r.patient_guidance


@pytest.mark.parametrize("text", ["khó thở, môi tím", "thở không nổi"])
def test_severe_dyspnea_is_emergency_without_asking(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence != "ambiguous"


def test_dyspnea_with_context_keeps_normal_routing():
    r = get_triage_service().evaluate_symptoms("khó thở 3 ngày nay kèm ho")
    assert not r.is_emergency and r.suggested_specialty == "Nội hô hấp"


@pytest.mark.asyncio
async def test_graph_bare_dyspnea_yes_is_emergency():
    first, second = await _chat(["khó thở", "Có, đang bị như vậy"])
    assert first["workflow_status"] == "EMERGENCY_CONFIRM" and "115" in first["response"]
    assert first["response"].count("?") == 1
    assert second["is_emergency"] and second["workflow_status"] == "EMERGENCY" and "115" in second["response"]


@pytest.mark.asyncio
async def test_graph_bare_dyspnea_no_is_same_day_respiratory():
    _first, second = await _chat(["khó thở", "Không phải"])
    assert not second.get("is_emergency") and second["workflow_status"] != "EMERGENCY_CONFIRM"
    assert second.get("ats_level") == 3 and second.get("suggested_department_name") == "Nội hô hấp"


@pytest.mark.asyncio
async def test_graph_clear_seizure_goes_straight_to_emergency():
    (out,) = await _chat(["con tôi bị co giật"])
    assert out["workflow_status"] == "EMERGENCY" and "115" in out["response"]


@pytest.mark.parametrize(
    "text", ["khó thở lắm", "khó thở quá trời", "khó thở nhiều", "hụt hơi", "thở dốc", "hut hoi qua"]
)
def test_dyspnea_with_intensity_or_synonym_is_never_lower_than_bare(text):
    # Câu nặng hơn ("lắm", "quá trời") không được xếp THẤP hơn "khó thở" trơn
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence == "ambiguous" and r.suggested_specialty == "Nội hô hấp"


@pytest.mark.parametrize("text", ["hụt hơi khi leo cầu thang", "thở dốc khi chạy bộ"])
def test_contextual_dyspnea_synonyms_route_to_respiratory(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert not r.is_emergency and r.suggested_specialty == "Nội hô hấp"


def test_negated_dyspnea_is_not_routed_to_respiratory():
    # eval D021: "không khó thở" không được kéo sang Nội hô hấp
    r = get_triage_service().evaluate_symptoms("không đau ngực, không khó thở, chỉ hơi mệt vài hôm")
    assert r.suggested_specialty != "Nội hô hấp"
