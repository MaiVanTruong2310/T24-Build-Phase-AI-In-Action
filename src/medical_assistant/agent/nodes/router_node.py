"""Intent Router Node.

Phân luồng ý định thông minh bằng Small LLM kết hợp rào chắn an toàn deterministic:
- Cổng an toàn (Bảo mật, Cấp cứu, Kê đơn, Chẩn đoán, FAQ Cache) được kiểm tra tức thì.
- Phân loại ý định thành 4 nhóm chính:
  1. clinical_triage: Triệu chứng, phân loại ATS, bệnh lý bản thân -> analyze_node
  2. booking: Đặt lịch, chọn slot, tra cứu phiếu hẹn -> analyze_node
  3. info_lookup: Tra cứu bác sĩ, chuyên khoa, bệnh viện, kiến thức bệnh học -> info_agent_node
  4. chitchat: Chào hỏi đơn thuần, xã giao -> respond_node (giữ nguyên clinical episode)
- Feature flag: INFO_AGENT_ENABLED.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.config import is_info_agent_enabled
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service
from src.medical_assistant.domain.triage_service import get_triage_service
from src.medical_assistant.infrastructure.llm import get_llm

logger = logging.getLogger(__name__)


class IntentRouteResult(BaseModel):
    """Schema cho kết quả phân luồng ý định người dùng."""

    route: Literal["clinical_triage", "booking", "info_lookup", "chitchat"] = Field(
        ...,
        description=(
            "Phân loại luồng xử lý: "
            "'clinical_triage' (mô tả triệu chứng bệnh, đau, ốm, khó chịu của bản thân); "
            "'booking' (yêu cầu đặt lịch, xem giờ trống, điền thông tin hẹn khám); "
            "'info_lookup' (tra cứu thông tin bác sĩ, chuyên khoa, bệnh viện, cơ sở, kiến thức bệnh học, bảng giá); "
            "'chitchat' (chào hỏi đơn thuần, hỏi thăm bot, xã giao không có mục đích y tế)."
        ),
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của phân loại từ 0.0 đến 1.0",
    )
    reasoning: str = Field(
        default="",
        description="Lý do ngắn gọn cho quyết định phân luồng",
    )


ROUTER_SYSTEM_PROMPT = """Bạn là Bộ phân luồng ý định thông minh (Intent Router) của Trợ lý y tế tiếp đón Vinmec.
Nhiệm vụ của bạn là phân loại câu hỏi của người dùng vào chính xác 1 trong 4 nhóm:

1. 'clinical_triage': Người dùng mô tả triệu chứng sức khỏe, cảm giác đau, sốt, khó chịu, bệnh tật của bản thân cần được đánh giá hoặc tư vấn chuyên khoa khám.
2. 'booking': Người dùng muốn đặt lịch khám, chọn giờ khám, xem lịch trống, cung cấp thông tin liên hệ đặt hẹn, hoặc xác nhận đặt chỗ.
3. 'info_lookup': Người dùng hỏi thông tin tra cứu khách quan: tìm bác sĩ (tên, chuyên khoa, kinh nghiệm), hỏi về khoa phòng, hỏi về bệnh viện/cơ sở y tế (địa chỉ, chi nhánh), hoặc hỏi kiến thức bệnh học tổng quát.
4. 'chitchat': Lời chào hỏi thông thường ("xin chào", "hello"), hỏi thăm danh tính bot ("bạn là ai", "bạn mấy tuổi"), lời khen/cảm ơn hoặc xã giao thuần túy.

QUY TẮC PHÂN LOẠI:
- Nếu người dùng hỏi bác sĩ hoặc cơ sở hoặc khoa phòng, ĐÓ LÀ 'info_lookup'.
- Nếu câu hỏi mơ hồ hoặc vừa hỏi thông tin vừa có thắc mắc chung, hãy ưu tiên 'info_lookup' để tra cứu dữ liệu thực tế.
- Nếu người dùng có triệu chứng rõ rệt ("tôi bị đau bụng", "sốt 3 ngày"), ĐÓ LÀ 'clinical_triage'.
"""


def _rule_based_fallback_route(query: str, rule_hint: str | None) -> tuple[str, float]:
    """Fallback phân loại bằng từ khóa nếu mô hình LLM gặp sự cố."""
    q_low = query.lower().strip()

    if rule_hint in {
        "MEDICATION_GUARDRAIL",
        "DIAGNOSIS_GUARDRAIL",
        "HEADACHE_WITH_VISUAL_CHANGE",
        "VISIT_PURPOSE_CLARIFICATION",
        "THIRD_PARTY_HEALTH_QUERY",
        "SELF_CARE_FOLLOWUP",
        "SOCIAL_STATEMENT",
    }:
        return "clinical_triage", 0.95

    # Nhận diện thao tác tiếp tục hỏi bệnh / mô tả thêm triệu chứng
    if "mô tả thêm" in q_low or "mo ta them" in q_low:
        return "clinical_triage", 0.95

    # Nhận diện hỏi chuyên khoa khám khi có triệu chứng / thắc mắc khoa khám (ưu tiên hơn booking)
    if re.search(r"(?:khoa|chuyên\s+khoa)\s+(?:nào|gì|gi)|khám\s+(?:ở\s+|tại\s+)?(?:khoa|đâu)", q_low):
        return "clinical_triage", 0.95

    # Nhận diện booking
    booking_terms = [
        "đặt lịch",
        "dat lich",
        "lịch khám",
        "lich kham",
        "khung giờ",
        "khung gio",
        "slot",
        "hẹn khám",
        "hen kham",
        "phiếu hẹn",
        "phieu hen",
        "tiến trình điều trị",
        "muốn khám",
        "muon kham",
        "muốn đi khám",
        "muon di kham",
        "đăng ký khám",
        "dang ky kham",
        "đặt hẹn",
        "dat hen",
        "ca sáng",
        "ca sang",
        "ca chiều",
        "ca chieu",
        "ngày mai ca",
    ]
    if any(t in q_low for t in booking_terms):
        return "booking", 0.85

    # Nhận diện info lookup (bác sĩ, cơ sở, chuyên khoa, bệnh học, thông tin tổng quát)
    info_terms = [
        "bác sĩ",
        "bac si",
        "chuyên khoa",
        "chuyen khoa",
        "khoa ",
        "khoa nào",
        "khoa gi",
        "khoa khám",
        "bệnh viện",
        "benh vien",
        "cơ sở",
        "co so",
        "chi nhánh",
        "chi nhanh",
        "ở đâu",
        "o dau",
        "địa chỉ",
        "dia chi",
        "bệnh học",
        "nguyên nhân",
        "phòng ngừa",
        "bảng giá",
        "chi phí",
        "giờ làm việc",
        "hotline",
        "danh sách",
        "danh sach",
        "bệnh gì",
        "benh gi",
        "điều trị những bệnh",
        "dấu hiệu cảnh báo",
        "dau hieu canh bao",
        "dấu hiệu của",
        "dau hieu cua",
        "dấu hiệu",
        "dau hieu",
        "triệu chứng điển hình",
        "trieu chung dien hinh",
        "những triệu chứng",
        "nhung trieu chung",
        "biểu hiện của",
        "bieu hien cua",
    ]
    if any(t in q_low for t in info_terms):
        return "info_lookup", 0.85

    # Nhận diện triệu chứng lâm sàng
    clinical_terms = [
        "đau",
        "dau",
        "sốt",
        "sot",
        "mệt",
        "met",
        "ho",
        "khó thở",
        "kho tho",
        "chóng mặt",
        "chong mat",
        "buồn nôn",
        "buon non",
        "nôn",
        "tê bì",
        "te bi",
        "ngứa",
        "ngua",
        "sưng",
        "sung",
        "chảy máu",
        "chay mau",
        "tiêu chảy",
        "tieu chay",
        "táo bón",
        "tao bon",
        "bị bệnh",
        "bi benh",
        "khám bệnh",
        "kham benh",
    ]
    if any(t in q_low for t in clinical_terms):
        return "clinical_triage", 0.8

    # Nhận diện xã giao / chào hỏi / chúc tụng
    chitchat_terms = [
        "xin chào",
        "xin chao",
        "chào",
        "chao",
        "hello",
        "hi",
        "cảm ơn",
        "cam on",
        "tạm biệt",
        "tam biet",
        "bạn là ai",
        "ban la ai",
        "mấy tuổi",
        "may tuoi",
        "chúc",
        "chuc",
    ]
    if any(t in q_low for t in chitchat_terms):
        return "chitchat", 0.9

    # Mặc định nghiêng về tra cứu thông tin
    return "info_lookup", 0.55


async def route_intent_node(state: AgentState, llm: Any = None) -> dict[str, Any]:
    """Node phân loại ý định người dùng và điều phối nhánh thực thi tối ưu."""
    query = state.get("query") or state.get("user_input", "")
    language = state.get("language") or "vi"

    # =========================================================================
    # 1. CỔNG AN TOÀN DETERMINISTIC (Chạy tức thì < 1ms, 0 Token LLM)
    # =========================================================================

    # 1.1 Tường lửa an ninh mạng
    sec_check = get_security_guardrail_service().inspect_query(query, language=language)
    if not sec_check.is_safe:
        return {
            "intent_route": "clinical_triage",
            "route_confidence": 1.0,
            "route_destination": "analyze",
            "metadata": {
                "route": "safety_blocked",
                "violation_type": sec_check.violation_type,
            },
        }

    # 1.2 Cấp cứu tối khẩn ATS 1/2
    emergency_check = get_triage_service().evaluate_symptoms(query, language=language)
    if emergency_check.is_emergency:
        return {
            "intent_route": "clinical_triage",
            "route_confidence": 1.0,
            "route_destination": "analyze",
            "is_emergency": True,
            "metadata": {
                "route": "emergency",
                "triggered_red_flags": emergency_check.triggered_red_flags,
            },
        }

    # 1.3 Zero-token FAQ Cache
    cache_check = get_cache_service().check_cache(query, language=language)
    if cache_check is not None:
        return {
            "intent_route": "info_lookup",
            "route_confidence": 1.0,
            "route_destination": "analyze",  # analyze_node sẽ hit cache và short-circuit tức thì
            "metadata": {
                "route": "faq_cache_hit",
            },
        }

    # 1.3.1 Tra cứu hồ sơ bệnh nhân trong phiên & Tra cứu lịch hẹn đã đặt
    from src.medical_assistant.domain.booking_slot_service import (
        detect_appointment_query,
        extract_booking_entities,
    )
    from src.medical_assistant.domain.guardrail_service import remove_accents

    if detect_appointment_query(query):
        return {
            "intent_route": "booking",
            "route_confidence": 1.0,
            "route_destination": "analyze",
            "metadata": {"route": "appointment_lookup"},
        }

    norm_q = remove_accents(query.lower())
    id_pattern = (
        r"(?:ten|so dien thoai|sdt|dia chi|thong tin(?: ca nhan)?|ho so)\s+(?:cua\s+)?(?:toi|minh)\b|"
        r"(?:hien thi|xem|kiem tra|cho biet)\s+(?:thong tin(?: ca nhan)?|ho so|ten|sdt|so dien thoai)\s+(?:cua\s+)?(?:toi|minh)\b|"
        r"\bmy\s+(?:name|phone|address|profile|info|contact)\b"
    )
    if re.search(id_pattern, norm_q) and not any(
        re.search(rf"\b{kw}\b", norm_q) for kw in ["dau", "sot", "ho", "benh", "kham"]
    ):
        return {
            "intent_route": "info_lookup",
            "route_confidence": 1.0,
            "route_destination": "analyze",
            "metadata": {"route": "session_profile_lookup"},
        }

    booking_entities = extract_booking_entities(query, state)
    if (
        booking_entities.get("is_booking_intent")
        or booking_entities.get("is_booking_confirmation")
        or (
            booking_entities.get("preferred_date")
            and not any(re.search(rf"\b{kw}\b", norm_q) for kw in ["dau", "sot", "ho", "benh"])
        )
    ):
        return {
            "intent_route": "booking",
            "route_confidence": 0.95,
            "route_destination": "analyze",
            "metadata": {"route": "booking_intent_direct"},
        }

    # 1.4 Rào chắn An toàn & Cổng Deterministic Veto (Prompt B: Hard Veto)
    guardrail_svc = get_guardrail_service()
    intent_hint = guardrail_svc.check_intent(
        query,
        current_department=state.get("suggested_department_name"),
        language=language,
        state=state,
    )
    if intent_hint:
        hint_intent = intent_hint.get("intent")
        if hint_intent in {
            "MEDICATION_GUARDRAIL",
            "DIAGNOSIS_GUARDRAIL",
            "HEADACHE_WITH_VISUAL_CHANGE",
            "VISIT_PURPOSE_CLARIFICATION",
            "THIRD_PARTY_HEALTH_QUERY",
            "SELF_CARE_FOLLOWUP",
            "SPECIALIZED_PROCEDURE_INQUIRY",
            "HITL_CONFIRM",
            "HITL_DECLINE",
        }:
            return {
                "intent_route": "clinical_triage",
                "route_confidence": 1.0,
                "route_destination": "analyze",
                "metadata": {
                    "route": "clinical_guardrail",
                    "guardrail_intent": hint_intent,
                },
            }
        if hint_intent == "SOCIAL_STATEMENT":
            has_clinical_episode = bool(
                state.get("active_probing_category")
                or state.get("ats_level")
                or state.get("collected_details")
                or (state.get("clinical_facts") and state.get("clinical_facts", {}).get("chief_complaint"))
            )
            if has_clinical_episode:
                return {
                    "intent_route": "clinical_triage",
                    "route_confidence": 1.0,
                    "route_destination": "analyze",
                    "metadata": {
                        "route": "clinical_guardrail",
                        "guardrail_intent": hint_intent,
                    },
                }
            return {
                "intent_route": "chitchat",
                "route_confidence": 1.0,
                "route_destination": "chitchat",
                "workflow_status": "SOCIAL_REDIRECT",
                "response": (
                    "Dạ, em hiểu đây có vẻ là chuyện cá nhân. Em không đánh giá hay suy đoán về người đó. "
                    "Em là Trợ lý Y tế Tiếp đón Thông minh của Hệ thống Y tế Đa khoa Quốc tế Vinmec. "
                    "Nếu bác muốn, em có thể tiếp tục hỗ trợ vấn đề sức khỏe hoặc yêu cầu đặt lịch đang trao đổi ạ."
                ),
                "disclaimer": "",
                "metadata": {
                    "route": "chitchat",
                    "guardrail_intent": hint_intent,
                },
            }
        if hint_intent == "HOLD_BOOKING":
            return {
                "intent_route": "booking",
                "route_confidence": 1.0,
                "route_destination": "analyze",
                "metadata": {
                    "route": "booking_guardrail",
                    "guardrail_intent": hint_intent,
                },
            }

    # 1.5 Bảo toàn phiên hội thoại lâm sàng đang probing (Clinical Episode Isolation)
    if state.get("workflow_status") in {
        "PROBING_IN_PROGRESS",
        "SAFETY_REVIEW",
        "GUARDRAIL_DIAGNOSIS",
        "GUARDRAIL_MEDICATION",
    } or state.get("active_probing_category"):
        if (
            "mo ta them" in norm_q
            or "mô tả thêm" in query.lower()
            or state.get("workflow_status") in {"PROBING_IN_PROGRESS", "SAFETY_REVIEW"}
        ):
            return {
                "intent_route": "clinical_triage",
                "route_confidence": 0.95,
                "route_destination": "analyze",
                "metadata": {
                    "route": "clinical_probing_active",
                    "active_probing_category": state.get("active_probing_category"),
                },
            }

    # Nếu feature flag info_agent bị tắt, dẫn thẳng vào analyze_node
    if not is_info_agent_enabled():
        return {
            "intent_route": "clinical_triage",
            "route_confidence": 1.0,
            "route_destination": "analyze",
            "metadata": {"info_agent_enabled": False},
        }

    # =========================================================================
    # 2. PHÂN LUỒNG Ý ĐỊNH BẰNG SMALL LLM (STRUCTURED OUTPUT)
    # =========================================================================
    hint_str = str(intent_hint.get("intent")) if intent_hint else "None"
    prompt_content = f'Tin nhắn người dùng: "{query}"\nGợi ý từ bộ lọc quy tắc (rule hint): {hint_str}'

    route_chosen: str = "info_lookup"
    confidence_val: float = 0.8
    reasoning_text: str = ""

    try:
        active_llm = llm or get_llm()
        structured_llm = active_llm.with_structured_output(IntentRouteResult)
        result: IntentRouteResult = await structured_llm.ainvoke(
            [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=prompt_content),
            ]
        )
        route_chosen = result.route
        confidence_val = float(result.confidence)
        reasoning_text = result.reasoning
    except Exception as exc:
        logger.warning("Intent router LLM failed, using rule-based fallback: %s", exc)
        route_chosen, confidence_val = _rule_based_fallback_route(query, hint_str)
        reasoning_text = f"Fallback keyword classifier ({route_chosen})"

    # =========================================================================
    # 3. QUYẾT ĐỊNH ĐIỀU HƯỚNG (DESTINATION RESOLUTION)
    # =========================================================================
    # - info_lookup HOẶC độ tin cậy thấp (< 0.6) -> info_agent
    # - chitchat -> respond (với phản hồi lịch sự, bảo tồn clinical state)
    # - clinical_triage / booking -> analyze_node
    has_clinical_episode = bool(
        state.get("active_probing_category")
        or state.get("ats_level")
        or state.get("collected_details")
        or (state.get("clinical_facts") and state.get("clinical_facts", {}).get("chief_complaint"))
    )

    if route_chosen == "info_lookup" or confidence_val < 0.6:
        dest = "info_agent"
    elif route_chosen == "chitchat":
        dest = "analyze" if has_clinical_episode else "chitchat"
    else:
        dest = "analyze"

    state_update: dict[str, Any] = {
        "intent_route": route_chosen,
        "route_confidence": confidence_val,
        "route_destination": dest,
        "metadata": {
            "route": route_chosen,
            "route_confidence": confidence_val,
            "route_destination": dest,
            "reasoning": reasoning_text,
            "rule_hint": hint_str,
        },
    }

    # Nếu là chitchat thuần túy, định hình câu trả lời xã giao thân thiện ngay
    if dest == "chitchat":
        state_update.update(
            {
                "workflow_status": "SOCIAL_REDIRECT",
                "response": (
                    "Dạ, em chào bác ạ! Em là Trợ lý Y tế Tiếp đón Thông minh của Hệ thống Y tế Đa khoa Quốc tế Vinmec. "
                    "Bác cần em hỗ trợ tư vấn triệu chứng, tra cứu thông tin bác sĩ, chuyên khoa hay đặt lịch khám bệnh hôm nay ạ?"
                ),
                "disclaimer": "",
            }
        )

    return state_update
