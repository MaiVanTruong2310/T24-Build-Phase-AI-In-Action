import asyncio
import re

from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.booking_slot_service import (
    build_booking_guidance_text,
    evaluate_missing_fields,
    extract_booking_entities,
)
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.disease_triage import ATSLevel, UrgencyTier
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.hybrid_dialogue_service import get_hybrid_dialogue_service
from src.medical_assistant.domain.language_service import (
    detect_language,
    get_medical_disclaimer,
    get_specialty_display_name,
)
from src.medical_assistant.domain.probing_service import get_probing_service
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service
from src.medical_assistant.domain.triage_service import get_triage_service

MAX_DETAILS_HISTORY = 4

def extract_facility_inquiry(query: str) -> tuple[bool, str | None]:
    """Phát hiện linh hoạt ý định hỏi nơi khám / bệnh viện / cơ sở kèm khu vực địa lý."""
    q = query.lower()
    region = None
    if any(k in q for k in ["hà nội", "ha noi", "hn"]):
        region = "Hà Nội"
    elif any(k in q for k in ["hồ chí minh", "tp hcm", "tphcm", "sài gòn", "sai gon", "hcm"]):
        region = "TP. Hồ Chí Minh"
    elif any(k in q for k in ["đà nẵng", "da nang"]):
        region = "Đà Nẵng"
    elif any(k in q for k in ["hải phòng", "hai phong"]):
        region = "Hải Phòng"
    elif any(k in q for k in ["nha trang"]):
        region = "Nha Trang"
    elif any(k in q for k in ["phú quốc", "phu quoc"]):
        region = "Phú Quốc"
    elif any(k in q for k in ["quảng ninh", "hạ long", "ha long"]):
        region = "Hạ Long"

    facility_keywords = [
        "bệnh viện", "cơ sở", "phòng khám", "ở đâu", "chỗ nào", "nơi nào",
        "khám ở", "viện nào", "địa chỉ", "chi nhánh"
    ]
    is_asking_facility = any(k in q for k in facility_keywords)
    return is_asking_facility, region



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
    import re

    from src.medical_assistant.domain.guardrail_service import remove_accents

    identity_query = remove_accents(query.lower())
    is_identity_query = re.search(r"(?:ten|so dien thoai|sdt|thong tin) (?:cua )?(?:toi|minh)|my (?:name|phone|contact)", identity_query)
    profile = state.get("patient_profile") or {}
    if is_identity_query and profile:
        name = profile.get("name") or state.get("patient_name") or ""
        phone = profile.get("phone") or state.get("patient_phone") or ""
        identity_response = (
            f"Dạ, tên Anh/Chị đã cung cấp là **{name}**. "
            + (f"Số điện thoại trong phiên này là **{phone}**." if phone else "Anh/Chị chưa cung cấp số điện thoại trong phiên này.")
            if lang == "vi" else f"Your provided name is **{name}**. " + (f"Your phone number in this session is **{phone}**." if phone else "No phone number was provided in this session.")
        )
        cached = (identity_response, [], "SESSION_PROFILE")
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
        "out_of_scope_decline",
    ]

    last_assistant_question = state.get("metadata", {}).get("clarification_question")
    guardrail = get_guardrail_service()
    intent_check = guardrail.check_intent(query, current_department=current_dept, language=lang)
    if not intent_check:
        fac_inquiry, fac_reg = extract_facility_inquiry(query)
        if fac_inquiry and fac_reg:
            intent_check = {
                "intent": "FACILITY_INFO",
                "matched_pattern": "smart_facility_extraction",
                "region_filter": fac_reg,
                "district_filter": None,
                "facility_name_query": None,
            }
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
            v2_response.proposed_action = "clarify_visit_purpose"
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
    patient_name = (
        booking_entities.get("patient_name")
        or (state.get("patient_profile") or {}).get("name")
        or v2_response.facts_delta.patient_name
        or state.get("patient_name")
    )
    patient_phone = (
        booking_entities.get("patient_phone")
        or (state.get("patient_profile") or {}).get("phone")
        or state.get("patient_phone")
    )
    patient_dob = (
        booking_entities.get("date_of_birth")
        or (state.get("patient_profile") or {}).get("date_of_birth")
        or state.get("patient_dob")
    )
    patient_gender = (
        booking_entities.get("gender")
        or (state.get("patient_profile") or {}).get("gender")
        or state.get("patient_gender")
    )
    patient_email = state.get("patient_email")
    facility_pref = (
        booking_entities.get("facility_preference")
        or state.get("facility_preference")
        or facility_pref
    )
    preferred_date = booking_entities.get("preferred_date") or state.get("preferred_date")
    preferred_period = booking_entities.get("preferred_period") or state.get("preferred_period")
    is_package_inquiry = bool(booking_entities.get("is_package_inquiry"))
    is_booking_intent = bool(
        booking_entities.get("is_booking_intent")
        or is_package_inquiry
        or (intent_check and intent_check.get("intent") in {"HOLD_BOOKING", "BOOKING_CONTACT_REQUEST", "FACILITY_BOOKING_START"})
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
    from src.medical_assistant.domain.action_validator import validate_action, has_clinical_evidence

    action = v2_response.proposed_action
    suggested_dept_code = department_query
    if not suggested_dept_code and triage_result.recommended_specialties:
        suggested_dept_code = triage_result.recommended_specialties[0].code
    if (
        not suggested_dept_code
        and triage_result.suggested_specialty
        and triage_result.suggested_specialty not in {"Sức khỏe tổng quát", "General Health"}
    ):
        suggested_dept_code = triage_result.suggested_specialty
    if not suggested_dept_code and rule_facts.get("chief_complaint"):
        suggested_dept_code = current_query_triage.suggested_specialty
    if not suggested_dept_code and v2_response.candidate_specialties:
        suggested_dept_code = v2_response.candidate_specialties[0].specialty_key
    if not suggested_dept_code:
        suggested_dept_code = current_dept or triage_result.suggested_specialty

    action = validate_action(action, clinical_facts, v2_response, allowed_actions)
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

    from src.medical_assistant.domain.language_service import canonicalize_specialty_code

    canonical_dept = canonicalize_specialty_code(suggested_dept_code)
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

    conversation_messages = list(state.get("messages") or [])

    return {
        "analysis": analysis,
        "is_emergency": is_emergency,
        "emergency_warning": triage_result.patient_guidance if is_emergency else None,
        "ats_level": (triage_result.ats_level.value if has_clinical_evidence(clinical_facts, v2_response) else None) if is_non_clinical else triage_result.ats_level.value,
        "urgency_tier": (triage_result.urgency_tier.value if has_clinical_evidence(clinical_facts, v2_response) else None) if is_non_clinical else triage_result.urgency_tier.value,
        "max_booking_days": 0
        if workflow_status == "SAFETY_REVIEW"
        else (None if is_non_clinical else current_max_days),
        "acuity_status": triage_result.acuity_status,
        "disposition": triage_result.disposition,
        "suggested_department_code": None if workflow_status == "VISIT_PURPOSE_CLARIFICATION" else canonical_dept,
        "suggested_department_name": None if workflow_status == "VISIT_PURPOSE_CLARIFICATION" else department_display,
        "patient_name": patient_name,
        "patient_phone": patient_phone,
        "patient_dob": patient_dob,
        "patient_gender": patient_gender,
        "patient_email": patient_email,
        "facility_preference": facility_pref,
        "preferred_date": preferred_date,
        "preferred_period": preferred_period,
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
        "messages": conversation_messages,
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
            "booking_entities_found": bool(booking_entities.get("patient_name") or booking_entities.get("patient_phone") or booking_entities.get("date_of_birth") or booking_entities.get("facility_preference") or booking_entities.get("preferred_date")),
            "tokens_saved": skip_llm,
            "llm_invoked": not skip_llm,
            "llm_succeeded": llm_succeeded,
            "candidate_specialties": candidate_specialties,
            "conflict_reason": triage_result.conflict_reason,
            "acuity_status": triage_result.acuity_status,
            "disposition": triage_result.disposition,
        },
    }


async def respond_node(state: AgentState) -> dict:
    meta = state.get("metadata", {})
    workflow_status = state.get("workflow_status", "")
    query = state.get("query") or state.get("user_input", "")
    enable_citation = state.get("enable_citation") if state.get("enable_citation") is not None else True
    patient_guidance = meta.get("patient_guidance") or state.get("emergency_warning", "")
    clarification = meta.get("clarification_question")
    quick_replies = meta.get("quick_replies", [])
    is_emergency = state.get("is_emergency", False)
    spec_name = state.get("suggested_department_name") or "Chuyên khoa phù hợp"
    lang = state.get("language") or "vi"
    spec_display = get_specialty_display_name(spec_name, lang)
    disclaimer = get_medical_disclaimer(lang)
    v2_draft = meta.get("v2_draft_response")
    # Universal Booking Intake snapshot for live form-filling (computed upfront)
    from src.medical_assistant.domain.booking_slot_service import generate_clinical_summary, detect_package_inquiry

    is_package_inquiry = bool(meta.get("is_package_inquiry") or detect_package_inquiry(query))
    is_auth = bool(state.get("is_authenticated") or state.get("user_id"))
    p_name = state.get("patient_name") or (state.get("patient_profile") or {}).get("name") or ""
    p_phone = state.get("patient_phone") or (state.get("patient_profile") or {}).get("phone") or ""
    p_dob = (
        state.get("patient_dob")
        or (state.get("patient_profile") or {}).get("date_of_birth")
        or ""
    )
    p_gender = (
        state.get("patient_gender")
        or (state.get("patient_profile") or {}).get("gender")
        or ""
    )
    fac_pref = state.get("facility_preference") or ""
    pref_date = state.get("preferred_date") or ""
    pref_period = state.get("preferred_period") or "any"
    available_docs = state.get("available_slots") or []

    # Task 2: Sinh tóm tắt lâm sàng chuẩn từ triệu chứng, vị trí, mức độ, thời gian
    clinical_summary_result = generate_clinical_summary(state, current_text=query)
    clinical_notes = clinical_summary_result.get("summary") or " ".join(state.get("collected_details") or [])
    clinical_details = clinical_summary_result.get("details") or {}

    missing_fields = [] if is_auth else evaluate_missing_fields(p_name, p_phone, p_dob, fac_pref, pref_date)

    # Task 3: Phát hiện nhu cầu gói khám
    booking_mode = "package" if is_package_inquiry or meta.get("is_package_inquiry") else "doctor"

    booking_intake = {
        "required": True,
        "endpoint": "/api/v1/booking-requests",
        "booking_mode": booking_mode,
        "patient_name": p_name,
        "patient_phone": p_phone,
        "date_of_birth": p_dob,
        "gender": p_gender,
        "specialty_code": state.get("suggested_department_code") or "",
        "specialty_name": spec_display,
        "facility_preference": fac_pref,
        "preferred_date": pref_date,
        "preferred_period": pref_period,
        "patient_notes": clinical_notes,
        "clinical_summary": clinical_notes,
        "clinical_details": clinical_details,
        "missing_fields": missing_fields,
        "is_authenticated": is_auth,
        "selected_slot_id": meta.get("slot_id"),
        "doctors": [
            {
                "id": doctor.get("id"),
                "name": doctor.get("full_name"),
                "title": doctor.get("title"),
                "source_url": doctor.get("source_url"),
            }
            for doctor in available_docs
        ],
    }

    if workflow_status == "SECURITY_BLOCKED":
        response = meta.get("security_response") or "Yêu cầu bị từ chối do vi phạm quy chuẩn an toàn thông tin."
    elif is_emergency:
        response = patient_guidance
    elif workflow_status == "FAQ_ANSWERED" and meta.get("cached_response"):
        response = meta["cached_response"]
    elif workflow_status == "GUARDRAIL_MEDICATION":
        symptoms = " ".join(state.get("collected_details") or [])
        response, quick_replies = get_guardrail_service().get_medication_guardrail_response(symptoms, spec_name, lang)
    elif workflow_status == "GUARDRAIL_DIAGNOSIS":
        symptoms = " ".join(state.get("collected_details") or [])
        response, quick_replies = get_guardrail_service().get_diagnosis_guardrail_response(symptoms, spec_name, lang)
        candidates = state.get("candidate_specialties") or []
        if len(candidates) >= 2:
            secondary_names = ", ".join(item.get("name") or item.get("code", "") for item in candidates[1:3])
            if lang == "vi":
                response += (
                    "\n\nDo triệu chứng thuộc nhiều nhóm cơ quan, hướng ưu tiên vẫn là "
                    f"**Khoa {spec_display}**; đồng thời cần cân nhắc **{secondary_names}** "
                    "nếu các triệu chứng tương ứng còn tiếp diễn."
                )
            else:
                response += (
                    "\n\nBecause the symptoms span more than one clinical system, the priority remains "
                    f"**{spec_display}**; **{secondary_names}** should also be considered if those symptoms persist."
                )
    elif workflow_status == "SAFETY_REVIEW":
        facts = state.get("clinical_facts") or {}
        positives = set(facts.get("positive_facts") or [])
        active_complaints = set(facts.get("active_complaint_codes") or [])
        has_chest = "chest_pain" in active_complaints or "chest_pain" in positives
        has_neuro_visual = "headache" in active_complaints and "vision_changes" in positives
        if lang == "vi" and has_chest and has_neuro_visual:
            response = (
                "Dạ, tổ hợp **đau hoặc tức ngực, đau đầu và nhìn mờ** cần được đánh giá trực tiếp trong hôm nay; "
                "em không chuyển bác sang đặt lịch khám thường. Nếu bác vẫn đang tức ngực, triệu chứng kéo dài từ 10 phút, "
                "hoặc có khó thở, vã mồ hôi, choáng/ngất, yếu tê một bên hay nói khó, bác hãy gọi 115 hoặc đến Cấp cứu ngay."
            )
        elif lang == "vi" and has_chest:
            response = (
                "Dạ, đau hoặc tức ngực mới xuất hiện cần được đánh giá trực tiếp trong hôm nay trước khi đặt lịch thường. "
                "Nếu cơn đau đang tiếp diễn, kéo dài từ 10 phút, hoặc kèm khó thở, vã mồ hôi, choáng/ngất hay lan ra tay, hàm hoặc lưng, "
                "bác hãy gọi 115 hoặc đến Cấp cứu ngay."
            )
        elif lang == "vi" and has_neuro_visual:
            response = (
                "Dạ, đau đầu kèm nhìn mờ cần được đánh giá trực tiếp trong hôm nay. Nếu đau đầu khởi phát đột ngột hoặc dữ dội, "
                "mất thị lực, yếu tê một bên, méo miệng, nói khó, lơ mơ hoặc co giật, bác hãy gọi 115 hoặc đến Cấp cứu ngay."
            )
        else:
            response = (
                "Dạ, thông tin hiện có cần được nhân viên y tế đánh giá trực tiếp trong hôm nay trước khi tìm lịch khám thường. "
                "Nếu triệu chứng đang tăng nhanh, đau dữ dội, khó thở, lơ mơ hoặc chảy máu nhiều, bác hãy gọi 115 hoặc đến Cấp cứu gần nhất."
                if lang == "vi"
                else "Your information requires an in-person clinical assessment today before routine scheduling. If symptoms are ongoing, severe, or worsening, seek emergency care now."
            )
        quick_replies = (
            ["Các triệu chứng vẫn đang tiếp diễn", "Có thêm dấu hiệu nguy hiểm"]
            if lang == "vi"
            else ["Symptoms are still ongoing", "There are additional warning signs"]
        )
    elif workflow_status == "DEPARTMENT_INFO":
        # Retrieve comparison flag from meta
        comparison_requested = meta.get("comparison_requested", False)

        info_resp, info_replies = get_guardrail_service().get_department_info_response(
            spec_display,
            language=lang,
            query=state.get("query", ""),
            comparison_requested=comparison_requested,
            enable_citation=enable_citation,
        )
        response = info_resp
        quick_replies = info_replies
    elif workflow_status == "FACILITY_INFO":
        from src.medical_assistant.domain.facility_service import get_facility_service

        region_filter = meta.get("region_filter")
        district_filter = meta.get("district_filter")
        facility_name_query = meta.get("facility_name_query")
        dept_context = state.get("suggested_department_name") or (
            spec_display if spec_display != "Sức khỏe tổng quát" else None
        )
        facility_resp, quick_replies = await asyncio.to_thread(
            get_facility_service().get_facilities_response,
            language=lang,
            region_filter=region_filter,
            district_filter=district_filter,
            facility_name_query=facility_name_query,
            department_context=dept_context,
            enable_citation=enable_citation,
        )

        clinical_prefix = ""
        has_clinical = bool(
            (state.get("clinical_facts") or {}).get("chief_complaint")
            or (state.get("clinical_facts") or {}).get("positive_facts")
            or state.get("collected_details")
            or any(kw in query.lower() for kw in ["đau", "nhức", "mỏi", "khó chịu", "khớp", "ngón tay", "lưng", "gối", "đầu"])
        )
        if has_clinical and dept_context:
            symptom_loc = ""
            for kw in ["khớp ngón tay cái", "ngón tay cái", "ngón tay", "khớp ngón", "khớp gối", "đầu gối", "cổ vai gáy", "thắt lưng", "cổ tay", "khớp"]:
                if kw in query.lower():
                    symptom_loc = f" ở {kw}"
                    break
            clinical_prefix = (
                f"Dạ, em đã ghi nhận triệu chứng của bác{symptom_loc}.\n"
                f"Về chuyên khoa, bác nên thăm khám tại **Khoa {dept_context}** để bác sĩ kiểm tra và đưa ra chẩn đoán chính xác nhất.\n\n"
            ) if lang == "vi" else (
                f"I have noted your reported symptoms{symptom_loc}. Given your symptoms, an in-person evaluation at **{dept_context}** is recommended.\n\n"
            )

        booking_suffix = ""
        if meta.get("is_booking_intent") or booking_intake.get("required"):
            p_label = f" (**Bệnh nhân:** {booking_intake.get('patient_name')}, **Chuyên khoa:** {spec_display})" if is_auth and booking_intake.get('patient_name') else ""
            region_str = f" tại {region_filter}" if region_filter else ""
            booking_suffix = (
                f"\n\n📋 **Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa:**\n"
                f"Em đã tự động trích xuất thông tin của bác vào phiếu ở khung bên cạnh{p_label}. "
                f"Bác vui lòng chọn cơ sở mong muốn{region_str} và ngày khám phù hợp trên phiếu rồi bấm **'Xác nhận gửi thông tin đặt khám'** nhé ạ!"
            ) if lang == "vi" else (
                f"\n\n📋 **Appointment Request Form:**\n"
                f"I have pre-filled your details on the right panel. Please select your preferred facility and date, then confirm to submit your request!"
            )

        response = clinical_prefix + facility_resp + booking_suffix
    elif workflow_status == "FACILITY_DOCTORS":
        from src.medical_assistant.domain.facility_service import get_facility_service

        fac_q = meta.get("facility_name_query") or state.get("metadata", {}).get("facility_preference") or "Vinmec"
        dept_ctx = state.get("suggested_department_name") or spec_display
        if dept_ctx in {"Sức khỏe tổng quát", "General Health"}:
            dept_ctx = None
        booking_intake["facility_preference"] = fac_q.title()
        response, quick_replies = await asyncio.to_thread(
            get_facility_service().get_facility_doctors_response,
            facility_query=fac_q,
            language=lang,
            enable_citation=enable_citation,
            department_context=dept_ctx,
            booking_intake=booking_intake,
            is_authenticated=is_auth,
        )
    elif workflow_status == "FACILITY_BOOKING_START":
        from src.medical_assistant.domain.facility_service import get_facility_service

        fac_q = meta.get("facility_name_query") or state.get("metadata", {}).get("facility_preference") or "Vinmec"
        response, quick_replies = await asyncio.to_thread(
            get_facility_service().get_facility_booking_guidance_response,
            facility_query=fac_q,
            language=lang,
        )
    elif is_package_inquiry and not is_emergency:
        response = (
            "Dạ, Vinmec hiện có các **Gói khám sức khỏe tổng quát và lộ trình tầm soát chuyên sâu** "
            "(như Khám sức khỏe định kỳ, Tầm soát tim mạch, Tầm soát ung thư sớm, Gói thai sản/sinh nở...).\n\n"
            "Em đã tự động chuyển **Phiếu Đăng Ký Khám** ở khung bên cạnh sang chế độ **Gói Khám Bệnh**. "
            "Bác có thể tra cứu chi tiết danh mục gói, chi phí niêm yết và chọn gửi yêu cầu trực tiếp trên bảng bên cạnh nhé ạ!"
        ) if lang == "vi" else (
            "Vinmec provides various comprehensive Health Checkup and Screening Packages. "
            "I have switched the Live Booking Panel on the right to **Health Packages** mode so you can view details and register directly!"
        )
        quick_replies = [
            "Gói khám tổng quát",
            "Tầm soát tim mạch",
            "Tầm soát ung thư",
            "Khám bác sĩ chuyên khoa",
        ] if lang == "vi" else ["Health checkup", "Cancer screening", "Specialist booking"]
    elif workflow_status == "BOOKING_CONTACT_REQUIRED":
        response = build_booking_guidance_text(
            is_authenticated=is_auth,
            missing_fields=missing_fields,
            current_intake=booking_intake,
            specialty_name=spec_display,
            lang=lang,
        )
        quick_replies = []
    elif (
        (meta.get("is_booking_intent") or meta.get("booking_entities_found"))
        and not is_emergency
        and workflow_status != "VISIT_PURPOSE_CLARIFICATION"
    ):
        is_fac_ask, fac_reg = extract_facility_inquiry(query)
        if (is_fac_ask or meta.get("is_facility_inquiry")) and not is_emergency:
            from src.medical_assistant.domain.facility_service import get_facility_service
            region_filter = fac_reg or meta.get("region_filter") or "Hà Nội"
            dept_context = state.get("suggested_department_name") or spec_display
            facility_resp, f_replies = await asyncio.to_thread(
                get_facility_service().get_facilities_response,
                language=lang,
                region_filter=region_filter,
                department_context=dept_context,
                enable_citation=enable_citation,
            )
            booking_cta = (
                f"\n\n📋 **Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa:**\n"
                f"Em đã tự động trích xuất thông tin của bác vào phiếu ở khung bên cạnh"
                + (f" (**Bệnh nhân:** {booking_intake.get('patient_name')}, **Chuyên khoa:** {spec_display})." if is_auth and booking_intake.get('patient_name') else ".")
                + f" Bác vui lòng chọn cơ sở mong muốn tại {region_filter} và xác nhận trên phiếu bên cạnh nhé ạ!"
            ) if lang == "vi" else (
                f"\n\n📋 **Appointment Request Form:**\n"
                f"I have pre-filled your details on the right panel. Please choose your preferred facility and confirm!"
            )
            lead_in = ""
            if v2_draft and len(v2_draft.strip()) > 20:
                cleaned_draft = re.sub(
                    r"(Bác có muốn xem lịch khám không[^\n]*|Em có thể hỗ trợ tìm bác sĩ[^\n]*|Bác có muốn đặt lịch[^\n]*)",
                    "",
                    v2_draft,
                    flags=re.IGNORECASE,
                ).strip()
                lead_in = (cleaned_draft + "\n\n") if cleaned_draft else ""
            if not lead_in:
                lead_in = f"Dạ, với triệu chứng khó chịu bác đang gặp, bác nên thăm khám tại **Khoa {dept_context}** để được kiểm tra trực tiếp.\n\n"
            response = lead_in + facility_resp + booking_cta
            quick_replies = [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Smart City"] if lang == "vi" else ["Times City", "Smart City"]
        elif has_compound_question and v2_draft and len(v2_draft.strip()) > 30 and not v2_draft.strip().startswith("Dạ, em đã điền sẵn"):
            booking_cta = (
                f"\n\n📋 **Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa:**\n"
                f"Em đã tự động trích xuất thông tin của bác vào phiếu ở khung bên cạnh"
                + (f" (**Bệnh nhân:** {booking_intake.get('patient_name')}, **Chuyên khoa:** {spec_display})." if is_auth and booking_intake.get('patient_name') else ".")
                + " Bác vui lòng kiểm tra lại thông tin và xác nhận trên phiếu bên cạnh nhé ạ!"
            ) if lang == "vi" else (
                f"\n\n📋 **Appointment Request Form:**\n"
                f"I have pre-filled the appointment details on the right panel. Please review and confirm your request!"
            )
            response = v2_draft + booking_cta
            quick_replies = [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Central Park"] if lang == "vi" else ["Times City", "Central Park"]
        else:
            response = build_booking_guidance_text(
                is_authenticated=is_auth,
                missing_fields=missing_fields,
                current_intake=booking_intake,
                specialty_name=spec_display,
                lang=lang,
            )
            quick_replies = [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Central Park"] if lang == "vi" else ["Times City", "Central Park"]
    elif workflow_status == "TRIAGED_READY_FOR_BOOKING":
        max_days = state.get("max_booking_days", 7)
        available_docs = state.get("available_slots") or []

        doctors_text = ""
        if available_docs:
            has_verified_slots = any(
                slot.get("verified") for doctor in available_docs for slot in doctor.get("available_slots", [])
            )
            if lang == "en":
                doctors_text = f"\n\n👨‍⚕️ **Sourced specialists for {spec_display}:**\n"
                for idx, doc in enumerate(available_docs, 1):
                    exp = doc.get("years_of_experience", 0)
                    exp_text = f" - {exp} years of experience" if exp else ""
                    doctors_text += f"\n**{idx}. Dr. {doc['full_name']}** ({doc['title']}{exp_text})\n"
                    if doc.get("workplace"):
                        doctors_text += f"   • Workplace: {doc['workplace']}\n"
                    for slot in doc.get("available_slots", []):
                        if slot.get("verified"):
                            doctors_text += (
                                f"   • Verified time: `{slot['starts_at']}` (Slot ID: `{slot['schedule_id']}`)\n"
                            )
                    if doc.get("source_url"):
                        doctors_text += f"   • [Official profile]({doc['source_url']})\n"
            else:
                doctors_text = f"\n\n👨‍⚕️ **Bác sĩ phù hợp có hồ sơ nguồn ({spec_display}):**\n"
                for idx, doc in enumerate(available_docs, 1):
                    exp = doc.get("years_of_experience", 0)
                    exp_text = f" - {exp} năm kinh nghiệm" if exp else ""
                    doctors_text += f"\n**{idx}. {doc['full_name']}** ({doc['title']}{exp_text})\n"
                    specialties = ", ".join(doc.get("specialties") or [])
                    if specialties:
                        doctors_text += f"   • Chuyên môn: {specialties}\n"
                    if doc.get("workplace"):
                        doctors_text += f"   • Nơi làm việc: {doc['workplace']}\n"
                    for slot in doc.get("available_slots", []):
                        if slot.get("verified"):
                            doctors_text += f"   • Lịch được database xác minh: `{slot['starts_at']}` (Mã slot: `{slot['schedule_id']}`)\n"
                    if doc.get("source_url") and enable_citation:
                        doctors_text += f"   • [Hồ sơ nguồn Vinmec]({doc['source_url']})\n"
            if has_verified_slots:
                prefix = (
                    f"Em đã kiểm tra lịch được database xác minh tại **Khoa {spec_display}** trong {max_days} ngày tới."
                    if lang == "vi"
                    else f"I found database-verified availability at **{spec_display}** for the next {max_days} days."
                )
                quick_replies = []
            else:
                prefix = (
                    "Database hiện chưa có lịch trống được xác minh. Em chỉ hiển thị hồ sơ bác sĩ từ dữ liệu crawl có URL nguồn; "
                    "đây không phải xác nhận bác sĩ đang rảnh."
                    if lang == "vi"
                    else "The database currently has no verified availability. These sourced doctor profiles do not confirm that the doctors are free."
                )
                quick_replies = (
                    ["Để lại thông tin để điều phối viên liên hệ", "Chọn cơ sở khác"]
                    if lang == "vi"
                    else ["Request coordinator contact", "Choose another facility"]
                )
            form_hint = (
                "\n\n📋 *Em đã tự động điền sẵn thông tin từ tài khoản của bác vào Phiếu Đăng Ký Khám ở khung bên cạnh. Bác vui lòng kiểm tra lại và xác nhận nhé!*"
                if is_auth
                else "\n\n📋 *Bác có thể nhắn Họ tên, SĐT và Ngày sinh để em tự động điền giúp bác, hoặc tự điền vào Phiếu Khám ở khung bên cạnh nhé ạ!*"
            ) if lang == "vi" else (
                "\n\n📋 *I have pre-filled the Appointment Form on the right panel with your profile. Please review and confirm!*"
                if is_auth
                else "\n\n📋 *You can provide your name, phone, and DOB for auto-fill, or type directly into the form on the right panel!*"
            )
            response = f"{prefix}{doctors_text}{form_hint}"
        else:
            response = (
                "Xin lỗi bác, hiện tại em chưa tìm thấy lịch khám phù hợp. Bác có muốn chọn ngày khác hoặc để em hỗ trợ thêm không ạ?"
                if lang == "vi"
                else "Sorry, I couldn't find any available slots. Would you like to try another date?"
            )
            quick_replies = ["Chọn ngày khác"] if lang == "vi" else ["Choose another date"]
    elif workflow_status in ["PROBING_IN_PROGRESS", "TRIAGED_AWAITING_SCHEDULE", "VISIT_PURPOSE_CLARIFICATION"]:
        if workflow_status == "VISIT_PURPOSE_CLARIFICATION" and meta.get("describe_more_requested"):
            response = v2_draft
            quick_replies = (
                ["Mô tả triệu chứng chính", "Triệu chứng mới xuất hiện", "Quay lại"]
                if lang == "vi"
                else ["Describe the main symptom", "New symptom", "Go back"]
            )
        elif workflow_status == "VISIT_PURPOSE_CLARIFICATION":
            response, quick_replies = get_guardrail_service().get_visit_purpose_clarification_response(lang)
        elif workflow_status == "TRIAGED_AWAITING_SCHEDULE":
            candidates = state.get("candidate_specialties") or []
            if len(candidates) >= 2:
                other_names = ", ".join(item.get("name") or item.get("code", "") for item in candidates[1:3])
                response = (
                    f"Dạ, bác đang có triệu chứng thuộc nhiều nhóm cơ quan. Hướng ưu tiên hiện tại là **Khoa {spec_display}**; "
                    f"đồng thời cần cân nhắc **{other_names}** dựa trên diễn biến và các dấu hiệu kèm theo. "
                    "Bác có muốn em tìm lịch theo hướng ưu tiên này không ạ?"
                    if lang == "vi"
                    else f"Your symptoms span more than one clinical system. The current priority is **{spec_display}**, while **{other_names}** also remains relevant. Would you like me to check appointments for the priority specialty?"
                )
            else:
                response = (
                    f"Dạ, dựa trên thông tin đã ghi nhận, hướng khám phù hợp là **Khoa {spec_display}**. Bác có muốn em tìm lịch khám phù hợp không ạ?"
                    if lang == "vi"
                    else f"Based on the information provided, an evaluation at **{spec_display}** is appropriate. Would you like me to check available appointments?"
                )
            quick_replies = (
                [f"Xem lịch {spec_display}", "Mô tả thêm triệu chứng"]
                if lang == "vi"
                else [f"View {spec_display} schedule", "Add symptom details"]
            )
        else:
            clinical_facts = state.get("clinical_facts") or {}
            chief = clinical_facts.get("chief_complaint")
            if lang == "en" and chief:
                response = f"I've noted your {chief.replace('_', ' ')}. {clarification or v2_draft}"
            elif lang == "vi":
                detail = clarification or v2_draft
                response = (
                    detail
                    if detail.startswith("Dạ, em đã ghi nhận")
                    else f"Dạ, em đã ghi nhận triệu chứng của bác.\n\n{detail}"
                )
            else:
                response = clarification or v2_draft or "How may I help further?"
    elif workflow_status == "HUMAN_HELP_REQUESTED":
        response = (
            "Dạ, em chưa thể xác nhận đã kết nối nhân viên ngay trong cuộc trò chuyện này. Bác có thể chọn kênh hỗ trợ trực tiếp để được tiếp nhận."
            if lang == "vi"
            else "I cannot confirm a live handoff in this chat. Please choose a direct support channel."
        )
    elif workflow_status == "LANGUAGE_CHANGED":
        response = (
            "Dạ, em đã chuyển sang tiếng Việt. Bác muốn em tiếp tục hỗ trợ nội dung nào ạ?"
            if lang == "vi"
            else "I've switched to English. How may I continue helping you?"
        )
    elif workflow_status == "SOCIAL_REDIRECT":
        response = (
            "Dạ, em hiểu đây có vẻ là chuyện cá nhân. Em không đánh giá hay suy đoán về người đó. "
            "Nếu bác muốn, em có thể tiếp tục hỗ trợ vấn đề sức khỏe hoặc yêu cầu đặt lịch đang trao đổi."
            if lang == "vi"
            else "That sounds like a personal matter. I won't judge or speculate about that person. I can continue helping with your health or appointment request."
        )
        quick_replies = (
            ["Tiếp tục vấn đề sức khỏe của tôi", "Xem lại chuyên khoa đã gợi ý"]
            if lang == "vi"
            else ["Continue my health concern", "Review the suggested specialty"]
        )
    elif workflow_status == "THIRD_PARTY_HEALTH_GUIDANCE":
        topic = meta.get("third_party_topic")
        if topic == "infertility":
            response = (
                "Dạ, nếu đây là tình trạng của một người khác, em không thể xác nhận chẩn đoán từ lời kể gián tiếp. "
                "Nếu người đó đã được đánh giá hoặc đang lo về vô sinh/hiếm muộn, hướng phù hợp là **Trung tâm Hỗ trợ sinh sản**, "
                "nơi có thể phối hợp đánh giá cả nam khoa và sản phụ khoa. Chính người cần khám nên trực tiếp cung cấp thông tin hoặc đồng ý trước khi tạo yêu cầu đặt lịch."
                if lang == "vi"
                else "I cannot confirm another person's diagnosis from a second-hand account. For infertility concerns, a reproductive medicine service can coordinate male and female fertility assessment. The patient should provide or consent to their own booking details."
            )
            quick_replies = (
                ["Xem thông tin Hỗ trợ sinh sản", "Quay lại vấn đề sức khỏe của tôi"]
                if lang == "vi"
                else ["View fertility service information", "Return to my health concern"]
            )
        else:
            response = (
                "Dạ, em có thể cung cấp định hướng chung, nhưng không thể đánh giá sức khỏe của người khác từ lời kể gián tiếp. "
                "Người cần khám nên trực tiếp mô tả triệu chứng hoặc đồng ý để cung cấp thông tin đặt lịch."
                if lang == "vi"
                else "I can provide general guidance, but I cannot assess another person's health from a second-hand account. The patient should describe their symptoms directly or consent to booking."
            )
            quick_replies = ["Quay lại vấn đề sức khỏe của tôi"] if lang == "vi" else ["Return to my health concern"]
    elif workflow_status == "OUT_OF_SCOPE":
        response = (
            "Dạ, em chỉ có thể hỗ trợ định hướng khám, thông tin bệnh viện và lịch hẹn trong phạm vi hệ thống."
            if lang == "vi"
            else "I can only help with care navigation, hospital information, and appointments within this system."
        )
    else:
        response = v2_draft if v2_draft else "Xin lỗi, tôi không thể xử lý yêu cầu của bạn."

    patient_profile = state.get("patient_profile") or {}
    display_name = patient_profile.get("name")
    if display_name and workflow_status != "SECURITY_BLOCKED" and display_name not in response:
        response = (f"Dạ {display_name},\n\n" if lang == "vi" else f"Hello {display_name},\n\n") + response

    full_response = response if workflow_status in {"SECURITY_BLOCKED", "SOCIAL_REDIRECT"} else response + disclaimer

    from src.medical_assistant.domain.security.dlp_service import get_dlp_service

    dlp_service = get_dlp_service()
    dlp_scan = dlp_service.sanitize(
        full_response, allowed_user_id=state.get("user_id"), allowed_user_phone=state.get("patient_phone")
    )
    full_response = dlp_scan.sanitized_text

    from src.medical_assistant.domain.token_counter import get_token_counter

    token_counter = get_token_counter()
    llm_fallback = bool(meta.get("llm_invoked")) and meta.get("llm_succeeded") is False
    zero_token = (
        bool(meta.get("tokens_saved")) or llm_fallback or workflow_status in {"SECURITY_BLOCKED", "FAQ_ANSWERED"}
    )
    token_metrics = token_counter.calculate_turn_metrics(
        state.get("query") or "", full_response, " ".join(state.get("collected_details") or []), zero_token
    )
    if llm_fallback:
        token_metrics["model"] = "fallback-rule"
        token_metrics["execution_mode"] = "llm_fallback_rule"
    meta["token_usage"] = token_metrics
    meta["quick_replies"] = quick_replies
    meta["booking_intake"] = None if workflow_status in {"FAQ_ANSWERED", "SECURITY_BLOCKED"} else booking_intake
    meta["dlp_leakage_detected"] = dlp_scan.has_leakage

    # Cập nhật và lưu giữ lịch sử hội thoại (Conversation Memory)
    history = list(state.get("messages") or [])
    user_q = state.get("query") or ""
    if user_q:
        history.append({"role": "user", "content": user_q})
    history.append({"role": "assistant", "content": full_response})
    if len(history) > 20:
        history = history[-20:]

    return {
        "response": full_response,
        "disclaimer": disclaimer,
        "token_usage": token_metrics,
        "metadata": meta,
        "messages": history,
        "last_assistant_response": full_response,
    }
