import asyncio
import logging
import re
from typing import Any

from src.medical_assistant.agent.nodes.helpers import extract_facility_inquiry
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.booking_slot_service import (
    FACILITIES_BY_REGION,
    FACILITY_MAPPING,
    clean_name,
    detect_booking_for,
    detect_context_reset,
    detect_facility_region,
    extract_booking_entities,
    is_facility_answer,
    match_slot,
    nearby_facilities,
    pick_listed_doctor,
    slot_date_period,
    verified_slots,
    wants_any_facility,
    wants_coordinator_scheduling,
)
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.disease_triage import ATSLevel, UrgencyTier
from src.medical_assistant.domain.doctor_resolution import name_supported_by_text, resolve_doctor
from src.medical_assistant.domain.guardrail_service import get_guardrail_service, remove_accents
from src.medical_assistant.domain.hybrid_dialogue_service import get_hybrid_dialogue_service
from src.medical_assistant.domain.language_service import (
    canonicalize_specialty_code,
    detect_language,
    get_specialty_display_name,
)
from src.medical_assistant.domain.probing_service import get_probing_service
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service
from src.medical_assistant.domain.triage_service import get_triage_service
from src.medical_assistant.domain.turn_relevance import is_gibberish, looks_off_topic

logger = logging.getLogger(__name__)

MAX_DETAILS_HISTORY = 4


def security_gate(query: str, lang: str, state: AgentState) -> dict[str, Any] | None:
    """Kiểm tra an toàn bảo mật, chống prompt injection, jailbreak và nội dung độc hại."""
    security_check = get_security_guardrail_service().inspect_query(query, language=lang)
    if security_check.is_safe:
        return None

    current_turn = state.get("probing_turn") or 0
    active_category = state.get("active_probing_category")
    collected_details = state.get("collected_details") or []
    clinical_facts = state.get("clinical_facts") or {}
    current_dept = state.get("suggested_department_name")

    return {
        "analysis": f"🛡️ Security Gateway: Attack Blocked ({security_check.violation_type}) [Lang: {lang.upper()}]",
        "is_emergency": False,
        "emergency_warning": None,
        "workflow_status": "SECURITY_BLOCKED",
        "probing_turn": current_turn,
        "active_probing_category": active_category,
        "collected_details": collected_details,
        "clinical_facts": clinical_facts,
        "suggested_department_name": current_dept,
        "ats_level": None,
        "urgency_tier": "BLOCKED",
        "max_booking_days": 0,
        "language": lang,
        "metadata": {
            "needs_more_probing": False,
            "security_blocked": True,
            "violation_type": security_check.violation_type,
            "detected_technique": security_check.detected_technique,
            "matched_pattern": security_check.matched_pattern,
            "security_response": security_check.safe_response,
            "quick_replies": security_check.quick_replies or [],
            "tokens_saved": True,
            "mutate_clinical_state": False,
        },
    }


def emergency_gate(query: str, lang: str, state: AgentState) -> dict[str, Any] | None:
    """Cổng an toàn y tế cấp cứu: phát hiện cờ đỏ và triệu chứng đe dọa tính mạng (ATS Level 1/2).

    Khớp MƠ HỒ (chữ không dấu đa nghĩa) không quyết ở đây: ambiguous_emergency_gate nhờ LLM khôi phục dấu."""
    triage_service = get_triage_service()
    emergency_fast_check = triage_service.evaluate_with_recent_context(query, state.get("messages"), language=lang)
    if not emergency_fast_check.is_emergency or emergency_fast_check.match_confidence == "ambiguous":
        return None
    return _emergency_state(emergency_fast_check, query, lang, state)


async def ambiguous_emergency_gate(query: str, lang: str, state: AgentState) -> tuple[dict[str, Any] | None, str]:
    """Cấp cứu khớp MƠ HỒ → (state cấp cứu | state hỏi xác nhận | None, câu dùng cho phần còn lại của lượt).

    None + câu đã khôi phục dấu = LLM xác định không phải cấp cứu → tư vấn tiếp với câu có dấu."""
    from src.medical_assistant.domain.ambiguity_resolution import resolve_ambiguous_emergency

    triage_service = get_triage_service()
    check = triage_service.evaluate_with_recent_context(query, state.get("messages"), language=lang)
    if not check.is_emergency or check.match_confidence != "ambiguous":
        return None, query
    decision = await resolve_ambiguous_emergency(triage_service, query, state.get("messages"), lang)
    logger.warning("AMBIGUOUS_EMERGENCY: %s rules=%s", decision.kind, decision.result.triggered_rule_ids)
    if decision.kind == "emergency":
        return _emergency_state(decision.result, decision.restored or query, lang, state), query
    if decision.kind == "clear":
        return None, decision.restored or query
    return _confirm_state(decision.result, query, lang, state, asks=1), query


def emergency_confirmation_gate(query: str, lang: str, state: AgentState) -> tuple[dict[str, Any] | None, str | None]:
    """Lượt trả lời câu hỏi xác nhận cấp cứu mơ hồ → (state, câu gốc cần tư vấn tiếp khi người dùng nói Không)."""
    from src.medical_assistant.domain.ambiguity_resolution import parse_yes_no

    pending = state.get("pending_emergency") or {}
    if not pending:
        return None, None
    answer = parse_yes_no(query)
    asks = int(pending.get("asks") or 1)
    if answer == "yes" or (answer is None and asks >= 2):
        # Xác nhận, hoặc hỏi 2 lần vẫn không rõ: an toàn là ưu tiên → cấp cứu đầy đủ
        result = get_triage_service().evaluate_with_recent_context(
            pending.get("query") or query, state.get("messages"), language=lang
        )
        result = result.model_copy(update={"match_confidence": "certain"})
        out = _emergency_state(result, pending.get("query") or query, lang, state)
        out["pending_emergency"] = None
        out["metadata"]["emergency_confirmation"] = "confirmed" if answer == "yes" else "unanswered_escalated"
        return out, None
    if answer == "no":
        return None, pending.get("query") or query
    result = get_triage_service().evaluate_with_recent_context(
        pending.get("query") or query, state.get("messages"), language=lang
    )
    return _confirm_state(result, pending.get("query") or query, lang, state, asks=asks + 1), None


def _confirm_state(result, query: str, lang: str, state: AgentState, asks: int) -> dict[str, Any]:
    """Hướng dẫn 115 CÓ ĐIỀU KIỆN + hỏi xác nhận Có/Không (không nâng cờ cấp cứu, không đẩy ca ưu tiên 0)."""
    return {
        "analysis": f"Ambiguous emergency match → confirm ({', '.join(result.triggered_rule_ids or [])})",
        "is_emergency": False,
        "workflow_status": "EMERGENCY_CONFIRM",
        "ats_level": result.ats_level.value,
        "collected_details": [*(state.get("collected_details") or []), query],
        "pending_emergency": {
            "query": query,
            "asks": asks,
            "flag": (result.triggered_red_flags or ["dấu hiệu nguy hiểm"])[0],
            "rule_ids": list(result.triggered_rule_ids or []),
        },
        "language": lang,
        "metadata": {
            "needs_more_probing": False,
            "triggered_rule_ids": result.triggered_rule_ids,
            "match_confidence": "ambiguous",
            "quick_replies": ["Có, đang bị như vậy", "Không phải"] if lang == "vi" else ["Yes", "No"],
            "tokens_saved": False,
        },
    }


def _emergency_state(emergency_fast_check, query: str, lang: str, state: AgentState) -> dict[str, Any]:
    current_turn = state.get("probing_turn") or 0
    active_category = state.get("active_probing_category")
    collected_details = state.get("collected_details") or []
    clinical_facts = state.get("clinical_facts") or {}

    return {
        "analysis": f"🚨 Emergency Safety Gate: ATS {emergency_fast_check.ats_level.value} ({', '.join(emergency_fast_check.triggered_red_flags)}) [Lang: {lang.upper()}]",
        "is_emergency": True,
        "emergency_warning": emergency_fast_check.patient_guidance,
        "workflow_status": "EMERGENCY",
        "probing_turn": current_turn,
        "active_probing_category": active_category,
        "collected_details": [*collected_details, query],
        "clinical_facts": clinical_facts,
        "suggested_department_name": emergency_fast_check.suggested_specialty,
        "ats_level": emergency_fast_check.ats_level.value,
        "urgency_tier": "EMERGENCY_BLOCK",
        "max_booking_days": 0,
        "language": lang,
        "pending_emergency": None,
        "metadata": {
            "needs_more_probing": False,
            "patient_guidance": emergency_fast_check.patient_guidance,
            "triggered_red_flags": emergency_fast_check.triggered_red_flags,
            "triggered_rule_ids": emergency_fast_check.triggered_rule_ids,
            "match_confidence": emergency_fast_check.match_confidence,
            "quick_replies": ["Gọi cấp cứu 115 ngay", "Đến phòng Cấp cứu gần nhất"]
            if lang == "vi"
            else ["Call Emergency 115", "Go to Emergency Room"],
            "tokens_saved": True,
        },
    }


async def cache_gate(query: str, lang: str, state: AgentState) -> dict[str, Any] | None:
    """Cổng tra cứu Zero-Token Cache, Appointment Lookup và Profile định danh bệnh nhân."""
    from src.medical_assistant.domain.booking_slot_service import detect_appointment_query

    current_turn = state.get("probing_turn") or 0
    collected_details = state.get("collected_details") or []
    current_dept = state.get("suggested_department_name")
    current_urgency = state.get("urgency_tier") or "STANDARD"
    current_max_days = state.get("max_booking_days") or 7

    cache_service = get_cache_service()
    cached = None
    folded_query = remove_accents(query.lower())
    is_cancel = bool(re.search(r"\bhuy\s+(?:lich|hen|yeu cau|phieu|dat)|\bcancel\b", folded_query))
    code_match = re.search(r"\bYC-?([0-9A-F]{8})\b", query, re.IGNORECASE)

    if is_cancel and code_match:
        from src.medical_assistant.domain.booking_lookup_service import get_booking_lookup_service

        code = f"YC-{code_match.group(1).upper()}"
        try:
            res = await get_booking_lookup_service().cancel_patient_request(
                code,
                user_id=state.get("user_id") or (state.get("metadata") or {}).get("user_id"),
                guest_token=state.get("guest_token") or "",
            )
        except Exception as exc:  # noqa: BLE001 - lỗi DB không được làm hỏng hội thoại
            logger.warning("Patient cancel failed: %s", exc)
            res = {"result": "error"}
        cancel_texts = {
            "cancelled": f"✅ Dạ, em đã **hủy yêu cầu đặt lịch `{code}`** cho bác. Khi cần, bác nhắn em để đặt lịch mới nhé ạ.",
            "handoff": (
                f"Dạ, yêu cầu `{code}` đang được điều phối viên xử lý nên em chưa tự hủy được. Em đã ghi nhận "
                "mong muốn hủy của bác; điều phối viên sẽ liên hệ xác nhận trong thời gian sớm nhất ạ."
            ),
            "not_found": (
                f"Dạ, em không tìm thấy yêu cầu `{code}` đang hoạt động trong tài khoản/phiên chat này. "
                "Bác kiểm tra lại mã phiếu, hoặc gọi tổng đài cơ sở để được hỗ trợ ạ."
            ),
        }
        text = cancel_texts.get(
            res.get("result"), "Dạ, hệ thống chưa xử lý được yêu cầu hủy lúc này. Bác vui lòng thử lại sau ít phút ạ."
        )
        cached = (text, ["Đặt lịch mới", "Tiến trình điều trị"], "PATIENT_CANCEL")
    elif code_match and re.search(r"\bdoi\s+(?:lich|hen|ngay|gio|buoi)|\breschedule\b", folded_query):
        from src.medical_assistant.domain.booking_lookup_service import _format_vn_date_str, get_booking_lookup_service
        from src.medical_assistant.domain.booking_slot_service import extract_booking_entities

        code = f"YC-{code_match.group(1).upper()}"
        wanted = extract_booking_entities(query, {})
        new_date, new_period = wanted.get("preferred_date"), wanted.get("preferred_period")
        if not new_date and not new_period:
            text = f"Dạ, bác muốn đổi lịch `{code}` sang ngày/buổi nào ạ? (ví dụ: *đổi lịch {code} sang sáng thứ 7*)"
        else:
            try:
                res = await get_booking_lookup_service().reschedule_patient_request(
                    code,
                    new_date,
                    new_period,
                    user_id=state.get("user_id") or (state.get("metadata") or {}).get("user_id"),
                    guest_token=state.get("guest_token") or "",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Patient reschedule failed: %s", exc)
                res = {"result": "error"}
            when = " ".join(
                x
                for x in [
                    {"morning": "buổi sáng", "afternoon": "buổi chiều", "evening": "buổi tối"}.get(new_period or ""),
                    _format_vn_date_str(new_date) if new_date else "",
                ]
                if x
            )
            text = {
                "updated": f"✅ Dạ, em đã cập nhật yêu cầu `{code}` sang **{when}**. Điều phối viên sẽ liên hệ xác nhận giờ khám cụ thể ạ.",
                "handoff": (
                    f"Dạ, yêu cầu `{code}` đã được điều phối viên tiếp nhận nên em chưa tự đổi được. Em đã ghi nhận "
                    f"mong muốn đổi sang **{when}**; điều phối viên sẽ liên hệ bác để sắp xếp lại ạ."
                ),
                "not_found": f"Dạ, em không tìm thấy yêu cầu `{code}` đang hoạt động trong tài khoản/phiên chat này ạ.",
            }.get(
                res.get("result"), "Dạ, hệ thống chưa xử lý được yêu cầu đổi lịch lúc này. Bác thử lại sau ít phút ạ."
            )
        cached = (text, ["Tiến trình điều trị", "Cần tư vấn thêm"], "PATIENT_RESCHEDULE")
    elif detect_appointment_query(query):
        from src.medical_assistant.domain.booking_lookup_service import get_booking_lookup_service

        lookup_svc = get_booking_lookup_service()
        user_id = state.get("user_id") or (state.get("metadata") or {}).get("user_id")
        user_phone = (state.get("patient_profile") or {}).get("phone") or state.get("patient_phone")
        user_name = (state.get("patient_profile") or {}).get("name") or state.get("patient_name")
        guest_tok = state.get("guest_token") or ""
        app_res = await lookup_svc.lookup_patient_appointments(
            user_id=user_id, phone=user_phone, guest_token=guest_tok, name=user_name
        )
        cached = (app_res["formatted_response"], ["Tiến trình điều trị", "Đặt lịch mới"], "APPOINTMENT_LOOKUP")
    else:
        identity_query = remove_accents(query.lower())
        clinical_keywords = [
            "dau",
            "sot",
            "ho",
            "kho tho",
            "non",
            "tieu chay",
            "benh",
            "kham",
            "chuyen khoa",
            "bac si",
            "trieu chung",
        ]
        has_clinical = any(re.search(rf"\b{kw}\b", identity_query) for kw in clinical_keywords)
        id_pattern = (
            r"(?:ten|so dien thoai|sdt|dia chi|thong tin(?: ca nhan)?|ho so)\s+(?:cua\s+)?(?:toi|minh)\b|"
            r"(?:hien thi|xem|kiem tra|cho biet)\s+(?:thong tin(?: ca nhan)?|ho so|ten|sdt|so dien thoai)\s+(?:cua\s+)?(?:toi|minh)\b|"
            r"\bmy\s+(?:name|phone|address|profile|info|contact)\b"
        )
        # "Tên tôi là X, sđt 09..." là CUNG CẤP thông tin (trả lời câu hỏi liên hệ), không phải hỏi hồ sơ.
        is_providing_identity = bool(
            re.search(r"(?<!\d)0\d{9}(?!\d)", re.sub(r"[\s.-]", "", query))
            or re.search(
                r"(?:ten|so dien thoai|sdt)\s+(?:cua\s+)?(?:toi|minh)\s+la\s+(?!gi\b|j\b|bao nhieu\b|the nao\b|so may\b)\w",
                identity_query,
            )
        )
        is_identity_query = (
            bool(re.search(id_pattern, identity_query)) and not has_clinical and not is_providing_identity
        )
        profile = state.get("patient_profile") or {}
        if is_identity_query:
            name = profile.get("name") or state.get("patient_name") or "Chưa cung cấp"
            phone = profile.get("phone") or state.get("patient_phone") or "Chưa cung cấp"
            address = profile.get("address") or state.get("patient_address") or "Chưa cập nhật địa chỉ"
            if lang == "vi":
                identity_response = (
                    f"📋 **Thông tin tài khoản/hồ sơ của Anh/Chị:**\n\n"
                    f"• 👤 **Họ và tên:** {name}\n"
                    f"• 📞 **Số điện thoại:** {phone}\n"
                    f"• 📍 **Địa chỉ:** {address}\n\n"
                    f"Anh/Chị có cần hỗ trợ tư vấn triệu chứng hoặc đặt lịch khám chuyên khoa không ạ?"
                )
            else:
                identity_response = (
                    f"📋 **Your Account/Profile Details:**\n\n"
                    f"• 👤 **Name:** {name}\n"
                    f"• 📞 **Phone:** {phone}\n"
                    f"• 📍 **Address:** {address}\n\n"
                    f"Would you like medical guidance or help booking an appointment?"
                )
            cached = (identity_response, ["Tư vấn khám bệnh", "Đặt lịch khám"], "SESSION_PROFILE")
        else:
            cached = cache_service.check_cache(query, language=lang)

    if cached is None:
        return None

    cached_response, cached_replies, faq_key = cached
    return {
        "analysis": f"⚡ Zero-Token Cache Hit: {faq_key} [Lang: {lang.upper()}]",
        "is_emergency": False,
        "emergency_warning": None,
        "ats_level": state.get("ats_level"),
        "urgency_tier": current_urgency or "FLEXIBLE",
        "max_booking_days": current_max_days or 30,
        "suggested_department_name": current_dept,
        "workflow_status": "FAQ_ANSWERED",
        "probing_turn": current_turn,
        "collected_details": collected_details,
        "language": lang,
        "metadata": {
            "needs_more_probing": False,
            "cached_response": cached_response,
            "quick_replies": cached_replies,
            "tokens_saved": True,
        },
    }


def resolve_action(
    intent_check: dict[str, Any] | None,
    booking_entities: dict[str, Any],
    v2_response: Any,
    triage_result: Any,
    clinical_facts: dict[str, Any],
    rule_facts: dict[str, Any],
    current_turn: int,
    active_category: str | None,
    should_ask_multi: bool,
    is_emergency: bool,
    is_describe_more: bool,
    has_explicit_booking_request: bool,
    query: str,
    state: AgentState,
) -> tuple[str, str, dict[str, Any]]:
    """
    Quyết định action với bảng ưu tiên tập trung, minh bạch:
    1. Quyền phủ quyết an toàn y tế & Pháp lý (Hard Veto - P0)
    2. Thao tác đặt khám trực tiếp (P1)
    3. Lâm sàng & Probing triệu chứng (P2) - Chiếm ưu tiên khi bệnh nhân có triệu chứng
    4. Tra cứu hành chính/Cơ sở/Khoa (P3) - Kích hoạt khi câu hỏi phi lâm sàng hoặc LLM đồng thuận
    5. Đề xuất từ LLM V2 (P4)
    """
    extra_args: dict[str, Any] = {}
    intent_name = (intent_check or {}).get("intent")
    probing_service = get_probing_service()

    # Lưu lại gợi ý từ regex làm hint cho state metadata (Prompt 5 / Prompt B: hint only)
    if intent_name:
        extra_args["intent_hint"] = intent_name
    if (intent_check or {}).get("department"):
        extra_args["department"] = intent_check["department"]
    if (intent_check or {}).get("requested_days"):
        extra_args["requested_days"] = intent_check["requested_days"]
    if (intent_check or {}).get("preferred_time"):
        extra_args["preferred_period"] = intent_check["preferred_time"]
    if (intent_check or {}).get("facility_name"):
        extra_args["facility_name"] = intent_check["facility_name"]
    if (intent_check or {}).get("facility_id"):
        extra_args["facility_id"] = intent_check["facility_id"]

    # --- ƯU TIÊN 0: Quyền phủ quyết an toàn y tế & Pháp lý (Hard Veto) ---
    if intent_name == "MEDICATION_GUARDRAIL":
        reason = "Quy tắc an toàn thuốc (RULE-SAF-02): Không kê đơn hay hướng dẫn liều dùng thuốc"
        logger.info("RESOLVE_ACTION: action=decline_medication_request, reason=%s", reason)
        return "decline_medication_request", reason, extra_args

    if intent_name == "DIAGNOSIS_GUARDRAIL":
        reason = "Quy tắc an toàn chẩn đoán (RULE-SAF-01): Không khẳng định bệnh thay bác sĩ"
        logger.info("RESOLVE_ACTION: action=respond_to_diagnosis_request, reason=%s", reason)
        return "respond_to_diagnosis_request", reason, extra_args

    if "HEADACHE_WITH_VISUAL_CHANGE" in triage_result.triggered_rule_ids:
        reason = "Cảnh báo an toàn thần kinh: Đau đầu kèm biến đổi thị giác (VETO)"
        logger.info("RESOLVE_ACTION: action=request_safety_review, reason=%s", reason)
        return "request_safety_review", reason, extra_args

    if intent_name == "HOLD_BOOKING":
        reason = "Yêu cầu giữ chỗ slot hẹn với ID cụ thể"
        extra_args["slot_id"] = (intent_check or {}).get("slot_id")
        logger.info("RESOLVE_ACTION: action=hold_slot, reason=%s", reason)
        return "hold_slot", reason, extra_args

    # --- ƯU TIÊN 1: Thao tác đặt khám trực tiếp & Đặt hẹn ---
    # Lượt trước đã hỏi họ tên + SĐT để chốt lịch, lượt này bệnh nhân gửi SĐT → chốt yêu cầu đặt lịch.
    awaiting_contact = state.get("workflow_status") in {
        "CONFIRM_BOOKING_CONVERSATIONALLY",
        "BOOKING_CONTACT_REQUIRED",
        "TRIAGED_READY_FOR_BOOKING",  # đã hiện lịch trống, bệnh nhân gửi SĐT = muốn đặt
        "FACILITY_CHOICE_REQUIRED",  # đang hỏi nơi khám mà gửi họ tên + SĐT → vẫn ghi nhận yêu cầu đặt lịch
        "SLOT_CHOICE_REQUIRED",
    }
    gave_contact = bool(booking_entities.get("patient_phone") or re.search(r"\d{4,}", query or ""))
    # Đặt hộ: lượt trước đã hỏi tên/năm sinh/SĐT của người khám → câu trả lời tiếp tục luồng chốt phiếu.
    answered_proxy = bool(
        _proxy_answer(query, state.get("awaiting_field"))
        or booking_entities.get("patient_name")
        or booking_entities.get("date_of_birth")
        or gave_contact
    )
    if state.get("awaiting_field") and state.get("booking_for") == "other" and answered_proxy and not is_emergency:
        reason = "Người dùng trả lời thông tin người khám (đặt hộ)"
        logger.info("RESOLVE_ACTION: action=confirm_booking_conversationally, reason=%s", reason)
        return "confirm_booking_conversationally", reason, extra_args
    if awaiting_contact and gave_contact and not is_emergency:
        reason = "Bệnh nhân cung cấp liên hệ cho yêu cầu đặt lịch đang chờ"
        logger.info("RESOLVE_ACTION: action=confirm_booking_conversationally, reason=%s", reason)
        return "confirm_booking_conversationally", reason, extra_args

    if booking_entities.get("is_booking_confirmation") and not is_emergency:
        reason = "Bệnh nhân xác nhận thông tin đặt khám qua hội thoại"
        logger.info("RESOLVE_ACTION: action=confirm_booking_conversationally, reason=%s", reason)
        return "confirm_booking_conversationally", reason, extra_args

    # "Trong người không khỏe": kể chung chung → hỏi kiểu khó chịu kèm nút đời thường, không hiện menu mục đích khám.
    if (
        intent_name == "VAGUE_COMPLAINT"
        and not is_emergency
        and not rule_facts.get("chief_complaint")
        and not rule_facts.get("positive_facts")
    ):
        reason = "Người dùng kể chung chung, chưa có triệu chứng cụ thể → hỏi kiểu khó chịu kèm gợi ý"
        logger.info("RESOLVE_ACTION: action=ask_clarifying_question, reason=%s", reason)
        return "ask_clarifying_question", reason, extra_args

    # "Tôi đang muốn khám bệnh ở bệnh viện": chữ "khám bệnh" làm is_booking_intent=True, nhưng chưa có triệu chứng,
    # khoa hay bác sĩ → phải hỏi mục đích, không tự gán khoa rồi tra lịch (từng ra Tim mạch khi LLM bật).
    if (
        (intent_name == "VISIT_PURPOSE_CLARIFICATION" or v2_response.primary_intent == "clarify_visit_purpose")
        and not booking_entities.get("is_doctor_inquiry")
        and not booking_entities.get("specialty_preference")
        and not booking_entities.get("doctor_preference")
        and not rule_facts.get("chief_complaint")
        and not rule_facts.get("positive_facts")  # "ợ nóng": có triệu chứng dù chưa thành triệu chứng chính
        and v2_response.primary_intent != "symptom_report"
        and not (intent_check or {}).get("department")
        and not state.get("suggested_department_name")  # đã có khoa từ lượt trước → không hỏi lại từ đầu
    ):
        reason = "Yêu cầu khám chung chung, chưa rõ triệu chứng/khoa → hỏi mục đích khám"
        logger.info("RESOLVE_ACTION: action=clarify_visit_purpose, reason=%s", reason)
        return "clarify_visit_purpose", reason, extra_args

    if (
        booking_entities.get("is_doctor_inquiry")
        or has_explicit_booking_request
        or v2_response.primary_intent == "schedule_request"
    ):
        reason = "Bệnh nhân yêu cầu tra cứu lịch trống hoặc thông tin bác sĩ điều trị"
        if (intent_check or {}).get("requested_days"):
            extra_args["requested_days"] = intent_check["requested_days"]
        if (intent_check or {}).get("preferred_time"):
            extra_args["preferred_period"] = intent_check["preferred_time"]
        if (intent_check or {}).get("department"):
            extra_args["department"] = intent_check["department"]
        logger.info("RESOLVE_ACTION: action=search_available_slot, reason=%s", reason)
        return "search_available_slot", reason, extra_args

    # Kiểm tra xem người dùng có đang báo cáo triệu chứng lâm sàng hay không
    has_clinical_symptoms = bool(
        rule_facts.get("chief_complaint")
        or clinical_facts.get("active_complaint_codes")
        or clinical_facts.get("positive_facts")
        or v2_response.primary_intent == "symptom_report"
    )

    # --- ƯU TIÊN 2: Khám lâm sàng & Probing (khi người bệnh có triệu chứng) ---
    if has_clinical_symptoms:
        if should_ask_multi:
            reason = "Bệnh nhân có nhiều triệu chứng cần phân định triệu chứng chính"
            logger.info("RESOLVE_ACTION: action=ask_clarifying_question, reason=%s", reason)
            return "ask_clarifying_question", reason, extra_args

        if (
            rule_facts.get("chief_complaint")
            and current_turn < 2
            and not triage_result.needs_multi_symptom_clarification
            and (probing_service.find_probing_tree(query) or active_category)
        ):
            reason = "Bệnh nhân mới nêu triệu chứng chính lượt đầu; cần hỏi thêm chi tiết lâm sàng (thời gian/vị trí)"
            logger.info("RESOLVE_ACTION: action=ask_clarifying_question, reason=%s", reason)
            return "ask_clarifying_question", reason, extra_args

        if is_describe_more:
            reason = "Người dùng bấm mô tả thêm triệu chứng"
            logger.info("RESOLVE_ACTION: action=clarify_visit_purpose, reason=%s", reason)
            return "clarify_visit_purpose", reason, extra_args
        if (
            getattr(v2_response, "needs_clarification", False) or v2_response.proposed_action == "clarify_visit_purpose"
        ) and intent_name not in {"FACILITY_INFO", "FACILITY_DOCTORS", "DEPARTMENT_INFO", "VIEW_SCHEDULE"}:
            # Đã nêu triệu chứng ("nổi mẩn đỏ ở tay và miệng") → hỏi thêm về triệu chứng, không quay về menu
            # "khám vì triệu chứng / khám tổng quát / ..." như thể người dùng chưa nói gì.
            reason = "Có triệu chứng nhưng LLM cần làm rõ thêm → hỏi tiếp về triệu chứng"
            logger.info("RESOLVE_ACTION: action=ask_clarifying_question, reason=%s", reason)
            return "ask_clarifying_question", reason, extra_args

    # Trích xuất tham số bổ trợ từ các intent hành chính (chỉ dùng làm gợi ý, không tự quyết định action)
    if intent_name == "DEPARTMENT_INFO":
        extra_args["department_query"] = (intent_check or {}).get("department_query")
        extra_args["comparison_requested"] = bool((intent_check or {}).get("comparison_requested"))
    elif intent_name == "VIEW_SCHEDULE":
        if (intent_check or {}).get("requested_days"):
            extra_args["requested_days"] = intent_check["requested_days"]
        if (intent_check or {}).get("preferred_time"):
            extra_args["preferred_period"] = intent_check["preferred_time"]
        if (intent_check or {}).get("department"):
            extra_args["department"] = intent_check["department"]

    # Nếu không có triệu chứng lâm sàng nhưng người dùng bấm "mô tả thêm" hoặc v2_response đòi hỏi clarify
    if (
        is_describe_more
        or (getattr(v2_response, "needs_clarification", False) is True)
        or (v2_response and getattr(v2_response, "proposed_action", None) == "clarify_visit_purpose")
    ):
        reason = "Mục đích khám chưa đủ rõ ràng hoặc người dùng bấm mô tả thêm triệu chứng"
        logger.info("RESOLVE_ACTION: action=clarify_visit_purpose, reason=%s", reason)
        return "clarify_visit_purpose", reason, extra_args

    # --- ƯU TIÊN 4: Quyết định từ LLM V2 / Router (Regex hành chính chỉ là fallback khi LLM không có đề xuất) ---
    admin_intent_action_map = {
        "DEPARTMENT_INFO": "show_department_info",
        "FACILITY_INFO": "show_facility_info",
        "FACILITY_DOCTORS": "show_facility_doctors",
        "FACILITY_BOOKING_START": "start_facility_booking",
        "BOOKING_CONTACT_REQUEST": "request_human_help",
        "VIEW_SCHEDULE": "search_available_slot",
    }

    if v2_response and v2_response.proposed_action:
        action = v2_response.proposed_action
        reason = f"Quyết định bởi LLM V2 ({action})" + (f" [Gợi ý regex: {intent_name}]" if intent_name else "")
    elif intent_name in admin_intent_action_map:
        action = admin_intent_action_map[intent_name]
        reason = f"Fallback sang gợi ý regex ({action}) do LLM không có đề xuất cụ thể"
    else:
        action = "suggest_specialty"
        reason = "Đề xuất mặc định định tuyến chuyên khoa"

    logger.info("RESOLVE_ACTION: action=%s, reason=%s", action, reason)
    return action, reason, extra_args


# Bỏ ngữ cảnh ("quên tất cả tư vấn trên"): xóa triệu chứng, khoa, lịch và phiếu đang giữ.
# Giữ danh tính tài khoản và cờ cấp cứu (cổng cấp cứu vẫn chạy lại mỗi lượt, không phụ thuộc ngữ cảnh cũ).
EPISODE_RESET_VALUES: dict[str, Any] = {
    "suggested_department_name": None,
    "suggested_department_code": None,
    "ats_level": None,
    "urgency_tier": None,
    "max_booking_days": None,
    "clinical_facts": {},
    "collected_details": [],
    "probing_turn": 0,
    "active_probing_category": None,
    "active_probing_categories": [],
    "probing_by_complaint": {},
    "booking_intake": {},
    "preferred_date": None,
    "preferred_period": None,
    "facility_preference": None,
    "facility_region": None,
    "facility_choice_skipped": None,
    "chosen_doctor": None,
    "chosen_slot": None,
    "doctor_preference": None,
    "doctor_name": None,
    "available_slots": [],
    "candidate_specialties": [],
    "routing_candidates": [],
    "last_listed_doctors": [],
    "booking_for": None,
    "proxy_patient": {},
    "awaiting_field": None,
    "workflow_status": "IDLE",
}
# Ý định có thể gỡ khi người dùng đang trả lời câu chọn nơi khám / bác sĩ / giờ ("Hà Nội", "Times City", "nào cũng
# được"): chỉ nhóm thông tin/xã giao. Không bao giờ gỡ chặn thuốc/chẩn đoán, giữ chỗ, xem lịch.
CHOICE_OVERRIDABLE_INTENTS = {
    "FACILITY_INFO",
    "FACILITY_DOCTORS",
    "DEPARTMENT_INFO",
    "SOCIAL_STATEMENT",
    "SELF_CARE_FOLLOWUP",
    "VISIT_PURPOSE_CLARIFICATION",
    "VAGUE_COMPLAINT",
}
# Hành động an toàn đã quyết định thì bước chọn nơi khám / bác sĩ / giờ không được ghi đè.
SAFETY_ACTIONS = {"decline_medication_request", "respond_to_diagnosis_request", "request_safety_review"}

_RESET_METADATA_KEYS = {
    "booking_intake",
    "clarification_question",
    "facility_preference",
    "time_preference",
    "awaiting_field",
}


def _reset_episode(state: AgentState) -> AgentState:
    metadata = {k: v for k, v in (state.get("metadata") or {}).items() if k not in _RESET_METADATA_KEYS}
    return {**state, **EPISODE_RESET_VALUES, "metadata": metadata}  # type: ignore[return-value]


def _short_turn_result(
    state: AgentState,
    lang: str,
    workflow_status: str,
    *,
    context_reset: bool,
    booking_for: str | None,
    extra: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Kết quả lượt không qua phân tầng lâm sàng (chọn bác sĩ, không tìm thấy bác sĩ, chỉ bỏ ngữ cảnh)."""
    result: dict[str, Any] = dict(EPISODE_RESET_VALUES) if context_reset else {}
    result.update(
        {
            "analysis": f"Deterministic: {workflow_status}",
            "is_emergency": False,
            "emergency_warning": None,
            "workflow_status": workflow_status,
            "booking_for": booking_for,
            "language": lang,
            "messages": list(state.get("messages") or []),
            "metadata": {
                "needs_more_probing": False,
                "llm_invoked": True,
                "context_reset": context_reset,
                **(metadata or {}),
            },
        }
    )
    result.update(extra or {})
    return result


def _proxy_answer(query: str, awaiting_field: str | None) -> dict[str, str]:
    """Câu trả lời ngắn cho câu hỏi đang chờ khi đặt hộ: "Trần Văn Bình" → tên, "1960"/"65 tuổi" → năm sinh."""
    text = (query or "").strip()
    if awaiting_field == "patient_name":
        words = text.replace(",", " ").split()
        if 2 <= len(words) <= 5 and not re.search(r"\d", text):
            return {"patient_name": clean_name(text)}
    if awaiting_field == "date_of_birth":
        from datetime import date

        year = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text)
        if year:
            return {"date_of_birth": f"{year.group(1)}-01-01"}
        age = re.search(r"\b(\d{1,3})\s*tuổi\b", text.lower())
        if age and 0 < int(age.group(1)) < 120:
            return {"date_of_birth": f"{date.today().year - int(age.group(1))}-01-01"}
    return {}


_pick_listed_doctor = pick_listed_doctor  # tên cũ (test/nhánh khác vẫn dùng)


async def analyze_node(state: AgentState) -> dict:
    query = state.get("query") or state.get("user_input", "")
    current_lang = state.get("language")
    detected_lang = detect_language(query)

    lower_query = query.lower()
    if any(p in lower_query for p in ["tiếng việt", "tieng viet", "bằng tiếng việt", "vietnamese", "nói tiếng việt"]):
        lang = "vi"
    elif any(p in lower_query for p in ["english", "in english", "speak english"]):
        lang = "en"
    elif current_lang and current_lang != detected_lang and len(query.strip().split()) >= 3:
        # "John Smith, 0912888777" (tên + SĐT, không dấu) không phải tín hiệu đổi ngôn ngữ.
        is_contact_only = re.search(r"\d{6,}", query) and remove_accents(query.lower()) == query.lower()
        lang = current_lang if is_contact_only else detected_lang
    else:
        lang = current_lang or detected_lang

    # "Quên tất cả tư vấn trên…": bỏ triệu chứng/khoa/lịch cũ trước khi đọc ngữ cảnh.
    # (LLM cũng có thể báo topic_change="reset"; xử lý sau khi gọi LLM.)
    context_reset = detect_context_reset(query)
    if context_reset:
        state = _reset_episode(state)

    current_turn = state.get("probing_turn") or 0
    active_category = state.get("active_probing_category")
    active_categories = list(
        state.get("active_probing_categories") or ([] if not active_category else [active_category])
    )
    probing_by_complaint = dict(state.get("probing_by_complaint") or {})
    collected_details = list(state.get("collected_details") or [])
    current_dept = state.get("suggested_department_name")
    current_ats = state.get("ats_level") or 4
    current_urgency = state.get("urgency_tier") or "STANDARD"
    current_max_days = state.get("max_booking_days") or 7
    clinical_facts = dict(state.get("clinical_facts") or {})

    facility_pref = state.get("metadata", {}).get("facility_preference")
    time_pref = state.get("metadata", {}).get("time_preference")

    # GATE 1: Security Gateway (Prompt Injection, Jailbreak, Safety)
    sec_gate_res = security_gate(query, lang, state)
    if sec_gate_res is not None:
        return sec_gate_res

    # GATE 1b: Trả lời câu hỏi xác nhận cấp cứu mơ hồ (Có → cấp cứu; Không → tư vấn tiếp câu gốc; không rõ → hỏi lại)
    confirm_res, resumed_query = emergency_confirmation_gate(query, lang, state)
    if confirm_res is not None:
        return confirm_res
    if resumed_query is not None:
        query = resumed_query
        state = {**state, "pending_emergency": None}

    # GATE 2: Emergency Safety Gate (ATS Level 1/2 Red Flags)
    emg_gate_res = emergency_gate(query, lang, state)
    if emg_gate_res is not None:
        return emg_gate_res
    # GATE 2b: Khớp MƠ HỒ (thiếu dấu, chữ đa nghĩa): LLM khôi phục dấu → cấp cứu / tư vấn tiếp với câu có dấu / hỏi
    # xác nhận. Người dùng vừa trả lời "Không phải" thì không hỏi lại cùng câu.
    ambiguity_resolved = resumed_query is not None  # người dùng đã trả lời "Không phải"
    if resumed_query is None:
        original_query = query
        amb_res, query = await ambiguous_emergency_gate(query, lang, state)
        if amb_res is not None:
            return amb_res
        ambiguity_resolved = query != original_query  # LLM khôi phục dấu → không phải cấp cứu

    # GATE 3: Zero-Token Cache & Appointment/Profile Lookup
    cache_gate_res = await cache_gate(query, lang, state)
    if cache_gate_res is not None:
        return cache_gate_res

    # 6-HOOK AGENT MIDDLEWARE PIPELINE
    from src.medical_assistant.domain.middleware_pipeline import get_middleware_pipeline

    middleware = get_middleware_pipeline()

    allowed_actions = [
        "clarify_visit_purpose",
        "ask_clarifying_question",
        "suggest_specialty",
        "search_available_slot",
        "hold_slot",
        "answer_faq",
        "show_department_info",
        "show_facility_info",
        "show_facility_doctors",
        "start_facility_booking",
        "decline_medication_request",
        "respond_to_diagnosis_request",
        "request_safety_review",
        "request_human_help",
        "acknowledge_language_change",
        "confirm_booking_conversationally",
    ]

    # HOOK 2: before_model_call (Action Space Pruning)
    allowed_actions, candidate_specs = middleware.execute_hook_2_before_model(
        allowed_actions=allowed_actions,
        state=state,
    )

    # Câu hỏi bot vừa hỏi: lưu ở state.pending_question (metadata bị router ghi đè mỗi lượt).
    last_assistant_question = state.get("pending_question") or state.get("metadata", {}).get("clarification_question")

    # HOOK 1: on_user_input (Security Audit & Intent Interception)
    intent_check, _ = middleware.execute_hook_1_user_input(
        query=query,
        state=state,
        current_dept=current_dept,
        language=lang,
    )
    if not intent_check:
        fac_inquiry, fac_reg = extract_facility_inquiry(query)
        if fac_inquiry:
            intent_check = {
                "intent": "FACILITY_INFO",
                "matched_pattern": "smart_facility_extraction",
                "region_filter": fac_reg,
                "district_filter": None,
                "facility_name_query": None,
            }

    # Đang chờ chọn khu vực/cơ sở: câu trả lời ngắn ("Hà Nội", "TP.HCM", "Times City", "nào cũng được") không được
    # để nhánh xã giao/thông tin cơ sở/lọc vô nghĩa bắt mất — xử lý ở bước hỏi nơi khám bên dưới.
    facility_answer = state.get("workflow_status") == "FACILITY_CHOICE_REQUIRED" and is_facility_answer(query)
    # Tương tự với câu chọn bác sĩ / giờ khám ngay sau danh sách bác sĩ có lịch trống.
    if state.get("workflow_status") in {"TRIAGED_READY_FOR_BOOKING", "SLOT_CHOICE_REQUIRED"}:
        listed_for_choice = state.get("last_listed_doctors") or []
        facility_answer = facility_answer or bool(
            _pick_listed_doctor(query, listed_for_choice, allow_bare=True)
            or match_slot(query, listed_for_choice, state.get("chosen_doctor"))
            or (listed_for_choice and wants_any_facility(query))
        )
    # Chỉ gỡ ý định thông tin/xã giao hay bắt nhầm câu trả lời ngắn. Chặn thuốc/chẩn đoán (SAF-02), giữ chỗ, xem lịch
    # luôn giữ: "Hà Nội, mà tôi nên uống thuốc gì?" vẫn phải được từ chối kê đơn.
    if facility_answer:
        clinical_guardrail = get_guardrail_service().detect_clinical_guardrail(query, current_dept, lang)
        if clinical_guardrail:
            intent_check = clinical_guardrail
        elif (intent_check or {}).get("intent") in CHOICE_OVERRIDABLE_INTENTS:
            intent_check = None

    boundary_intent = (intent_check or {}).get("intent")
    if boundary_intent == "SPECIALIZED_PROCEDURE_INQUIRY":
        dept_code = "MAT" if any(w in query.lower() for w in ["cận", "lasik", "mắt", "khúc xạ"]) else None
        dept_name = "Mắt (Nhãn khoa)" if dept_code == "MAT" else None
        return {
            "analysis": "Specialized procedure inquiry -> offer HITL escalation",
            "is_emergency": False,
            "emergency_warning": None,
            "ats_level": None,
            "urgency_tier": None,
            "max_booking_days": None,
            "suggested_department_code": dept_code,
            "suggested_department_name": dept_name,
            "patient_name": state.get("patient_name"),
            "workflow_status": "HITL_AWAITING_CONFIRMATION",
            "probing_turn": current_turn,
            "active_probing_category": None,
            "collected_details": collected_details,
            "clinical_facts": clinical_facts,
            "available_slots": [],
            "language": lang,
            "metadata": {
                "needs_more_probing": False,
                "quick_replies": ["Yêu cầu hỗ trợ", "Không"],
                "tokens_saved": True,
                "llm_invoked": False,
                "llm_succeeded": False,
                "specialized_procedure": True,
            },
        }

    if boundary_intent == "HITL_CONFIRM":
        return {
            "analysis": "Patient confirmed HITL escalation -> coordinator role notified",
            "is_emergency": False,
            "emergency_warning": None,
            "ats_level": None,
            "urgency_tier": None,
            "max_booking_days": None,
            "suggested_department_code": state.get("suggested_department_code"),
            "suggested_department_name": state.get("suggested_department_name"),
            "patient_name": state.get("patient_name"),
            "workflow_status": "HITL_ESCALATED_COORDINATOR",
            "probing_turn": current_turn,
            "active_probing_category": None,
            "collected_details": collected_details,
            "clinical_facts": clinical_facts,
            "available_slots": [],
            "language": lang,
            "metadata": {
                "needs_more_probing": False,
                "quick_replies": ["Để lại thông tin liên hệ", "Hỏi câu hỏi khác"],
                "tokens_saved": True,
                "llm_invoked": False,
                "llm_succeeded": False,
                "coordinator_notified": True,
            },
        }

    if boundary_intent == "HITL_DECLINE":
        return {
            "analysis": "Patient declined HITL escalation -> conversational prompt",
            "is_emergency": False,
            "emergency_warning": None,
            "ats_level": None,
            "urgency_tier": None,
            "max_booking_days": None,
            "suggested_department_code": None,
            "suggested_department_name": None,
            "patient_name": state.get("patient_name"),
            "workflow_status": "HITL_DECLINED_CONVERSATIONAL",
            "probing_turn": current_turn,
            "active_probing_category": None,
            "collected_details": collected_details,
            "clinical_facts": clinical_facts,
            "available_slots": [],
            "language": lang,
            "metadata": {
                "needs_more_probing": False,
                "quick_replies": ["Mô tả triệu chứng", "Tìm bệnh viện", "Tra cứu bác sĩ"],
                "tokens_saved": True,
                "llm_invoked": False,
                "llm_succeeded": False,
            },
        }

    if boundary_intent in {"SOCIAL_STATEMENT", "THIRD_PARTY_HEALTH_QUERY", "SELF_CARE_FOLLOWUP"}:
        workflow_by_intent = {
            "SOCIAL_STATEMENT": "SOCIAL_REDIRECT",
            "THIRD_PARTY_HEALTH_QUERY": "THIRD_PARTY_HEALTH_GUIDANCE",
            "SELF_CARE_FOLLOWUP": "TRIAGED_AWAITING_SCHEDULE",
        }
        return {
            "analysis": f"Conversation boundary: {boundary_intent} | clinical episode preserved",
            "is_emergency": state.get("is_emergency", False),
            "emergency_warning": state.get("emergency_warning"),
            "ats_level": current_ats,
            "urgency_tier": current_urgency,
            "max_booking_days": current_max_days,
            "suggested_department_code": state.get("suggested_department_code"),
            "suggested_department_name": current_dept,
            "patient_name": state.get("patient_name"),
            "workflow_status": workflow_by_intent[boundary_intent],
            "probing_turn": current_turn,
            "active_probing_category": active_category,
            "collected_details": collected_details,
            "clinical_facts": clinical_facts,
            "available_slots": state.get("available_slots") or [],
            "language": lang,
            "metadata": {
                "needs_more_probing": False,
                "quick_replies": [],
                "tokens_saved": True,
                "llm_invoked": False,
                "llm_succeeded": False,
                "preserve_clinical_episode": True,
                "third_party_topic": (intent_check or {}).get("topic"),
            },
        }

    # HYBRID DIALOGUE V2: LLM suy luận ngữ cảnh tự nhiên
    hybrid_service = get_hybrid_dialogue_service()
    v2_response, llm_succeeded = await hybrid_service.process_turn_async(
        text=query,
        state={**state, "language": lang},
        recent_turns=collected_details,
        last_assistant_question=last_assistant_question,
        allowed_actions=allowed_actions,
    )
    skip_llm = False

    # LLM hiểu được cách nói mà regex bỏ sót ("thôi bỏ qua mấy cái đó") → bỏ ngữ cảnh như trên.
    if llm_succeeded and not context_reset and getattr(v2_response, "topic_change", "none") == "reset":
        context_reset = True
        state = _reset_episode(state)
        current_turn = 0
        active_category = None
        active_categories = []
        probing_by_complaint = {}
        collected_details = []
        current_dept = None
        current_ats = 4
        current_urgency = "STANDARD"
        current_max_days = 7
        clinical_facts = {}
        facility_pref = None
        time_pref = None

    department_query = (intent_check or {}).get("department_query")
    comparison_requested = bool((intent_check or {}).get("comparison_requested"))
    if intent_check and intent_check.get("department"):
        v2_response.action_args.specialty_key = intent_check.get("department")

    fact_service = get_clinical_fact_service()
    conversation_turn = 1 + sum(1 for message in (state.get("messages") or []) if message.get("role") == "user")
    rule_facts = fact_service.extract(
        query, turn_index=conversation_turn, in_episode=bool(clinical_facts.get("chief_complaint"))
    )
    if (
        rule_facts.get("primary_complaint")
        and intent_check
        and intent_check.get("intent") in {"DIAGNOSIS_GUARDRAIL", "MEDICATION_GUARDRAIL"}
    ):
        rule_facts["primary_complaint_explicit"] = True
        rule_facts["primary_complaint_explicit_code"] = rule_facts["primary_complaint"]

    extracted_facts = hybrid_service.adapt_v2_to_v1(v2_response, llm_succeeded=llm_succeeded)
    response_subject = getattr(v2_response.facts_delta, "subject", "unknown")
    is_self_clinical_turn = bool(
        response_subject != "other"
        and (
            rule_facts.get("chief_complaint")
            or rule_facts.get("complaints")
            or rule_facts.get("positive_facts")
            or rule_facts.get("negative_facts")
            or rule_facts.get("duration_days") is not None
            or v2_response.primary_intent == "symptom_report"
        )
    )
    if is_self_clinical_turn:
        clinical_facts = fact_service.merge(clinical_facts, rule_facts)
        clinical_facts = fact_service.merge(clinical_facts, extracted_facts)

    booking_entities = extract_booking_entities(query, state)
    # "Đặt lịch với bác sĩ đầu tiên / thứ 2" → lấy từ danh sách bác sĩ vừa hiển thị ở lượt trước.
    picked_doctor = _pick_listed_doctor(
        query,
        state.get("last_listed_doctors") or [],
        # Ngay sau câu hỏi chọn bác sĩ: chấp nhận câu ngắn "số 2", "2".
        allow_bare=state.get("workflow_status") in {"DOCTOR_CHOICE_REQUIRED", "TRIAGED_READY_FOR_BOOKING"},
    )
    if picked_doctor and not re.search(r"\d{1,2}/\d{1,2}", query):
        # "bác sĩ thứ 2" là thứ tự trong danh sách, không phải ngày thứ Hai.
        booking_entities.pop("preferred_date", None)
    if picked_doctor and not booking_entities.get("doctor_preference"):
        booking_entities["doctor_preference"] = picked_doctor["full_name"]
        booking_entities["doctor_name"] = f"BS. {picked_doctor['full_name']}"
        if picked_doctor.get("specialty") and not booking_entities.get("specialty_preference"):
            booking_entities["specialty_preference"] = picked_doctor["specialty"]
        if picked_doctor.get("workplace") and not booking_entities.get("facility_preference"):
            workplace = picked_doctor["workplace"].lower()
            booking_entities["facility_preference"] = next(
                (FACILITY_MAPPING[k] for k in sorted(FACILITY_MAPPING, key=len, reverse=True) if k in workplace),
                picked_doctor["workplace"],
            )
    intake_state = state.get("booking_intake") or (state.get("metadata") or {}).get("booking_intake") or {}
    awaiting_field = state.get("awaiting_field")

    # Bác sĩ người dùng nêu tên: regex ("bác si"/"BS" + tên) hoặc LLM (chỉ khi tên có thật trong câu).
    doctor_query = None
    doctor_title_hint = booking_entities.get("doctor_title_hint")
    if not picked_doctor and booking_entities.get("doctor_preference") not in (None, "", "coordinator"):
        doctor_query = booking_entities["doctor_preference"]
    llm_doctor = getattr(v2_response.action_args, "doctor_name", None) if llm_succeeded else None
    if not picked_doctor and not doctor_query and llm_doctor and name_supported_by_text(llm_doctor, query):
        doctor_query = llm_doctor.strip()
        doctor_title_hint = doctor_title_hint or getattr(v2_response.action_args, "doctor_title_hint", None)

    # Người khám: regex ("khám cho người nhà", "người khám không phải tôi") hoặc LLM subject=other
    # trong ngữ cảnh đặt lịch; giữ nguyên lựa chọn ở các lượt sau cho tới khi người dùng đổi/bỏ ngữ cảnh.
    booking_context = bool(
        booking_entities.get("is_booking_intent")
        or doctor_query
        or picked_doctor
        or awaiting_field
        or state.get("workflow_status")
        in {"TRIAGED_READY_FOR_BOOKING", "CONFIRM_BOOKING_CONVERSATIONALLY", "BOOKING_CONTACT_REQUIRED"}
    )
    booking_for = detect_booking_for(query)
    if (
        booking_for is None
        and llm_succeeded
        and booking_context
        and getattr(v2_response.facts_delta, "subject", "unknown") == "other"
    ):
        booking_for = "other"
    booking_for = booking_for or state.get("booking_for")

    explicit_doctor = False
    if doctor_query:
        resolution = await resolve_doctor(doctor_query, doctor_title_hint)
        if not resolution.data_unavailable and not resolution.candidates:
            return _short_turn_result(
                state,
                lang,
                "DOCTOR_NOT_FOUND",
                context_reset=context_reset,
                booking_for=booking_for,
                metadata={"doctor_query": doctor_query},
            )
        if len(resolution.candidates) > 1:
            # Trùng tên: liệt kê để người dùng chọn, không tự chọn thay (kể cả khi chức danh gợi ý một người).
            return _short_turn_result(
                state,
                lang,
                "DOCTOR_CHOICE_REQUIRED",
                context_reset=context_reset,
                booking_for=booking_for,
                extra={"last_listed_doctors": resolution.candidates},
                metadata={
                    "doctor_query": doctor_query,
                    "doctor_candidates": resolution.candidates,
                    "doctor_exact_match": resolution.exact,
                    "doctor_title_hint": doctor_title_hint,
                },
            )
        unique = resolution.unique
        if unique:
            explicit_doctor = True
            booking_entities["doctor_preference"] = unique["full_name"]
            booking_entities["doctor_name"] = f"BS. {unique['full_name']}"
            if unique.get("specialty"):
                booking_entities["specialty_preference"] = unique["specialty"]
            if unique.get("workplace") and not booking_entities.get("facility_preference"):
                workplace = unique["workplace"].lower()
                booking_entities["facility_preference"] = next(
                    (FACILITY_MAPPING[k] for k in sorted(FACILITY_MAPPING, key=len, reverse=True) if k in workplace),
                    unique["workplace"],
                )
    elif picked_doctor:
        explicit_doctor = True

    # Chỉ nói "quên hết/bắt đầu lại" mà không kèm yêu cầu mới → xác nhận ngắn, hỏi cần hỗ trợ gì.
    if context_reset and not (
        booking_entities.get("is_booking_intent")
        or explicit_doctor
        or booking_for == "other"
        or rule_facts.get("chief_complaint")
        or rule_facts.get("complaints")
        or (llm_succeeded and v2_response.primary_intent in {"symptom_report", "schedule_request"})
    ):
        return _short_turn_result(state, lang, "CONTEXT_RESET", context_reset=True, booking_for=None)

    # Lạc đề / vô nghĩa chen giữa cuộc tư vấn ("tôi muốn đi chơi", "asdkjh"): KHÔNG tính là câu trả lời,
    # giữ nguyên triệu chứng/khoa/ATS/lượt thăm dò; respond hỏi lại đúng câu đang chờ.
    # Cổng cấp cứu đã chạy trước nên câu có dấu hiệu nguy hiểm không bao giờ tới đây.
    relevance = getattr(v2_response, "turn_relevance", "relevant") if llm_succeeded else "relevant"
    if not llm_succeeded:
        relevance = "gibberish" if is_gibberish(query) else ("off_topic" if looks_off_topic(query) else "relevant")
    has_turn_content = bool(
        booking_entities.get("is_booking_intent")
        or booking_entities.get("patient_phone")
        or booking_entities.get("preferred_date")
        or explicit_doctor
        or doctor_query
        or context_reset
        or rule_facts.get("chief_complaint")
        or rule_facts.get("complaints")
        or rule_facts.get("positive_facts")
        or rule_facts.get("duration_days") is not None
        or _proxy_answer(query, awaiting_field)
        or facility_answer
    )
    if relevance in {"off_topic", "gibberish"} and not has_turn_content:
        streak = int(state.get("off_topic_streak") or 0) + 1
        return {
            "analysis": f"Turn relevance: {relevance} (streak {streak}) | clinical episode preserved",
            "workflow_status": state.get("workflow_status") or "IDLE",
            "off_topic_streak": streak,
            "language": lang,
            "messages": list(state.get("messages") or []),
            "metadata": {
                "off_topic": relevance,
                "off_topic_streak": streak,
                "pending_question": state.get("pending_question"),
                "needs_more_probing": True,  # đi thẳng tới respond, không tìm bác sĩ/lịch
                "llm_invoked": True,
                "llm_succeeded": llm_succeeded,
                "quick_replies": [],
            },
        }

    if booking_for == "other":
        # Đặt hộ: KHÔNG lấy họ tên/SĐT/ngày sinh/giới tính của chủ tài khoản (state.patient_* cũng nạp từ
        # tài khoản mỗi lượt). Chỉ dùng điều người dùng nói về người khám; thiếu thì hỏi.
        proxy_intake = state.get("proxy_patient") or {}
        answer = _proxy_answer(query, awaiting_field)
        llm_name = getattr(v2_response.facts_delta, "patient_name", None) if llm_succeeded else None
        if llm_name and not name_supported_by_text(llm_name, query):
            llm_name = None
        patient_name = (
            booking_entities.get("patient_name")
            or answer.get("patient_name")
            or llm_name
            or proxy_intake.get("patient_name")
        )
        patient_phone = booking_entities.get("patient_phone") or proxy_intake.get("patient_phone")
        patient_dob = (
            booking_entities.get("date_of_birth") or answer.get("date_of_birth") or proxy_intake.get("date_of_birth")
        )
        patient_gender = booking_entities.get("gender") or proxy_intake.get("gender")
    else:
        patient_name = (
            booking_entities.get("patient_name")
            or (state.get("patient_profile") or {}).get("name")
            or getattr(v2_response.facts_delta, "patient_name", None)
            or state.get("patient_name")
            or intake_state.get("patient_name")
        )
        patient_phone = (
            booking_entities.get("patient_phone")
            or (state.get("patient_profile") or {}).get("phone")
            or state.get("patient_phone")
            or intake_state.get("patient_phone")
        )
        patient_dob = (
            booking_entities.get("date_of_birth")
            or (state.get("patient_profile") or {}).get("date_of_birth")
            or state.get("patient_dob")
            or intake_state.get("date_of_birth")
        )
        patient_gender = (
            booking_entities.get("gender")
            or (state.get("patient_profile") or {}).get("gender")
            or state.get("patient_gender")
            or intake_state.get("gender")
        )
    patient_email = state.get("patient_email") or intake_state.get("patient_email")
    facility_pref = (
        booking_entities.get("facility_preference")
        or state.get("facility_preference")
        or facility_pref
        or intake_state.get("facility_preference")
    )
    preferred_date = (
        booking_entities.get("preferred_date") or state.get("preferred_date") or intake_state.get("preferred_date")
    )
    preferred_period = (
        booking_entities.get("preferred_period")
        or state.get("preferred_period")
        or intake_state.get("preferred_period")
    )
    doctor_pref = (
        booking_entities.get("doctor_preference")
        or state.get("doctor_preference")
        or intake_state.get("doctor_preference")
        or ""
    )
    doctor_name = (
        booking_entities.get("doctor_name") or state.get("doctor_name") or intake_state.get("doctor_name") or ""
    )

    llm_facility_name = getattr(v2_response.action_args, "facility_name", None)
    if llm_facility_name and not booking_entities.get("facility_preference"):
        lower_fac = llm_facility_name.lower().strip()
        matched_fac = None
        for k in sorted(FACILITY_MAPPING.keys(), key=len, reverse=True):
            if k in lower_fac:
                matched_fac = FACILITY_MAPPING[k]
                break
        facility_pref = matched_fac or llm_facility_name

    llm_date_text = getattr(v2_response.action_args, "preferred_date_text", None)
    if llm_date_text and not preferred_date:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from src.medical_assistant.domain.booking_slot_service import parse_vietnamese_date

        vn_today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        parsed_dt = parse_vietnamese_date(llm_date_text, reference_date=vn_today)
        if parsed_dt:
            preferred_date = parsed_dt.isoformat()

    llm_period = getattr(v2_response.action_args, "preferred_period", None)
    if llm_period and llm_period != "null" and not booking_entities.get("preferred_period"):
        preferred_period = llm_period

    llm_phone = getattr(v2_response.facts_delta, "patient_phone", None)
    if llm_phone and not booking_entities.get("patient_phone"):
        patient_phone = llm_phone

    is_package_inquiry = bool(booking_entities.get("is_package_inquiry"))
    is_booking_intent = bool(
        booking_entities.get("is_booking_intent")
        or is_package_inquiry
        or bool(llm_facility_name or llm_date_text)
        or (
            intent_check
            and intent_check.get("intent") in {"HOLD_BOOKING", "BOOKING_CONTACT_REQUEST", "FACILITY_BOOKING_START"}
        )
    )

    is_describe_more = bool(intent_check and intent_check.get("intent") == "DESCRIBE_MORE_SYMPTOMS")
    is_generic_visit = bool(intent_check and intent_check.get("intent") == "VISIT_PURPOSE_CLARIFICATION")
    is_probing_answer = bool(
        state.get("workflow_status") == "PROBING_IN_PROGRESS"
        and active_category
        and intent_check is None
        and response_subject != "other"
        and v2_response.primary_intent != "out_of_scope"
    )
    if (
        query
        and query not in collected_details
        and not is_describe_more
        and not is_generic_visit
        and (is_self_clinical_turn or is_probing_answer)
    ):
        collected_details.append(query)
    if len(collected_details) > MAX_DETAILS_HISTORY:
        collected_details = collected_details[-MAX_DETAILS_HISTORY:]

    triage_service = get_triage_service()
    combined_symptoms_text = " ".join(collected_details)
    triage_result = triage_service.evaluate_symptoms(combined_symptoms_text, language=lang)
    triage_result = triage_service.resolve_multi_symptom(triage_result, clinical_facts, language=lang)
    current_query_triage = triage_service.evaluate_symptoms(query, language=lang)
    # Lưới an toàn thứ hai: LLM chỉ được NÂNG lên cấp cứu khi luật bỏ sót (phương ngữ, cách kể lạ), có trích dẫn thật.
    if not triage_result.is_emergency and llm_succeeded:
        from src.medical_assistant.domain.llm_safety_escalation import llm_emergency_escalation

        recent_user = [m.get("content") or "" for m in state.get("messages") or [] if m.get("role") == "user"][-2:]
        escalation = llm_emergency_escalation(v2_response, query, [*recent_user, *collected_details], lang)
        if escalation:
            logger.warning("LLM_SAFETY_ESCALATION: %s", escalation["triggered_rule_ids"])
            triage_result = triage_result.model_copy(update=escalation)

    def serialize_candidate(candidate):
        return {
            "code": candidate.code,
            "name": candidate.name,
            "score": candidate.score,
            "ats_level": candidate.ats_level,
            "evidence": candidate.evidence,
            "missing_information": candidate.missing_information,
            "source": candidate.source,
            "routing_confidence": candidate.routing_confidence,
            "evidence_strength": candidate.evidence_strength,
            "has_independent_evidence": candidate.has_independent_evidence,
            "publicly_recommended": candidate.publicly_recommended,
            "suppression_reason": candidate.suppression_reason,
        }

    routing_candidates = [serialize_candidate(candidate) for candidate in triage_result.candidate_specialties]
    candidate_specialties = [serialize_candidate(candidate) for candidate in triage_result.recommended_specialties]
    if not candidate_specialties and routing_candidates:
        candidate_specialties = routing_candidates

    # ACTION SPACE PRUNING TRÊN KẾT QUẢ TRIAGE
    if state.get("pruned_departments"):
        pruned_depts_lower = {d.lower() for d in state["pruned_departments"]}
        candidate_specialties = [
            cs
            for cs in candidate_specialties
            if cs.get("name", "").lower() not in pruned_depts_lower
            and cs.get("code", "").lower() not in pruned_depts_lower
        ]
        if triage_result.recommended_specialties:
            filtered_recs = [
                rec
                for rec in triage_result.recommended_specialties
                if rec.name.lower() not in pruned_depts_lower and rec.code.lower() not in pruned_depts_lower
            ]
            if filtered_recs:
                triage_result.recommended_specialties = filtered_recs

    # Khớp MƠ HỒ trên văn bản gộp các lượt: không tự thành cấp cứu đầy đủ. Đã giải quyết trong lượt này (người dùng
    # nói "Không phải" / LLM khôi phục dấu thấy không cấp cứu) → khám trong ngày (ATS 3, không đẩy bàn điều phối);
    # chưa giải quyết → hỏi xác nhận như cổng cấp cứu.
    if triage_result.is_emergency and triage_result.match_confidence == "ambiguous":
        if not ambiguity_resolved:
            return _confirm_state(triage_result, query, lang, state, asks=1)
        triage_result = triage_result.model_copy(
            update={
                "is_emergency": False,
                "ats_level": ATSLevel.LEVEL_3_URGENT,
                "urgency_tier": UrgencyTier.SAME_DAY,
                "max_booking_days": 1,
                "care_setting": "URGENT_CLINICAL_ASSESSMENT",
            }
        )
    is_emergency = triage_result.is_emergency
    if is_emergency:
        return {
            "analysis": f"ATS Level: {triage_result.ats_level.value} (EMERGENCY_BLOCK) | Chuyên khoa: Cấp cứu | Cờ đỏ: {triage_result.triggered_red_flags} [Lang: {lang.upper()}]",
            "is_emergency": True,
            "emergency_warning": triage_result.patient_guidance,
            "ats_level": triage_result.ats_level.value,
            "urgency_tier": "EMERGENCY_BLOCK",
            "max_booking_days": 0,
            "suggested_department_name": "Cấp cứu",
            "workflow_status": "EMERGENCY",
            "probing_turn": current_turn,
            "collected_details": collected_details,
            "language": lang,
            "metadata": {
                "patient_guidance": triage_result.patient_guidance,
                "needs_more_probing": False,
                "tokens_saved": False,
                "v2_draft_response": v2_response.draft_response,
            },
        }

    from src.medical_assistant.domain.action_validator import has_clinical_evidence

    has_explicit_booking_request = bool(booking_entities.get("is_booking_intent") or is_booking_intent)

    suggested_dept_code = (
        triage_result.suggested_specialty
        if triage_result.ats_level.value < current_query_triage.ats_level.value
        else department_query
    )
    # Bác sĩ cụ thể người dùng chỉ định luôn thắng khoa đang nhớ từ ngữ cảnh cũ.
    if booking_entities.get("specialty_preference") and (
        has_explicit_booking_request or not current_dept or explicit_doctor
    ):
        suggested_dept_code = booking_entities["specialty_preference"]
        current_dept = booking_entities["specialty_preference"]
    if not suggested_dept_code and triage_result.recommended_specialties:
        spec_candidates = [
            s.code
            for s in triage_result.recommended_specialties
            if s.code not in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
        ]
        if spec_candidates:
            suggested_dept_code = spec_candidates[0]
    if (
        not suggested_dept_code
        and triage_result.suggested_specialty
        and triage_result.suggested_specialty not in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
    ):
        suggested_dept_code = triage_result.suggested_specialty
    if not suggested_dept_code and rule_facts.get("chief_complaint"):
        suggested_dept_code = current_query_triage.suggested_specialty
    # LLM đang hỏi lại mục đích khám thì danh sách khoa nó kèm theo chỉ là ví dụ (["TONG_QUAT", "TIM_MACH", …]),
    # không phải chẩn đoán hướng khám: lấy phần tử đầu từng gán nhầm Tim mạch cho "tôi muốn đi khám bệnh ở Hà Nội".
    llm_is_clarifying = v2_response.primary_intent == "clarify_visit_purpose" or bool(
        getattr(v2_response, "needs_clarification", False)
    )
    if not suggested_dept_code and v2_response.candidate_specialties and not llm_is_clarifying:
        v2_spec_candidates = [
            s.specialty_key
            for s in v2_response.candidate_specialties
            if s.specialty_key not in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
        ]
        if v2_spec_candidates:
            suggested_dept_code = v2_spec_candidates[0]
    # Đặt lịch đích danh bác sĩ mà chưa có chuyên khoa: lấy chuyên khoa thật của bác sĩ đó từ dữ liệu.
    _general_codes = {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
    if (
        booking_entities.get("doctor_preference")
        and not explicit_doctor  # đã tra DB ở trên
        and (not suggested_dept_code or suggested_dept_code in _general_codes)
        and not (current_dept and current_dept not in _general_codes)
    ):
        try:
            from src.medical_assistant.agent.tools.doctor_tools import search_doctors

            found = await asyncio.to_thread(
                search_doctors.invoke, {"name": booking_entities["doctor_preference"], "limit": 1}
            )
            doc_specs = ((found or {}).get("doctors") or [{}])[0].get("specialties") or []
            if doc_specs:
                suggested_dept_code = doc_specs[0]
                current_dept = doc_specs[0]
        except Exception as exc:
            logger.warning("Doctor specialty lookup failed: %s", exc)
    # Hướng khám DỰ KIẾN: ứng viên top-1 bị loại chỉ vì điểm thấp (below_primary_threshold) vẫn tốt hơn
    # việc rơi về "Sức khỏe tổng quát". Không áp dụng khi đã có khoa hiện tại hoặc ca khẩn cấp.
    tentative_routing = False
    _general_codes = {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
    if (not suggested_dept_code or suggested_dept_code in _general_codes) and not (
        current_dept and current_dept not in _general_codes
    ):
        for cand in triage_result.candidate_specialties[:1]:
            if cand.suppression_reason == "below_primary_threshold" and cand.code not in _general_codes:
                suggested_dept_code = cand.code
                tentative_routing = True
    if not suggested_dept_code or suggested_dept_code in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}:
        if current_dept and current_dept not in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}:
            suggested_dept_code = current_dept
        else:
            suggested_dept_code = suggested_dept_code or triage_result.suggested_specialty

    probing_service = get_probing_service()
    probing_by_complaint = probing_service.sync_probing_state(clinical_facts, probing_by_complaint)
    active_categories = probing_service.active_categories(probing_by_complaint)
    if active_categories:
        active_category = active_categories[0]

    should_ask_multi = bool(
        triage_result.needs_multi_symptom_clarification
        and current_turn < 4
        and probing_service.should_ask_multi_question(probing_by_complaint)
    )

    # RESOLVE ACTION: Bảng ưu tiên tập trung duy nhất
    action, action_reason, extra_args = resolve_action(
        intent_check=intent_check,
        booking_entities=booking_entities,
        v2_response=v2_response,
        triage_result=triage_result,
        clinical_facts=clinical_facts,
        rule_facts=rule_facts,
        current_turn=current_turn,
        active_category=active_category,
        should_ask_multi=should_ask_multi,
        is_emergency=is_emergency,
        is_describe_more=is_describe_more,
        has_explicit_booking_request=has_explicit_booking_request,
        query=query,
        state=state,
    )

    # Người dùng chỉ định một bác sĩ cụ thể để khám → đi luồng đặt lịch với bác sĩ đó (hỏi liên hệ / chốt phiếu),
    # không in lại lịch của khoa cũ. Ca cấp cứu và kiểm tra an toàn vẫn được ưu tiên.
    if (
        explicit_doctor
        and not is_emergency
        and (booking_entities.get("is_booking_intent") or booking_for == "other" or picked_doctor)
        and action in {"search_available_slot", "suggest_specialty", "ask_clarifying_question", "clarify_visit_purpose"}
    ):
        action, action_reason = "confirm_booking_conversationally", "Người dùng chỉ định bác sĩ cụ thể để đặt lịch"

    # Đồng bộ các tham số từ extra_args (từ VIEW_SCHEDULE, DEPARTMENT_INFO, FACILITY_*,...)
    if extra_args.get("requested_days"):
        v2_response.action_args.requested_days = extra_args["requested_days"]
    if extra_args.get("preferred_period"):
        v2_response.action_args.preferred_period = extra_args["preferred_period"]
    if extra_args.get("department"):
        suggested_dept_code = extra_args["department"]
        current_dept = extra_args["department"]
        v2_response.action_args.specialty_key = extra_args["department"]
    if extra_args.get("department_query"):
        v2_response.action_args.department_key = extra_args["department_query"]
        department_query = extra_args["department_query"]
    if "comparison_requested" in extra_args:
        v2_response.action_args.comparison_requested = extra_args["comparison_requested"]
        comparison_requested = extra_args["comparison_requested"]
    if extra_args.get("facility_name"):
        v2_response.action_args.facility_name = extra_args["facility_name"]
    if extra_args.get("facility_id"):
        v2_response.action_args.facility_id = extra_args["facility_id"]

    # Khôi phục mẫu phản hồi cho DESCRIBE_MORE_SYMPTOMS nếu cần
    if (intent_check or {}).get("intent") == "DESCRIBE_MORE_SYMPTOMS":
        if lang == "vi":
            v2_response.draft_response = "Dạ, bác hãy chia sẻ rõ hơn về triệu chứng hoặc cảm giác khó chịu/đau đang gặp, bắt đầu từ khi nào và mức độ hiện tại ạ?"
        else:
            v2_response.draft_response = (
                "Please describe the symptom or discomfort, when it began, and how severe it is now."
            )

    # HOOK 4: before_tool_execution (Validate action & enforce pruned departments)
    action, suggested_dept_code = middleware.execute_hook_4_before_tool(
        action=action,
        clinical_facts=clinical_facts,
        v2_response=v2_response,
        allowed_actions=allowed_actions,
        suggested_dept_code=suggested_dept_code,
        recommended_specialties=triage_result.recommended_specialties,
        pruned_departments=state.get("pruned_departments"),
        current_dept=current_dept,
    )

    # Hỏi nơi khám trước khi tra lịch (khu vực → cơ sở), mỗi lượt một câu. Cấp cứu không đi qua đây.
    facility_region = state.get("facility_region")
    facility_choice_skipped = bool(state.get("facility_choice_skipped"))
    choice_allowed = not triage_result.is_emergency and action not in SAFETY_ACTIONS
    if state.get("workflow_status") == "FACILITY_CHOICE_REQUIRED" and choice_allowed:
        answered_region = detect_facility_region(query)
        facility_region = answered_region or facility_region
        if facility_pref or wants_any_facility(query):
            facility_choice_skipped = not facility_pref
            action = "search_available_slot"
        elif answered_region:
            region_facilities = FACILITIES_BY_REGION[answered_region]
            if len(region_facilities) == 1:  # TP.HCM chỉ có Central Park → chọn luôn
                facility_pref = FACILITY_MAPPING[region_facilities[0][0].lower()]
                action = "search_available_slot"
            else:
                action = "ask_facility_choice"
    if (
        action == "search_available_slot"
        and not facility_pref
        and not facility_choice_skipped
        and not triage_result.is_emergency
        # Hỏi thông tin bác sĩ ("cho tôi xin thông tin các bác sĩ trong khoa"): trả lời luôn, không chặn hỏi nơi khám.
        and not booking_entities.get("is_doctor_inquiry")
        and not re.search(r"\b(?:thong tin|danh sach|gioi thieu|cac|nhung)\b.{0,20}\bbac si\b", remove_accents(query))
    ):
        action = "ask_facility_choice"

    # Đã chọn cơ sở và hiện danh sách bác sĩ có lịch trống → chọn bác sĩ → chọn giờ → giữ chỗ (mỗi lượt một câu).
    chosen_doctor = state.get("chosen_doctor")
    chosen_slot = state.get("chosen_slot")
    listed_doctors = state.get("last_listed_doctors") or []
    previous_status = state.get("workflow_status")

    def pick_doctor(doctor: dict[str, Any] | None) -> str:
        """Chọn (hoặc đổi) bác sĩ: bỏ giờ đã chọn trước đó; bác sĩ không còn giờ trống → điều phối viên xếp giờ."""
        nonlocal chosen_doctor, chosen_slot
        chosen_doctor, chosen_slot = doctor, None
        if doctor and not verified_slots([doctor]):
            return "confirm_booking_conversationally"
        return "ask_slot_choice"

    # Ô trên lưới lịch 7 ngày ("14:00 chiều 17/10 · Nguyễn Văn Thái") chọn luôn cả bác sĩ lẫn giờ → giữ chỗ ngay.
    grid_pick = (
        match_slot(query, listed_doctors)
        if previous_status == "TRIAGED_READY_FOR_BOOKING" and listed_doctors and choice_allowed
        else None
    )
    if grid_pick:
        chosen_doctor, chosen_slot = grid_pick
        extra_args["slot_id"] = chosen_slot["schedule_id"]
        preferred_date, preferred_period = slot_date_period(chosen_slot)
        action = "hold_slot"
    elif listed_doctors and choice_allowed and verified_slots(listed_doctors):
        if previous_status == "TRIAGED_READY_FOR_BOOKING" and (picked_doctor or wants_any_facility(query)):
            action = pick_doctor(picked_doctor)  # None = "bác sĩ nào cũng được"
        elif previous_status == "SLOT_CHOICE_REQUIRED":
            slot_match = match_slot(query, listed_doctors, chosen_doctor)
            if slot_match:
                chosen_doctor, chosen_slot = slot_match
                extra_args["slot_id"] = chosen_slot["schedule_id"]
                preferred_date, preferred_period = slot_date_period(chosen_slot)
                action = "hold_slot"
            elif picked_doctor:  # đổi ý chọn bác sĩ khác
                action = pick_doctor(picked_doctor)
            elif wants_coordinator_scheduling(query):
                chosen_slot = None
                action = "confirm_booking_conversationally"
    if action == "search_available_slot":  # tra lịch mới → danh sách mới, bỏ lựa chọn cũ
        chosen_doctor = chosen_slot = None
    if chosen_doctor:
        doctor_pref = chosen_doctor["full_name"]
        doctor_name = f"BS. {chosen_doctor['full_name']}"

    if (
        (not suggested_dept_code or suggested_dept_code in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"})
        and current_dept
        and current_dept not in {"Sức khỏe tổng quát", "General Health", "TONG_QUAT"}
    ):
        suggested_dept_code = current_dept

    # BẢO TOÀN QUYỀN PHỦ QUYẾT AN TOÀN LÂM SÀNG: HEADACHE_WITH_VISUAL_CHANGE luôn ghi đè sau hook 4
    if "HEADACHE_WITH_VISUAL_CHANGE" in triage_result.triggered_rule_ids:
        action = "request_safety_review"

    if action == "request_safety_review":
        safety_update = {
            "max_booking_days": 0,
            "disposition": "SAFETY_REVIEW",
            "acuity_status": "DETERMINED" if triage_result.triggered_rule_ids else "PROVISIONAL",
        }
        if triage_result.ats_level.value > ATSLevel.LEVEL_3_URGENT.value:
            has_explicit_clinical_evidence = bool(
                clinical_facts.get("active_complaint_codes") or clinical_facts.get("positive_facts")
            )
            if has_explicit_clinical_evidence:
                safety_update.update(
                    {
                        "ats_level": ATSLevel.LEVEL_3_URGENT,
                        "urgency_tier": UrgencyTier.SAME_DAY,
                        "care_setting": "URGENT_CLINICAL_ASSESSMENT",
                        "acuity_status": "PROVISIONAL",
                    }
                )
        triage_result = triage_result.model_copy(update=safety_update)

    workflow_status = "TRIAGED_AWAITING_SCHEDULE"
    needs_more_probing = False
    next_question = None
    quick_replies = v2_response.quick_replies
    new_turn = current_turn
    new_category = active_category
    detected_tree = probing_service.find_probing_tree(query)
    if detected_tree and not active_category:
        new_category = detected_tree.category_key

    if action == "request_safety_review":
        workflow_status = "SAFETY_REVIEW"
    elif action == "clarify_visit_purpose":
        workflow_status = "VISIT_PURPOSE_CLARIFICATION"
    elif action == "ask_clarifying_question":
        probing_result = None
        # Cùng điều kiện với resolve_action: đã có triệu chứng cụ thể ("mệt mỏi") thì hỏi tiếp triệu chứng đó.
        vague_prompt = (
            (intent_check or {}).get("intent") == "VAGUE_COMPLAINT"
            and not rule_facts.get("chief_complaint")
            and not rule_facts.get("positive_facts")
        )
        if vague_prompt:
            # Không tăng lượt probing: lượt sau người dùng mới nêu triệu chứng thật.
            next_question, quick_replies = get_guardrail_service().get_vague_complaint_prompt(
                intent_check.get("kind", "general"), lang
            )
            workflow_status = "PROBING_IN_PROGRESS"
            needs_more_probing = True
        elif should_ask_multi:
            next_question = triage_result.clarification_question
            complaint_labels = {
                "headache": ("Đau đầu", "Headache"),
                "abdominal_pain": ("Đau bụng", "Abdominal pain"),
                "constipation": ("Táo bón", "Constipation"),
                "sore_throat": ("Đau họng", "Sore throat"),
                "chest_pain": ("Đau ngực", "Chest pain"),
                "shortness_of_breath": ("Khó thở", "Shortness of breath"),
                "cough": ("Ho", "Cough"),
                "back_pain": ("Đau lưng", "Back pain"),
                "joint_pain": ("Đau khớp", "Joint pain"),
            }
            top_complaints = []
            for candidate in triage_result.candidate_specialties[:2]:
                complaint_code = next((value for value in candidate.evidence if value in complaint_labels), None)
                if complaint_code:
                    top_complaints.append(complaint_labels[complaint_code][0 if lang == "vi" else 1])
            quick_replies = (
                [f"{name} là chính" for name in top_complaints]
                + ["Các triệu chứng tương đương", "Có dấu hiệu nặng lên"]
                if lang == "vi"
                else [f"{name} is the main concern" for name in top_complaints]
                + ["Symptoms are similar", "Symptoms are worsening"]
            )
            active_codes = list(clinical_facts.get("active_complaint_codes") or [])
            probing_by_complaint = probing_service.mark_multi_question_asked(probing_by_complaint, active_codes)
            workflow_status = "PROBING_IN_PROGRESS"
            needs_more_probing = True
            new_turn += 1
        else:
            probing_result = probing_service.get_next_question(
                query,
                current_turn,
                active_category=new_category,
                language=lang,
                clinical_facts=clinical_facts,
            )
        if probing_result:
            next_question, quick_replies, new_category = probing_result
            category_codes = [
                code
                for code, item in probing_by_complaint.items()
                if item.get("status") == "active" and item.get("category") == new_category
            ]
            probing_by_complaint = probing_service.mark_multi_question_asked(
                probing_by_complaint,
                category_codes,
            )
            workflow_status = "PROBING_IN_PROGRESS"
            needs_more_probing = True
            new_turn += 1
        elif should_ask_multi or vague_prompt:
            pass
        elif current_turn >= 2 or active_category:
            workflow_status = "TRIAGED_AWAITING_SCHEDULE"
            quick_replies = v2_response.quick_replies
        else:
            workflow_status = "PROBING_IN_PROGRESS"
            needs_more_probing = True
            # Bản nháp của clarify_visit_purpose là menu mục đích khám; LLM lỗi/thiếu thì bản nháp rỗng.
            next_question = (
                v2_response.draft_response if v2_response.proposed_action != "clarify_visit_purpose" else ""
            ) or ("Dạ, triệu chứng này bắt đầu từ khi nào ạ?" if lang == "vi" else "When did this symptom start?")
            new_turn += 1
    elif action in {"ask_facility_choice", "search_available_slot"}:
        # Hỏi nơi khám cũng giữ yêu cầu tra lịch ("2 ngày tới", "buổi sáng") để lượt chọn cơ sở dùng tiếp.
        workflow_status = "FACILITY_CHOICE_REQUIRED" if action == "ask_facility_choice" else "TRIAGED_READY_FOR_BOOKING"
        if v2_response.action_args.requested_days:
            current_max_days = v2_response.action_args.requested_days
        if v2_response.action_args.preferred_period != "null":
            time_pref = v2_response.action_args.preferred_period
        if v2_response.action_args.facility_id:
            facility_pref = v2_response.action_args.facility_id
    elif action == "confirm_booking_conversationally":
        workflow_status = "CONFIRM_BOOKING_CONVERSATIONALLY"
    elif action == "ask_slot_choice":
        workflow_status = "SLOT_CHOICE_REQUIRED"
    elif action == "hold_slot":
        workflow_status = "BOOKING_CONTACT_REQUIRED"
    elif action == "answer_faq":
        workflow_status = "FAQ_ANSWERED"
    elif action == "show_department_info":
        workflow_status = "DEPARTMENT_INFO"
    elif action == "show_facility_info":
        workflow_status = "FACILITY_INFO"
    elif action == "show_facility_doctors":
        workflow_status = "FACILITY_DOCTORS"
    elif action == "start_facility_booking":
        workflow_status = "FACILITY_BOOKING_START"
    elif action == "decline_medication_request":
        workflow_status = "GUARDRAIL_MEDICATION"
    elif action == "respond_to_diagnosis_request":
        workflow_status = "GUARDRAIL_DIAGNOSIS"
    elif action == "request_human_help":
        workflow_status = "BOOKING_CONTACT_REQUIRED" if suggested_dept_code else "HUMAN_HELP_REQUESTED"
    elif action == "acknowledge_language_change":
        workflow_status = "LANGUAGE_CHANGED"
    elif action == "out_of_scope_decline":
        workflow_status = "OUT_OF_SCOPE"
    elif action == "suggest_specialty":
        workflow_status = "TRIAGED_AWAITING_SCHEDULE"
    else:
        workflow_status = "TRIAGED_AWAITING_SCHEDULE"

    canonical_dept = canonicalize_specialty_code(suggested_dept_code)
    department_display = get_specialty_display_name(canonical_dept, "vi")

    available_slots = state.get("available_slots") or []
    slot_data_unavailable = False
    slot_data_unavailable_reason = None
    slots_queried_in_analyze = False
    facility_fallback = None
    if action == "search_available_slot":
        from src.medical_assistant.domain.doctor_schedule_service import fetch_available_doctors_slots_cached

        # "Cơ sở nào ở Hà Nội cũng được": tra lịch chỉ lọc được theo một cơ sở → tra lần lượt các cơ sở trong khu vực.
        facility_queries = (
            [FACILITY_MAPPING[name.lower()] for name, _ in FACILITIES_BY_REGION[facility_region]]
            if facility_region in FACILITIES_BY_REGION and not facility_pref
            else [facility_pref]
        )

        async def fetch_at(queries: list[str | None]) -> list[tuple[list, bool, str | None]]:
            return await asyncio.gather(
                *(
                    fetch_available_doctors_slots_cached(
                        state=state,
                        specialty_name=get_specialty_display_name(canonical_dept, "vi"),
                        limit_doctors=3,
                        # Đủ 2 ca/ngày × 7 ngày cho lưới lịch; phần chữ chỉ ghi vài ca đầu (respond_node).
                        slots_per_doctor=14,
                        requested_days=current_max_days,
                        preferred_period=time_pref,
                        facility_id=facility_query,
                    )
                    for facility_query in queries
                )
            )

        results = await fetch_at(facility_queries)
        doctors = [doctor for found, _, _ in results for doctor in found][:3]  # giữ thứ tự cơ sở
        # Cơ sở đã chọn không có bác sĩ chuyên khoa này còn lịch (vd. Riverside chưa có Tai Mũi Họng)
        # → tra các cơ sở cùng khu vực, báo rõ là cơ sở khác thay vì chỉ trả lời "chưa tìm thấy lịch".
        if not doctors and facility_pref and len(facility_queries) == 1:
            alternatives = nearby_facilities(facility_pref)
            if alternatives:
                alt_results = await fetch_at(alternatives)
                picked = [(name, doctor) for name, (found, _, _) in zip(alternatives, alt_results) for doctor in found][
                    :3
                ]
                doctors = [doctor for _, doctor in picked]
                if doctors:
                    results = alt_results
                    # Tên cơ sở đã tra (không lấy `workplace`: có hồ sơ ghi khoa, vd. "Khoa Nhi - Sơ sinh - ...").
                    facility_fallback = {"requested": facility_pref, "found": list(dict.fromkeys(n for n, _ in picked))}
        if len(results) == 1:
            _, slot_data_unavailable, slot_data_unavailable_reason = results[0]
        else:
            # Nhiều cơ sở: chỉ báo thiếu dữ liệu khi mọi cơ sở đều lỗi và không có bác sĩ nào.
            failed = [reason for _, unavailable, reason in results if unavailable]
            slot_data_unavailable = bool(failed) and len(failed) == len(results) and not doctors
            slot_data_unavailable_reason = failed[0] if slot_data_unavailable else None
        available_slots = doctors
        slots_queried_in_analyze = True

    is_non_clinical = workflow_status in {
        "DEPARTMENT_INFO",
        "FACILITY_INFO",
        "FACILITY_DOCTORS",
        "FACILITY_BOOKING_START",
        "VISIT_PURPOSE_CLARIFICATION",
        "FAQ_ANSWERED",
        "SECURITY_BLOCKED",
        "SOCIAL_REDIRECT",
        "THIRD_PARTY_HEALTH_GUIDANCE",
        "OUT_OF_SCOPE",
        "LANGUAGE_CHANGED",
    }

    if is_non_clinical:
        analysis_parts = [
            f"Deterministic Action: {action}",
            f"Status: {workflow_status}",
        ]
        if intent_check:
            analysis_parts.append(f"Intent: {intent_check.get('intent')}")
            if intent_check.get("region_filter"):
                analysis_parts.append(f"Khu vực: {intent_check.get('region_filter')}")
            if intent_check.get("district_filter"):
                analysis_parts.append(f"Quận/Huyện: {intent_check.get('district_filter')}")
            if intent_check.get("facility_name_query"):
                analysis_parts.append(f"Cơ sở: {intent_check.get('facility_name_query')}")
            if intent_check.get("matched_pattern"):
                analysis_parts.append(f"Quy tắc khớp: '{intent_check.get('matched_pattern')}'")
        if department_display and workflow_status == "DEPARTMENT_INFO":
            analysis_parts.append(f"Chuyên khoa: {department_display}")
        analysis_parts.append(f"Lang: {lang.upper()}")
        analysis = " | ".join(analysis_parts)
    else:
        analysis = (
            f"Hybrid V2 Action: {action} ({action_reason}) | "
            f"ATS Level: {triage_result.ats_level.value} ({triage_result.urgency_tier.value}) | "
            f"Chuyên khoa: {canonical_dept} | "
            f"Lang: {lang.upper()}"
        )

    from src.medical_assistant.domain.compaction_service import get_compaction_service

    conversation_messages = list(state.get("messages") or [])
    compaction_res = get_compaction_service().compact_conversation(conversation_messages, state, recent_window_size=4)
    compacted_messages = compaction_res["recent_messages"]
    durable_soap_note = compaction_res["durable_soap_note"]

    has_evidence = bool(
        is_emergency
        or has_clinical_evidence(clinical_facts, v2_response)
        or rule_facts.get("chief_complaint")
        or rule_facts.get("complaints")
        or clinical_facts.get("chief_complaint")
        or clinical_facts.get("positive_facts")
        or (collected_details and len(collected_details) > 0 and is_self_clinical_turn)
    )
    is_department_focused_action = bool(
        workflow_status
        in {
            "DEPARTMENT_INFO",
            "FACILITY_DOCTORS",
            "FACILITY_BOOKING_START",
            "TRIAGED_READY_FOR_BOOKING",
            "CONFIRM_BOOKING_CONVERSATIONALLY",
            "BOOKING_CONTACT_REQUIRED",
            "FACILITY_CHOICE_REQUIRED",
            "SLOT_CHOICE_REQUIRED",
        }
        or (action in {"search_available_slot", "confirm_booking_conversationally"})
    )

    return {
        "analysis": analysis,
        "durable_soap_note": durable_soap_note,
        "is_emergency": is_emergency,
        "emergency_warning": triage_result.patient_guidance if is_emergency else None,
        "ats_level": triage_result.ats_level.value if (has_evidence or is_emergency) else None,
        "urgency_tier": triage_result.urgency_tier.value if (has_evidence or is_emergency) else None,
        "max_booking_days": 0
        if workflow_status == "SAFETY_REVIEW"
        else (current_max_days if (has_evidence or is_department_focused_action) else None),
        "acuity_status": triage_result.acuity_status if (has_evidence or is_emergency) else "NOT_APPLICABLE",
        "disposition": triage_result.disposition if (has_evidence or is_emergency) else "CONVERSATIONAL",
        "suggested_department_code": canonical_dept
        if ((has_evidence or is_department_focused_action) and workflow_status != "VISIT_PURPOSE_CLARIFICATION")
        else None,
        "suggested_department_name": department_display
        if ((has_evidence or is_department_focused_action) and workflow_status != "VISIT_PURPOSE_CLARIFICATION")
        else None,
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "patient_dob": patient_dob,
        "patient_gender": patient_gender,
        "patient_email": patient_email,
        "facility_preference": facility_pref,
        "facility_region": facility_region,
        "facility_choice_skipped": facility_choice_skipped,
        "chosen_doctor": chosen_doctor,
        "chosen_slot": chosen_slot,
        # Danh sách bác sĩ vừa hiển thị kèm lịch trống: để lượt sau chọn "BS. X" / "bác sĩ thứ 2" / giờ khám.
        # Ghi cả khi rỗng: lần tra mới không ra ai thì "2" / "bác sĩ nào cũng được" không được chọn người của lần trước.
        **({"last_listed_doctors": available_slots} if slots_queried_in_analyze else {}),
        "preferred_date": preferred_date,
        "preferred_period": preferred_period,
        "doctor_preference": doctor_pref,
        "doctor_name": doctor_name,
        "booking_for": booking_for,
        "off_topic_streak": 0,
        # Thông tin người khám khi đặt hộ, giữ qua các lượt (state.patient_* bị nạp lại từ tài khoản mỗi lượt).
        "proxy_patient": {
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "date_of_birth": patient_dob,
            "gender": patient_gender,
        }
        if booking_for == "other"
        else {},
        **({"booking_intake": {}, "last_listed_doctors": []} if context_reset else {}),
        "is_authenticated": state.get("is_authenticated"),
        "workflow_status": workflow_status,
        "probing_turn": new_turn,
        "active_probing_category": new_category,
        "active_probing_categories": active_categories,
        "probing_by_complaint": probing_by_complaint,
        "collected_details": collected_details,
        "clinical_facts": clinical_facts,
        "available_slots": available_slots,
        "candidate_specialties": candidate_specialties,
        "routing_candidates": routing_candidates,
        "conflict_reason": triage_result.conflict_reason,
        "language": lang,
        "session_id": state.get("session_id"),
        "guest_token": state.get("guest_token"),
        "user_id": state.get("user_id"),
        "messages": compacted_messages,
        "enable_citation": state.get("enable_citation") if state.get("enable_citation") is not None else True,
        "metadata": {
            "needs_more_probing": needs_more_probing,
            "clarification_question": next_question,
            "quick_replies": quick_replies,
            "patient_guidance": triage_result.patient_guidance,
            "facility_preference": facility_pref,
            "time_preference": time_pref,
            "v2_draft_response": v2_response.draft_response,
            "slot_id": extra_args.get("slot_id") or v2_response.action_args.slot_id,
            "comparison_requested": comparison_requested or bool(v2_response.action_args.comparison_requested),
            "department_query": department_query,
            "intent_hint": extra_args.get("intent_hint") or (intent_check or {}).get("intent"),
            "describe_more_requested": bool(intent_check and intent_check.get("intent") == "DESCRIBE_MORE_SYMPTOMS"),
            "region_filter": (intent_check or {}).get("region_filter"),
            "district_filter": (intent_check or {}).get("district_filter"),
            "facility_name_query": (intent_check or {}).get("facility_name_query"),
            "schedule_lookup_requested": action == "search_available_slot",
            "facility_fallback": facility_fallback,
            "slots_fetched_in_turn": slots_queried_in_analyze,
            "data_unavailable": slot_data_unavailable or bool(state.get("metadata", {}).get("data_unavailable")),
            "data_unavailable_reason": slot_data_unavailable_reason
            or state.get("metadata", {}).get("data_unavailable_reason"),
            "is_booking_intent": is_booking_intent,
            "is_doctor_inquiry": bool(booking_entities.get("is_doctor_inquiry")),
            "is_booking_confirmation": bool(booking_entities.get("is_booking_confirmation")),
            "booking_entities_found": bool(
                booking_entities.get("patient_name")
                or booking_entities.get("patient_phone")
                or booking_entities.get("date_of_birth")
                or booking_entities.get("facility_preference")
                or booking_entities.get("preferred_date")
            ),
            "tokens_saved": skip_llm,
            "llm_invoked": not skip_llm,
            "llm_succeeded": llm_succeeded,
            "fallback_used": not llm_succeeded,
            "action": action,
            "action_reason": action_reason,
            "tentative_routing": tentative_routing,
            "candidate_specialties": candidate_specialties,
            "conflict_reason": triage_result.conflict_reason,
            "acuity_status": triage_result.acuity_status,
            "disposition": triage_result.disposition,
        },
    }
