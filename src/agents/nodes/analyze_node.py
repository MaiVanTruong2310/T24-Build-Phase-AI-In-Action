import asyncio
import re

from src.agents.nodes.helpers import extract_facility_inquiry
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.booking_slot_service import (
    extract_booking_entities,
)
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.disease_triage import ATSLevel, UrgencyTier
from src.medical_assistant.domain.hybrid_dialogue_service import get_hybrid_dialogue_service
from src.medical_assistant.domain.language_service import (
    canonicalize_specialty_code,
    detect_language,
    get_specialty_display_name,
)
from src.medical_assistant.domain.probing_service import get_probing_service
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service
from src.medical_assistant.domain.triage_service import get_triage_service

MAX_DETAILS_HISTORY = 4


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
        lang = detected_lang
    else:
        lang = current_lang or detected_lang

    current_turn = state.get("probing_turn") or 0
    active_category = state.get("active_probing_category")
    active_categories = list(
        state.get("active_probing_categories") or ([] if not active_category else [active_category])
    )
    probing_by_complaint = dict(state.get("probing_by_complaint") or {})
    collected_details = state.get("collected_details") or []
    current_dept = state.get("suggested_department_name")
    current_ats = state.get("ats_level") or 4
    current_urgency = state.get("urgency_tier") or "STANDARD"
    current_max_days = state.get("max_booking_days") or 7
    clinical_facts = state.get("clinical_facts") or {}

    facility_pref = state.get("metadata", {}).get("facility_preference")
    time_pref = state.get("metadata", {}).get("time_preference")

    security_check = get_security_guardrail_service().inspect_query(query, language=lang)
    if not security_check.is_safe:
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

    triage_service = get_triage_service()
    emergency_fast_check = triage_service.evaluate_symptoms(query, language=lang)
    if emergency_fast_check.is_emergency:
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
            "metadata": {
                "needs_more_probing": False,
                "patient_guidance": emergency_fast_check.patient_guidance,
                "triggered_red_flags": emergency_fast_check.triggered_red_flags,
                "triggered_rule_ids": emergency_fast_check.triggered_rule_ids,
                "quick_replies": ["Gọi cấp cứu 115 ngay", "Đến phòng Cấp cứu gần nhất"]
                if lang == "vi"
                else ["Call Emergency 115", "Go to Emergency Room"],
                "tokens_saved": True,
            },
        }

    cache_service = get_cache_service()

    from src.medical_assistant.domain.booking_slot_service import detect_appointment_query
    from src.medical_assistant.domain.guardrail_service import remove_accents

    is_app_query = detect_appointment_query(query)
    if is_app_query:
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
        id_pattern = (
            r"(?:ten|so dien thoai|sdt|dia chi|thong tin(?: ca nhan)?|ho so)\b.*?\b(?:cua (?:toi|minh)|my)\b|"
            r"(?:hien thi|xem|kiem tra)\b.*?\b(?:thong tin(?: ca nhan)?|ho so)\b.*?\b(?:cua (?:toi|minh))|"
            r"my (?:name|phone|address|profile|info|contact)"
        )
        is_identity_query = bool(re.search(id_pattern, identity_query))
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
    if cached is not None:
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

    # HYBRID DIALOGUE V2 INTEGRATION
    hybrid_service = get_hybrid_dialogue_service()
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

    # 6-HOOK AGENT MIDDLEWARE PIPELINE
    from src.medical_assistant.domain.middleware_pipeline import get_middleware_pipeline

    middleware = get_middleware_pipeline()

    # HOOK 2: before_model_call (Action Space Pruning)
    allowed_actions, candidate_specs = middleware.execute_hook_2_before_model(
        allowed_actions=allowed_actions,
        state=state,
    )

    last_assistant_question = state.get("metadata", {}).get("clarification_question")

    # HOOK 1: on_user_input (Security Audit & Intent Interception)
    intent_check, _ = middleware.execute_hook_1_user_input(
        query=query,
        state=state,
        current_dept=current_dept,
        language=lang,
    )
    if not intent_check or intent_check.get("intent") == "SELF_CARE_FOLLOWUP":
        fac_inquiry, fac_reg = extract_facility_inquiry(query)
        if fac_inquiry:
            intent_check = {
                "intent": "FACILITY_INFO",
                "matched_pattern": "smart_facility_extraction",
                "region_filter": fac_reg,
                "district_filter": None,
                "facility_name_query": None,
            }
    from src.medical_assistant.domain.guardrail_service import remove_accents

    normalized_query = remove_accents(query)
    if "khia" in normalized_query or "khia" in query.lower():
        intent_check = {"intent": "DEPARTMENT_INFO", "department_query": "TONG_QUAT"}
    elif current_dept and "kham o dau" in normalized_query:
        intent_check = {"intent": "SELF_CARE_FOLLOWUP"}
    elif "slot" in query.lower() and not state.get("selected_slot"):
        slot_match = re.search(r"slot\s+([a-z0-9-]+)", query.lower())
        intent_check = {"intent": "HOLD_BOOKING", "slot_id": slot_match.group(1) if slot_match else None}
    boundary_intent = (intent_check or {}).get("intent")
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
    # LLM-CENTRIC ARCHITECTURE: Luôn ưu tiên LLM làm bộ não tư duy và hiểu ngữ cảnh tự nhiên
    # Chỉ fallback khi API LLM gặp sự cố mạng hoặc quota
    v2_response, llm_succeeded = await hybrid_service.process_turn_async(
        text=query,
        state={**state, "language": lang},
        recent_turns=collected_details,
        last_assistant_question=last_assistant_question,
        allowed_actions=allowed_actions,
    )
    skip_llm = False

    # Safety Guardrails & Deterministic Intent Validation
    department_query = None
    comparison_requested = False
    if intent_check:
        intent_name = intent_check.get("intent")
        if intent_name == "MEDICATION_GUARDRAIL":
            v2_response.proposed_action = "decline_medication_request"
        elif intent_name == "DIAGNOSIS_GUARDRAIL":
            v2_response.proposed_action = "respond_to_diagnosis_request"
        elif intent_name == "DEPARTMENT_INFO":
            v2_response.proposed_action = "show_department_info"
            department_query = intent_check.get("department_query")
            comparison_requested = bool(intent_check.get("comparison_requested"))
            v2_response.action_args.department_key = department_query
            v2_response.action_args.comparison_requested = comparison_requested
        elif intent_name == "FACILITY_INFO":
            v2_response.proposed_action = "show_facility_info"
        elif intent_name == "FACILITY_DOCTORS":
            v2_response.proposed_action = "show_facility_doctors"
        elif intent_name == "FACILITY_BOOKING_START":
            v2_response.proposed_action = "start_facility_booking"
        elif intent_name == "HOLD_BOOKING":
            v2_response.proposed_action = "hold_slot"
            v2_response.action_args.slot_id = intent_check.get("slot_id")
        elif intent_name == "BOOKING_CONTACT_REQUEST":
            v2_response.proposed_action = "request_human_help"
        elif intent_name == "VISIT_PURPOSE_CLARIFICATION" and v2_response.proposed_action not in {
            "search_available_slot",
            "show_facility_info",
            "show_department_info",
        }:
            v2_response.proposed_action = "clarify_visit_purpose"
        elif intent_name == "DESCRIBE_MORE_SYMPTOMS":
            v2_response.proposed_action = "ask_clarifying_question"
            if lang == "vi":
                v2_response.draft_response = "Dạ, bác hãy chia sẻ rõ hơn về triệu chứng hoặc cảm giác khó chịu/đau đang gặp, bắt đầu từ khi nào và mức độ hiện tại ạ?"
            else:
                v2_response.draft_response = (
                    "Please describe the symptom or discomfort, when it began, and how severe it is now."
                )
        elif intent_name == "VIEW_SCHEDULE":
            v2_response.proposed_action = "search_available_slot"
            if intent_check.get("requested_days"):
                v2_response.action_args.requested_days = intent_check.get("requested_days")
            if intent_check.get("preferred_time"):
                v2_response.action_args.preferred_period = intent_check.get("preferred_time")
            if intent_check.get("department"):
                suggested_dept_code = intent_check.get("department")
                current_dept = intent_check.get("department")
                v2_response.action_args.specialty_key = intent_check.get("department")

    if v2_response.primary_intent == "schedule_request" and v2_response.proposed_action != "search_available_slot":
        v2_response.proposed_action = "search_available_slot"
    if v2_response.proposed_action == "search_available_slot" and v2_response.action_args.specialty_key:
        suggested_dept_code = v2_response.action_args.specialty_key
        current_dept = v2_response.action_args.specialty_key

    fact_service = get_clinical_fact_service()
    # Rules preserve explicit common facts even when the LLM omits a field;
    # the LLM layer adds conversational/semantic detail on top.
    conversation_turn = 1 + sum(1 for message in (state.get("messages") or []) if message.get("role") == "user")
    rule_facts = fact_service.extract(query, turn_index=conversation_turn)
    if (
        rule_facts.get("primary_complaint")
        and intent_check
        and intent_check.get("intent") in {"DIAGNOSIS_GUARDRAIL", "MEDICATION_GUARDRAIL"}
    ):
        rule_facts["primary_complaint_explicit"] = True
        rule_facts["primary_complaint_explicit_code"] = rule_facts["primary_complaint"]
    extracted_facts = hybrid_service.adapt_v2_to_v1(v2_response)
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
    intake_state = state.get("booking_intake") or (state.get("metadata") or {}).get("booking_intake") or {}
    patient_name = (
        booking_entities.get("patient_name")
        or (state.get("patient_profile") or {}).get("name")
        or v2_response.facts_delta.patient_name
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

    # Grounding LLM-extracted slots from v2_response (Dialogue State Tracking)
    llm_facility_name = getattr(v2_response.action_args, "facility_name", None)
    if llm_facility_name and not booking_entities.get("facility_preference"):
        from src.medical_assistant.domain.booking_slot_service import FACILITY_MAPPING

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

    combined_symptoms_text = " ".join(collected_details)
    triage_result = triage_service.evaluate_symptoms(combined_symptoms_text, language=lang)
    triage_result = triage_service.resolve_multi_symptom(triage_result, clinical_facts, language=lang)
    current_query_triage = triage_service.evaluate_symptoms(query, language=lang)

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

    # Validation against safety rules (Rule vs LLM)
    is_emergency = triage_result.is_emergency
    if is_emergency:
        return {
            "analysis": f"ATS Level: 1 (EMERGENCY_BLOCK) | Chuyên khoa: Cấp cứu | Cờ đỏ: {triage_result.triggered_red_flags} [Lang: {lang.upper()}]",
            "is_emergency": True,
            "emergency_warning": triage_result.patient_guidance,
            "ats_level": 1,
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

    # Action Validation via ActionValidator
    from src.medical_assistant.domain.action_validator import has_clinical_evidence

    action = v2_response.proposed_action
    if action == "clarify_visit_purpose" and (
        state.get("collected_details") or state.get("suggested_department_name") or rule_facts.get("chief_complaint")
    ):
        action = "ask_clarifying_question"
    suggested_dept_code = department_query
    if booking_entities.get("specialty_preference"):
        suggested_dept_code = booking_entities["specialty_preference"]
        current_dept = booking_entities["specialty_preference"]
    if not suggested_dept_code and triage_result.recommended_specialties:
        suggested_dept_code = triage_result.recommended_specialties[0].code
    if not suggested_dept_code and triage_result.candidate_specialties:
        suggested_dept_code = triage_result.candidate_specialties[0].code
    if (
        not suggested_dept_code
        and triage_result.suggested_specialty
        and triage_result.suggested_specialty not in {"Sức khỏe tổng quát", "General Health"}
    ):
        suggested_dept_code = triage_result.suggested_specialty
    if not suggested_dept_code and current_query_triage.suggested_specialty:
        suggested_dept_code = current_query_triage.suggested_specialty
    if not suggested_dept_code and v2_response.candidate_specialties:
        suggested_dept_code = v2_response.candidate_specialties[0].specialty_key
    if not suggested_dept_code:
        suggested_dept_code = current_dept or triage_result.suggested_specialty

    # Nếu người dùng hỏi/chọn bác sĩ hoặc xác nhận đặt lịch
    has_explicit_booking_request = bool(booking_entities.get("is_booking_intent") or is_booking_intent)
    if booking_entities.get("is_doctor_inquiry"):
        action = "search_available_slot"
    elif booking_entities.get("is_booking_confirmation") and not is_emergency:
        action = "confirm_booking_conversationally"
    elif has_explicit_booking_request:
        action = "search_available_slot"

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
    if action != "confirm_booking_conversationally" and (
        (is_describe_more and state.get("active_probing_category"))
        or (
            (
                getattr(v2_response, "needs_clarification", False)
                or v2_response.proposed_action == "clarify_visit_purpose"
            )
            and not (
                intent_check
                and intent_check.get("intent")
                in {"FACILITY_INFO", "FACILITY_DOCTORS", "DEPARTMENT_INFO", "VIEW_SCHEDULE"}
            )
        )
    ):
        action = "ask_clarifying_question" if state.get("active_probing_category") else "clarify_visit_purpose"
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
    if should_ask_multi:
        action = "ask_clarifying_question"
    # A model may jump straight to a specialty while duration/severity/red flags
    # are still unknown. Keep one bounded clinical clarification before routing.
    if (
        rule_facts.get("chief_complaint")
        and current_turn < 2
        and action == "suggest_specialty"
        and not triage_result.needs_multi_symptom_clarification
    ):
        if probing_service.find_probing_tree(query) or active_category:
            action = "ask_clarifying_question"

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
        if should_ask_multi:
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
        elif should_ask_multi:
            pass
        elif current_turn >= 2 or active_category:
            workflow_status = "TRIAGED_AWAITING_SCHEDULE"
            quick_replies = v2_response.quick_replies
        else:
            workflow_status = "PROBING_IN_PROGRESS"
            needs_more_probing = True
            next_question = v2_response.draft_response
            new_turn += 1
    elif action == "search_available_slot":
        workflow_status = "TRIAGED_READY_FOR_BOOKING"
        # Extract requested days/period
        if v2_response.action_args.requested_days:
            current_max_days = v2_response.action_args.requested_days
        if v2_response.action_args.preferred_period != "null":
            time_pref = v2_response.action_args.preferred_period
        if v2_response.action_args.facility_id:
            facility_pref = v2_response.action_args.facility_id
    elif action == "confirm_booking_conversationally":
        workflow_status = "CONFIRM_BOOKING_CONVERSATIONALLY"
    elif action == "hold_slot":
        # The public chat has no authenticated patient identity. A slot selection
        # therefore opens a contact intake instead of pretending to lock a slot.
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
    digestive_query = (
        "dau quan bung" in normalized_query
        or "o chua" in normalized_query
        or "bụng" in query.lower()
        or "ợ chua" in query.lower()
    )
    if digestive_query:
        canonical_dept = "TIEU_HOA"
    if canonical_dept == "TONG_QUAT" and triage_result.candidate_specialties:
        candidate_code = triage_result.candidate_specialties[0].code
        if candidate_code and canonicalize_specialty_code(candidate_code) != "TONG_QUAT":
            canonical_dept = canonicalize_specialty_code(candidate_code)
    department_display = get_specialty_display_name(canonical_dept, "vi")

    available_slots = state.get("available_slots") or []
    if action == "search_available_slot":
        from src.medical_assistant.domain.doctor_schedule_service import get_doctor_schedule_service

        doctor_service = get_doctor_schedule_service()
        doctors = await asyncio.to_thread(
            doctor_service.get_available_doctors_and_slots,
            specialty_name=get_specialty_display_name(canonical_dept, "vi"),
            limit_doctors=3,
            slots_per_doctor=2,
            requested_days=current_max_days,
            preferred_period=time_pref,
            facility_id=facility_pref,
        )
        available_slots = doctors

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
            f"Hybrid V2 Action: {action} | "
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
        or (canonical_dept != "TONG_QUAT" and canonical_dept is not None)
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
        }
        or (action in {"search_available_slot", "confirm_booking_conversationally"})
    )
    if digestive_query and workflow_status == "VISIT_PURPOSE_CLARIFICATION":
        workflow_status = "TRIAGED_AWAITING_SCHEDULE"

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
        "preferred_date": preferred_date,
        "preferred_period": preferred_period,
        "doctor_preference": doctor_pref,
        "doctor_name": doctor_name,
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
            "slot_id": v2_response.action_args.slot_id,
            "comparison_requested": comparison_requested or bool(v2_response.action_args.comparison_requested),
            "department_query": department_query,
            "describe_more_requested": bool(intent_check and intent_check.get("intent") == "DESCRIBE_MORE_SYMPTOMS"),
            "region_filter": (intent_check or {}).get("region_filter"),
            "district_filter": (intent_check or {}).get("district_filter"),
            "facility_name_query": (intent_check or {}).get("facility_name_query"),
            "schedule_lookup_requested": action == "search_available_slot",
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
            "candidate_specialties": candidate_specialties,
            "conflict_reason": triage_result.conflict_reason,
            "acuity_status": triage_result.acuity_status,
            "disposition": triage_result.disposition,
        },
    }
