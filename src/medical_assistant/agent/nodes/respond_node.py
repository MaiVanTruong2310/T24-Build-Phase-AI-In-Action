import asyncio
import logging
import re

from src.medical_assistant.agent.nodes.helpers import extract_facility_inquiry
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.booking_slot_service import (
    build_booking_guidance_text,
    detect_package_inquiry,
    evaluate_missing_fields,
    generate_clinical_summary,
)
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.language_service import (
    get_medical_disclaimer,
    get_same_day_safety_net,
    get_specialty_display_name,
)

logger = logging.getLogger(__name__)


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

    is_package_inquiry = bool(meta.get("is_package_inquiry") or detect_package_inquiry(query))
    has_compound_question = bool(meta.get("has_compound_question") or meta.get("compound_question"))
    is_auth = bool(state.get("is_authenticated") or state.get("user_id"))
    existing_intake = state.get("booking_intake") or (state.get("metadata") or {}).get("booking_intake") or {}
    p_name = (
        state.get("patient_name")
        or (state.get("patient_profile") or {}).get("name")
        or existing_intake.get("patient_name")
        or ""
    )
    p_phone = (
        state.get("patient_phone")
        or (state.get("patient_profile") or {}).get("phone")
        or existing_intake.get("patient_phone")
        or ""
    )
    p_dob = (
        state.get("patient_dob")
        or (state.get("patient_profile") or {}).get("date_of_birth")
        or existing_intake.get("date_of_birth")
        or ""
    )
    p_gender = (
        state.get("patient_gender")
        or (state.get("patient_profile") or {}).get("gender")
        or existing_intake.get("gender")
        or ""
    )
    fac_pref = state.get("facility_preference") or existing_intake.get("facility_preference") or ""
    pref_date = state.get("preferred_date") or existing_intake.get("preferred_date") or ""
    pref_period = state.get("preferred_period") or existing_intake.get("preferred_period") or "any"
    available_docs = state.get("available_slots") or []
    doc_pref = state.get("doctor_preference") or existing_intake.get("doctor_preference") or ""
    doc_name = state.get("doctor_name") or existing_intake.get("doctor_name") or ""

    # Đánh giá lộ trình chuyên khoa phân tầng (Care Pipeline) dựa trên toàn bộ lịch sử triệu chứng
    full_clinical_text = " ".join([*state.get("collected_details", []), query]).strip()
    from src.medical_assistant.domain.care_pipeline_service import get_care_pipeline_service

    care_pipeline = get_care_pipeline_service().evaluate_multi_specialty_pipeline(
        full_clinical_text or query, language=lang
    )

    ranked_specialties = []
    if care_pipeline.is_multi_specialty:
        spec_display = care_pipeline.primary_department
        ranked_specialties = [
            {
                "priority": step.step_number,
                "department_name": step.department_name,
                "department_code": step.department_code,
                "rationale": step.clinical_rationale,
                "target_symptoms": step.target_symptoms,
                "is_primary": (step.step_number == 1),
            }
            for step in care_pipeline.pipeline_steps
        ]
    elif spec_display:
        ranked_specialties = [
            {
                "priority": 1,
                "department_name": spec_display,
                "department_code": state.get("suggested_department_code") or "",
                "rationale": "Chuyên khoa phù hợp với triệu chứng",
                "target_symptoms": [],
                "is_primary": True,
            }
        ]

    should_fetch_slots = bool(
        not available_docs
        and spec_display
        and not meta.get("slots_fetched_in_turn")
        and workflow_status
        in {
            "TRIAGED_READY_FOR_BOOKING",
            "TRIAGED_AWAITING_SCHEDULE",
            "FACILITY_DOCTORS",
            "CONFIRM_BOOKING_CONVERSATIONALLY",
            "BOOKING_CONTACT_REQUIRED",
        }
    )
    if should_fetch_slots:
        from src.medical_assistant.domain.doctor_schedule_service import fetch_available_doctors_slots_cached

        available_docs, slot_unavail, slot_reason = await fetch_available_doctors_slots_cached(
            state=state,
            specialty_name=spec_display,
            limit_doctors=5,
            facility_id=fac_pref,
        )
        if slot_unavail:
            meta["data_unavailable"] = True
            meta["data_unavailable_reason"] = slot_reason
        meta["slots_fetched_in_turn"] = True

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
        "specialty_code": state.get("suggested_department_code")
        or (ranked_specialties[0]["department_code"] if ranked_specialties else ""),
        "specialty_name": spec_display,
        "is_multi_specialty": care_pipeline.is_multi_specialty,
        "ranked_specialties": ranked_specialties,
        "facility_preference": fac_pref,
        "preferred_date": pref_date,
        "preferred_period": pref_period,
        "doctor_preference": doc_pref,
        "doctor_name": doc_name,
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
    elif workflow_status == "CONFIRM_BOOKING_CONVERSATIONALLY":
        from src.medical_assistant.domain.booking_lookup_service import _format_vn_date_str, get_booking_lookup_service

        lookup_svc = get_booking_lookup_service()
        guest_token = state.get("guest_token") or ""
        session_id = state.get("session_id") or "session"

        p_name = (
            booking_intake.get("patient_name")
            or (state.get("patient_profile") or {}).get("name")
            or state.get("patient_name")
            or "Quý khách"
        )
        p_phone = (
            booking_intake.get("patient_phone")
            or (state.get("patient_profile") or {}).get("phone")
            or state.get("patient_phone")
        )
        pref_date = booking_intake.get("preferred_date") or state.get("preferred_date")
        facility_name = (
            booking_intake.get("facility_preference")
            or state.get("facility_preference")
            or "Chưa chọn cơ sở (điều phối viên tư vấn cơ sở phù hợp)"  # không tự gán cơ sở thay bệnh nhân
        )

        if ranked_specialties and len(ranked_specialties) > 1:
            spec_display_name = " ➔ ".join([s["department_name"] for s in ranked_specialties])
        else:
            spec_display_name = spec_display or state.get("suggested_department_name") or "Chuyên khoa phù hợp"

        doc_display_name = booking_intake.get("doctor_name") or "Điều phối viên y tế sắp xếp bác sĩ phù hợp nhất"
        pref_period = booking_intake.get("preferred_period") or state.get("preferred_period") or "morning"
        period_display = (
            "Buổi sáng (08:00 - 12:00)"
            if pref_period == "morning"
            else ("Buổi chiều (13:00 - 17:00)" if pref_period == "afternoon" else "Linh hoạt")
        )

        if not p_name or not p_phone or len(str(p_phone).replace(" ", "")) < 9:
            latest_text = str(state.get("query") or state.get("user_input") or "")
            # SĐT quá ngắn (LLM có thể trích "12345") cũng là SĐT sai, không phải "chưa có SĐT".
            phone_invalid = bool(p_phone) and len(str(p_phone).replace(" ", "")) < 9
            if phone_invalid:
                p_phone = None
            if (not p_phone and re.search(r"\d{4,}", latest_text)) or phone_invalid:
                # Có gõ dãy số nhưng không phải SĐT Việt Nam hợp lệ → nói rõ thay vì lặp lại câu chung.
                response = (
                    "Dạ, số điện thoại bác vừa nhắn chưa đúng định dạng (cần 10 số, ví dụ 0912 345 678). "
                    "Bác vui lòng kiểm tra và nhắn lại số điện thoại giúp em nhé ạ!"
                )
            elif p_name and p_name != "Quý khách" and not p_phone:
                response = (
                    f"Dạ, em đã ghi nhận tên **{p_name}**. "
                    "Bác vui lòng cho em xin **Số điện thoại** để nhân viên y tế liên hệ xác nhận lịch nhé ạ!"
                )
            else:
                response = (
                    "Dạ, em rất sẵn lòng hỗ trợ giữ chỗ và đặt lịch ngay cho bác! "
                    "Tuy nhiên em cần thêm **Họ và tên** cùng **Số điện thoại** chính xác để nhân viên y tế liên hệ tiếp nhận. "
                    "Bác vui lòng nhắn lại thông tin giúp em nhé ạ!"
                )
            if lang == "en":
                if (not p_phone and re.search(r"\d{4,}", latest_text)) or phone_invalid:
                    response = (
                        "The phone number you sent doesn't look valid (a 10-digit Vietnamese number, "
                        "e.g. 0912 345 678). Could you please check and send it again?"
                    )
                elif p_name and p_name != "Quý khách" and not p_phone:
                    response = f"Thank you, **{p_name}**. Could you share your **phone number** so our coordinator can confirm the appointment?"
                else:
                    response = (
                        "I'd be glad to book this for you! Please send your **full name** and **phone number** "
                        "so our coordinator can contact you to confirm."
                    )
            quick_replies = []
        else:
            intake_payload = {
                **booking_intake,
                "patient_name": p_name,
                "patient_phone": p_phone,
                "facility_preference": facility_name,
                "preferred_date": pref_date,
                "preferred_period": pref_period,
                # Phiếu cho điều phối viên luôn ghi tên chuyên khoa tiếng Việt.
                "specialty_name": get_specialty_display_name(spec_display_name, "vi")
                if lang == "en"
                else spec_display_name,
                "doctor_name": doc_display_name,
            }
            try:
                commit_res = await lookup_svc.auto_commit_conversational_booking(
                    intake_data=intake_payload,
                    user=None,
                    session_id=session_id,
                    guest_token=guest_token,
                    state=state,
                )
                request_code = commit_res["request_code"]
                booking_intake.update(
                    {
                        "confirmed": True,
                        "saved": True,
                        "request_code": request_code,
                        "request_id": commit_res["request_id"],
                    }
                )
                date_text = (
                    _format_vn_date_str(pref_date) if pref_date else "Điều phối viên liên hệ sắp xếp ngày gần nhất"
                )
                symptoms_text = (
                    booking_intake.get("patient_notes")
                    or " | ".join(state.get("collected_details") or [])
                    or "Khám và tư vấn chuyên khoa"
                )

                response = (
                    f"🎉 **ĐÃ GIỮ CHỖ THÀNH CÔNG!**\n\n"
                    f"Dạ bác **{p_name}**, em đã ghi nhận yêu cầu đặt lịch của bác lên hệ thống điều phối y tế Vinmec:\n\n"
                    f"📋 **Thông tin phiếu hẹn:**\n"
                    f"• 🔖 **Mã tiếp nhận / Mã phiếu hẹn:** `{request_code}`\n"
                    f"• 👤 **Bệnh nhân:** {p_name}\n"
                    f"• 📞 **Số điện thoại:** {p_phone}\n"
                    f"• 🩺 **Lộ trình chuyên khoa (Ưu tiên):** {spec_display_name}\n"
                    f"• 🏥 **Cơ sở khám:** {facility_name}\n"
                    f"• 👨‍⚕️ **Bác sĩ:** {doc_display_name}\n"
                    f"• 📅 **Ngày khám:** {date_text}\n"
                    f"• ⏰ **Buổi khám:** {period_display}\n"
                    f"• 📝 **Lý do & Triệu chứng:** {symptoms_text}\n\n"
                    f"✅ **Đã giữ chỗ thành công! Bác hãy để ý số điện thoại của mình ({p_phone}) để được nhân viên điều phối có thể liên lạc và chốt lịch của bạn nhé ạ!**\n\n"
                    f"💡 Bác có thể dùng mã phiếu `{request_code}` tra cứu trạng thái tiếp nhận tại mục **Tiến trình điều trị** trên thanh menu bất cứ lúc nào."
                )
                quick_replies = ["Tiến trình điều trị", "Cần tư vấn thêm"]
                if lang == "en":
                    response = (
                        f"🎉 **APPOINTMENT REQUEST RECEIVED!**\n\n"
                        f"📋 **Request code:** `{request_code}`\n"
                        f"• 👤 **Patient:** {p_name}\n"
                        f"• 📞 **Phone:** {p_phone}\n"
                        f"• 🩺 **Specialty:** {spec_display_name}\n"
                        f"• 🏥 **Facility:** {facility_name}\n"
                        f"• 👨‍⚕️ **Doctor:** {doc_display_name}\n"
                        f"• 📅 **Date:** {pref_date or 'Coordinator will arrange the earliest date'}\n"
                        f"• ⏰ **Session:** {pref_period}\n\n"
                        f"✅ Our coordinator will call {p_phone} to confirm the exact time. "
                        f"You can track the request with code `{request_code}` under **Treatment progress**."
                    )
                    quick_replies = ["Treatment progress", "More help"]
            except Exception as exc:
                logger.error("Error auto-committing conversational booking: %s", exc)
                response = build_booking_guidance_text(
                    is_authenticated=is_auth,
                    missing_fields=missing_fields,
                    current_intake=booking_intake,
                    specialty_name=spec_display,
                    lang=lang,
                )
                quick_replies = []
    elif care_pipeline.is_multi_specialty and workflow_status not in {
        "OUT_OF_SCOPE",
        "SOCIAL_REDIRECT",
        "CONFIRM_BOOKING_CONVERSATIONALLY",
        "SAFETY_REVIEW",
    }:
        p_dept = care_pipeline.primary_department
        s_dept = care_pipeline.secondary_departments[0] if care_pipeline.secondary_departments else "Khoa phối hợp"
        if is_emergency:
            response = (
                f"🚨 **CẢNH BÁO CẤP TÍNH & LỘ TRÌNH KHÁM PHÂN TẦNG (CARE PIPELINE):**\n\n"
                f"Dạ thưa bác, bác đang có đồng thời các triệu chứng ở cả **{p_dept}** và **{s_dept}**. "
                f"Tuy nhiên, theo nguyên tắc giải phẫu sinh tồn tối thượng trong y khoa, "
                f"**vị trí cơ quan sinh tồn ({p_dept}) luôn được ưu tiên khẩn cấp trước mọi mức độ đau ở các cơ quan ngoại vi ({s_dept})**!\n\n"
                f"Em xin vạch ra lộ trình xử trí tối ưu nhất cho bác:\n\n"
                f"• **📍 BƯỚC 1 (Xử trí cấp cứu khẩn cấp ngay): {p_dept} / Cấp Cứu (Gọi 115)**\n"
                f"  - Tình trạng ở cơ quan sinh tồn có dấu hiệu nguy kịch đe dọa sinh mạng. Bác cần gọi 115 hoặc đến ngay phòng Cấp cứu để được xử trí khẩn cấp, không chờ đợi lịch khám hẹn trước!\n\n"
                f"• **📍 BƯỚC 2 (Khám chuyên khoa kế tiếp sau khi ổn định): {s_dept}**\n"
                f"  - Sau khi các bác sĩ cấp cứu và chuyên khoa sinh tồn đã kiểm soát an toàn và tính mạng ổn định, bác sẽ được kết hợp thăm khám chuyên khoa {s_dept} để điều trị dứt điểm triệu chứng đau ngoại vi này.\n"
            )
            quick_replies = (
                ["Gọi Cấp cứu 115", f"Lộ trình {s_dept}", "Cần hỗ trợ khẩn"]
                if lang == "vi"
                else ["Call 115", f"Plan for {s_dept}", "Emergency Help"]
            )
        else:
            has_booking_action = bool(
                meta.get("is_booking_intent")
                or meta.get("booking_entities_found")
                or fac_pref
                or pref_date
                or any(
                    kw in query.lower()
                    for kw in [
                        "đặt lịch",
                        "phiếu hẹn",
                        "làm phiếu",
                        "hẹn khám",
                        "lên lịch",
                        "sáng mai",
                        "chiều mai",
                        "ngày mai",
                        "long biên",
                        "times city",
                        "riverside",
                    ]
                )
            )
            if has_booking_action:
                clean_pipeline = re.sub(
                    r"\n*👉\s*(?:Bác có muốn em hỗ trợ|Would you like me to).*$",
                    "",
                    care_pipeline.formatted_guidance,
                    flags=re.DOTALL | re.IGNORECASE,
                ).strip()

                booking_block = build_booking_guidance_text(
                    is_authenticated=is_auth,
                    missing_fields=missing_fields,
                    current_intake=booking_intake,
                    specialty_name=p_dept,
                    lang=lang,
                )
                response = f"{clean_pipeline}\n\n{booking_block}"
                quick_replies = (
                    ["Xác nhận gửi thông tin", f"Ưu tiên {s_dept}", "Đổi cơ sở", "Đổi ngày khám"]
                    if lang == "vi"
                    else ["Confirm & Submit", f"Prioritize {s_dept}", "Change Facility", "Change Date"]
                )
            else:
                response = care_pipeline.formatted_guidance
                quick_replies = (
                    [f"Đặt lịch {p_dept}", f"Khám {s_dept}", "Mô tả thêm triệu chứng"]
                    if lang == "vi"
                    else [f"Book {p_dept}", f"Visit {s_dept}", "More details"]
                )
    elif is_emergency:
        response = patient_guidance
    elif workflow_status == "HITL_AWAITING_CONFIRMATION":
        response = (
            "Dạ, cái này nằm ngoài phạm vi của em, em có thể giúp bác liên hệ với các bác sĩ có chuyên môn để tư vấn nhé."
            if lang == "vi"
            else "This procedure is beyond my scope. I can help connect you with our medical specialists for consultation."
        )
        quick_replies = ["Yêu cầu hỗ trợ", "Không"] if lang == "vi" else ["Request assistance", "No"]
    elif workflow_status == "HITL_ESCALATED_COORDINATOR":
        response = (
            "Dạ, em đã chuyển thông tin yêu cầu của bác tới role Điều phối viên y tế. "
            "Điều phối viên sẽ liên hệ với bác để kết nối các bác sĩ có chuyên môn tư vấn chi tiết về thủ thuật/phẫu thuật này nhé ạ!"
            if lang == "vi"
            else "I have forwarded your request to our Medical Coordinator. The coordinator will contact you shortly to connect with our specialists!"
        )
        quick_replies = (
            ["Để lại thông tin liên hệ", "Hỏi câu hỏi khác"]
            if lang == "vi"
            else ["Leave contact info", "Ask another question"]
        )
    elif workflow_status == "HITL_DECLINED_CONVERSATIONAL":
        response = (
            "Thế bác còn câu hỏi nào khác không? Ví dụ: triệu chứng, tìm bệnh viện,..."
            if lang == "vi"
            else "Do you have any other questions? For example: symptoms, find hospital, look up doctors,..."
        )
        quick_replies = (
            ["Mô tả triệu chứng", "Tìm bệnh viện", "Tra cứu bác sĩ"]
            if lang == "vi"
            else ["Describe symptoms", "Find hospital", "Look up doctors"]
        )
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
        is_direct_clinical_input = any(
            kw in query.lower()
            for kw in [
                "đau",
                "nhức",
                "mỏi",
                "khó chịu",
                "khớp",
                "ngón tay",
                "lưng",
                "gối",
                "đầu",
                "buồn nôn",
                "chóng mặt",
                "sốt",
            ]
        )
        has_nav_or_booking_keywords = any(
            kw in query.lower()
            for kw in [
                "bác sĩ",
                "bac si",
                "bệnh viện",
                "benh vien",
                "đặt lịch",
                "dat lich",
                "times city",
                "cơ sở",
                "co so",
                "chi nhánh",
                "các sĩ",
                "cac si",
            ]
        )
        if is_direct_clinical_input and not has_nav_or_booking_keywords and dept_context:
            symptom_loc = ""
            for kw in [
                "khớp ngón tay cái",
                "ngón tay cái",
                "ngón tay",
                "khớp ngón",
                "khớp gối",
                "đầu gối",
                "cổ vai gáy",
                "thắt lưng",
                "cổ tay",
                "khớp",
            ]:
                if kw in query.lower():
                    symptom_loc = f" ở {kw}"
                    break
            clinical_prefix = (
                (
                    f"Dạ, em đã ghi nhận triệu chứng của bác{symptom_loc}.\n"
                    f"Về chuyên khoa, bác nên thăm khám tại **Khoa {dept_context}** để bác sĩ kiểm tra và đưa ra chẩn đoán chính xác nhất.\n\n"
                )
                if lang == "vi"
                else (
                    f"I have noted your reported symptoms{symptom_loc}. Given your symptoms, an in-person evaluation at **{dept_context}** is recommended.\n\n"
                )
            )

        booking_suffix = ""
        if meta.get("is_booking_intent") or booking_intake.get("required"):
            booking_suffix = "\n\n" + build_booking_guidance_text(
                is_authenticated=is_auth,
                missing_fields=missing_fields,
                current_intake=booking_intake,
                specialty_name=spec_display,
                lang=lang,
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
            (
                "Dạ, Vinmec hiện có các **Gói khám sức khỏe tổng quát và lộ trình tầm soát chuyên sâu** "
                "(như Khám sức khỏe định kỳ, Tầm soát tim mạch, Tầm soát ung thư sớm, Gói thai sản/sinh nở...).\n\n"
                "Em đã tự động chuyển **Phiếu Đăng Ký Khám** ở khung bên cạnh sang chế độ **Gói Khám Bệnh**. "
                "Bác có thể tra cứu chi tiết danh mục gói, chi phí niêm yết và chọn gửi yêu cầu trực tiếp trên bảng bên cạnh nhé ạ!"
            )
            if lang == "vi"
            else (
                "Vinmec provides various comprehensive Health Checkup and Screening Packages. "
                "I have switched the Live Booking Panel on the right to **Health Packages** mode so you can view details and register directly!"
            )
        )
        quick_replies = (
            [
                "Gói khám tổng quát",
                "Tầm soát tim mạch",
                "Tầm soát ung thư",
                "Khám bác sĩ chuyên khoa",
            ]
            if lang == "vi"
            else ["Health checkup", "Cancer screening", "Specialist booking"]
        )
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
        and workflow_status
        not in {
            "PROBING_IN_PROGRESS",
            "VISIT_PURPOSE_CLARIFICATION",
            "OUT_OF_SCOPE",
            "SOCIAL_REDIRECT",
            "TRIAGED_READY_FOR_BOOKING",
        }
    ):
        has_specific_booking = bool(
            booking_intake.get("facility_preference")
            or booking_intake.get("preferred_date")
            or state.get("facility_preference")
            or state.get("preferred_date")
            or any(
                kw in query.lower()
                for kw in [
                    "tự chọn",
                    "tu chon",
                    "chọn giúp",
                    "đặt tôi",
                    "dat toi",
                    "ngày",
                    "vào ngày",
                    "times city",
                    "smart city",
                    "riverside",
                    "royal city",
                ]
            )
        )
        is_fac_ask, fac_reg = extract_facility_inquiry(query)
        if (is_fac_ask or meta.get("is_facility_inquiry")) and not is_emergency and not has_specific_booking:
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
                (
                    "\n\n📋 **Phiếu Hẹn Khám Bác Sĩ Chuyên Khoa:**\n"
                    "Em đã tự động trích xuất thông tin của bác vào phiếu ở khung bên cạnh"
                    + (
                        f" (**Bệnh nhân:** {booking_intake.get('patient_name')}, **Chuyên khoa:** {spec_display})."
                        if is_auth and booking_intake.get("patient_name")
                        else "."
                    )
                    + f" Bác vui lòng chọn cơ sở mong muốn tại {region_filter} và xác nhận trên phiếu bên cạnh nhé ạ!"
                )
                if lang == "vi"
                else (
                    "\n\n📋 **Appointment Request Form:**\n"
                    "I have pre-filled your details on the right panel. Please choose your preferred facility and confirm!"
                )
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
            quick_replies = (
                [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Smart City"]
                if lang == "vi"
                else ["Times City", "Smart City"]
            )
        elif (
            has_compound_question
            and v2_draft
            and len(v2_draft.strip()) > 30
            and not v2_draft.strip().startswith("Dạ, em đã điền")
        ):
            booking_cta = "\n\n" + build_booking_guidance_text(
                is_authenticated=is_auth,
                missing_fields=missing_fields,
                current_intake=booking_intake,
                specialty_name=spec_display,
                lang=lang,
            )
            response = v2_draft + booking_cta
            quick_replies = (
                [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Central Park"]
                if lang == "vi"
                else ["Times City", "Central Park"]
            )
        else:
            response = build_booking_guidance_text(
                is_authenticated=is_auth,
                missing_fields=missing_fields,
                current_intake=booking_intake,
                specialty_name=spec_display,
                lang=lang,
            )
            quick_replies = (
                [f"Khoa {spec_display}", "Cơ sở Times City", "Cơ sở Central Park"]
                if lang == "vi"
                else ["Times City", "Central Park"]
            )
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
                    title = doc.get("title") or ""
                    title_text = f" ({title}{exp_text})" if (title or exp_text) else ""
                    doctors_text += f"\n**{idx}. Dr. {doc['full_name']}**{title_text}\n"
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
                doctors_text = f"\n\n👨‍⚕️ **Bác sĩ chuyên khoa ({spec_display}):**\n"
                for idx, doc in enumerate(available_docs, 1):
                    exp = doc.get("years_of_experience", 0)
                    exp_text = f" - {exp} năm kinh nghiệm" if exp else ""
                    title = doc.get("title") or ""
                    title_text = f" ({title}{exp_text})" if (title or exp_text) else ""
                    doctors_text += f"\n**{idx}. {doc['full_name']}**{title_text}\n"
                    specialties = ", ".join(doc.get("specialties") or [])
                    if specialties:
                        doctors_text += f"   • Chuyên môn: {specialties}\n"
                    if doc.get("workplace"):
                        doctors_text += f"   • Nơi làm việc: {doc['workplace']}\n"
                    for slot in doc.get("available_slots", []):
                        if slot.get("verified"):
                            doctors_text += f"   • Lịch khám: `{slot['starts_at']}`\n"
                    if doc.get("source_url") and enable_citation:
                        doctors_text += f"   • [Hồ sơ bác sĩ Vinmec]({doc['source_url']})\n"
            if has_verified_slots:
                matched_facility_name = (
                    state.get("facility_preference")
                    or booking_intake.get("facility_preference")
                    or meta.get("facility_preference")
                )
                facility_location_text = ""
                if matched_facility_name and any(
                    k in str(matched_facility_name).lower()
                    for k in ["minh khai", "times city", "hai bà trưng", "hai ba trung"]
                ):
                    facility_location_text = "tại cơ sở **Bệnh viện Đa khoa Quốc tế Vinmec Times City** (458 Minh Khai, Hai Bà Trưng, Hà Nội) "
                elif matched_facility_name:
                    facility_location_text = f"tại cơ sở **{matched_facility_name}** "

                prefix = (
                    f"Dạ, em đã kiểm tra lịch khám còn trống {facility_location_text}thuộc **Khoa {spec_display}** trong {max_days} ngày tới:"
                    if lang == "vi"
                    else f"I found available appointments {facility_location_text}at **{spec_display}** for the next {max_days} days:"
                )
                quick_replies = []
            elif meta.get("is_doctor_inquiry"):
                prefix = (
                    (
                        "Dạ, bác hoàn toàn có thể tự chọn bác sĩ chuyên khoa phù hợp theo nguyện vọng của mình ạ!\n"
                        f"Dưới đây là danh sách các chuyên gia, bác sĩ hàng đầu tại **Khoa {spec_display}** của Vinmec để bác lựa chọn:"
                    )
                    if lang == "vi"
                    else (
                        f"Yes, you can certainly choose your preferred specialist! Here are the specialists for **{spec_display}** at Vinmec:"
                    )
                )
                quick_replies = (
                    [f"Khoa {spec_display}", "Cơ sở Riverside", "Cơ sở Times City"]
                    if lang == "vi"
                    else ["Riverside", "Times City"]
                )
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
            if lang == "vi" and not has_verified_slots and available_docs:
                prefix = "Bác sĩ phù hợp có hồ sơ nguồn: " + prefix
            if meta.get("is_doctor_inquiry"):
                form_hint = (
                    (
                        "\n\n📋 *Bác có thể chọn bác sĩ trực tiếp trên danh sách thả xuống ở Phiếu Đăng Ký Khám bên cạnh, hoặc nhắn tên bác sĩ mong muốn để em cập nhật vào phiếu cho bác nhé ạ!*"
                    )
                    if lang == "vi"
                    else (
                        "\n\n📋 *You can select your doctor directly from the dropdown on the Appointment Form, or let me know your preference!*"
                    )
                )
            else:
                form_hint = (
                    (
                        "\n\n📋 *Em đã tự động điền sẵn thông tin từ tài khoản của bác vào Phiếu Đăng Ký Khám ở khung bên cạnh. Bác vui lòng kiểm tra lại và xác nhận nhé!*"
                        if is_auth
                        else "\n\n📋 *Bác có thể nhắn Họ tên, SĐT và Ngày sinh để em tự động điền giúp bác, hoặc tự điền vào Phiếu Khám ở khung bên cạnh nhé ạ!*"
                    )
                    if lang == "vi"
                    else (
                        "\n\n📋 *I have pre-filled the Appointment Form on the right panel with your profile. Please review and confirm!*"
                        if is_auth
                        else "\n\n📋 *You can provide your name, phone, and DOB for auto-fill, or type directly into the form on the right panel!*"
                    )
                )
            response = f"{prefix}{doctors_text}{form_hint}"
        else:
            if meta.get("data_unavailable"):
                from src.medical_assistant.config import get_settings

                hotline_num = getattr(get_settings(), "hospital_hotline", "1900 232 389")
                if lang == "vi":
                    response = (
                        f"Dạ, hệ thống tra cứu lịch trực tuyến của bệnh viện hiện đang tạm thời gián đoạn kết nối "
                        f"nên em chưa thể tra cứu thông tin lịch khám trực tiếp lúc này. "
                        f"Để kiểm tra lịch hẹn nhanh nhất, bác có thể liên hệ trực tiếp Tổng đài {hotline_num} "
                        "hoặc điền thông tin vào Phiếu Đăng Ký Khám bên cạnh để điều phối viên y tế liên hệ hỗ trợ bác nhé ạ!"
                    )
                    quick_replies = ["Để lại thông tin tư vấn", f"Gọi hotline {hotline_num}"]
                else:
                    response = (
                        f"Our online schedule system is temporarily unavailable. "
                        f"Please contact our hotline at {hotline_num} or complete the Appointment Form on the side "
                        "for our medical coordinator to assist you directly!"
                    )
                    quick_replies = ["Leave contact info", f"Call hotline {hotline_num}"]
            elif meta.get("is_doctor_inquiry"):
                from src.medical_assistant.config import get_settings

                hotline_num = getattr(get_settings(), "hospital_hotline", "1900 232 389")
                if available_docs:
                    doc_names = ", ".join(f"**{d.get('full_name')}**" for d in available_docs[:3] if d.get("full_name"))
                    response = (
                        (
                            f"Dạ, tại chuyên khoa **{spec_display}**, hiện có các bác sĩ: {doc_names}. "
                            "Bác có thể chọn trực tiếp bác sĩ mong muốn tại **Phiếu Đăng Ký Khám** ở khung bên cạnh, "
                            "hoặc để điều phối viên y tế sắp xếp lịch hẹn phù hợp nhất nhé ạ!"
                        )
                        if lang == "vi"
                        else (
                            f"We currently have doctors available for **{spec_display}**: {doc_names}. "
                            "Please select your doctor on the Appointment Form or let our coordinator assist you!"
                        )
                    )
                else:
                    response = (
                        (
                            f"Dạ, hiện tại hệ thống chưa tìm thấy thông tin bác sĩ còn lịch trống trực tiếp cho chuyên khoa **{spec_display}** tại cơ sở đã chọn. "
                            f"Bác có thể để lại thông tin tại **Phiếu Đăng Ký Khám** bên cạnh để điều phối viên y tế kiểm tra và bố trí bác sĩ cho bác, "
                            f"hoặc liên hệ Tổng đài {hotline_num} để được hỗ trợ trực tiếp nhé ạ!"
                        )
                        if lang == "vi"
                        else (
                            f"Currently, no open slots or available doctors were found for **{spec_display}** at the selected facility. "
                            f"Please submit the Appointment Form or contact hotline {hotline_num} for direct support!"
                        )
                    )
                quick_replies = (
                    ["Để điều phối viên xếp", "Chọn cơ sở khác", f"Gọi hotline {hotline_num}"]
                    if lang == "vi"
                    else ["Coordinator arrangement", "Other facility", f"Call {hotline_num}"]
                )
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
            if care_pipeline.is_multi_specialty:
                response = care_pipeline.formatted_guidance
                p_dept = care_pipeline.primary_department
                s_dept = (
                    care_pipeline.secondary_departments[0] if care_pipeline.secondary_departments else "Khoa phối hợp"
                )
                quick_replies = (
                    [f"Đặt lịch {p_dept}", f"Khám {s_dept}", "Mô tả thêm triệu chứng"]
                    if lang == "vi"
                    else [f"Book {p_dept}", f"Visit {s_dept}", "More details"]
                )
            else:
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
            has_symptoms = bool(
                chief
                or clinical_facts.get("positive_facts")
                or clinical_facts.get("complaints")
                or state.get("collected_details")
                or state.get("ats_level")
            )
            if lang == "en" and chief:
                response = f"I've noted your {chief.replace('_', ' ')}. {clarification or v2_draft}"
            elif lang == "vi":
                detail = clarification or v2_draft or ""
                if has_symptoms and not detail.startswith("Dạ, em đã ghi nhận"):
                    response = f"Dạ, em đã ghi nhận triệu chứng của bác.\n\n{detail}"
                else:
                    response = detail
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
    elif workflow_status in {"OUT_OF_SCOPE", "SOCIAL_REDIRECT"}:
        response = (
            "Dạ, em là Trợ lý AI Y tế của Vinmec. Em chỉ có thể hỗ trợ các thông tin về sức khỏe, chuyên khoa và đặt lịch khám bệnh. "
            "Bác vui lòng chia sẻ tình trạng sức khỏe hoặc nhu cầu khám để em hỗ trợ nhé ạ!"
            if lang == "vi"
            else "I am the AI Medical Assistant. I can only assist with healthcare navigation, specialties, and appointments. Please share your symptoms or medical questions so I can assist you!"
        )
        quick_replies = (
            [
                "Tư vấn triệu chứng",
                "Bảng giá khám bệnh",
                "Đặt lịch khám bác sĩ",
            ]
            if lang == "vi"
            else ["Check symptoms", "Pricing", "Book doctor"]
        )
    elif workflow_status == "VISIT_PURPOSE_CLARIFICATION":
        if v2_draft and len(v2_draft.strip()) > 10:
            response = v2_draft
        else:
            response = (
                "Dạ, để em có thể tư vấn chuyên khoa chính xác và gợi ý cơ sở y tế phù hợp nhất, "
                "bác vui lòng chia sẻ thêm: Hiện tại bác đang cảm thấy khó chịu hoặc có triệu chứng gì ở đâu, "
                "hoặc bác đang có nhu cầu khám chuyên khoa nào (ví dụ: Tiêu hóa, Tim mạch, Cơ xương khớp hay Khám sức khỏe tổng quát) ạ?"
                if lang == "vi"
                else "To help guide you to the right specialty and facility, could you please share your symptoms or the specialty you wish to consult (e.g., Gastroenterology, Cardiology, Orthopedics, or General Health Screening)?"
            )
        quick_replies = (
            ["Khám Tiêu hóa", "Khám Tim mạch", "Khám Cơ xương khớp", "Khám sức khỏe tổng quát"]
            if lang == "vi"
            else ["Gastroenterology", "Cardiology", "Orthopedics", "General Checkup"]
        )
    else:
        response = v2_draft if v2_draft else "Xin lỗi, tôi không thể xử lý yêu cầu của bạn."

    patient_profile = state.get("patient_profile") or {}
    display_name = (patient_profile.get("name") or "").strip()
    if display_name and workflow_status != "SECURITY_BLOCKED":
        name_parts = display_name.split()
        first_name = name_parts[-1] if name_parts else display_name
        has_name_in_response = (
            display_name.lower() in response.lower()
            or (first_name and f"bác {first_name.lower()}" in response.lower())
            or (first_name and f"anh {first_name.lower()}" in response.lower())
            or (first_name and f"chị {first_name.lower()}" in response.lower())
        )
        already_has_greeting = bool(re.match(r"^(?:dạ|chào|xin chào|kính chào|hello|hi)\b", response.strip().lower()))
        if not has_name_in_response and not already_has_greeting:
            response = (f"Dạ {display_name},\n\n" if lang == "vi" else f"Hello {display_name},\n\n") + response

    clinical_facts = state.get("clinical_facts") or {}
    has_clinical_context = bool(
        state.get("is_emergency")
        or state.get("ats_level")
        or state.get("suggested_department_name")
        or clinical_facts.get("chief_complaint")
        or clinical_facts.get("positive_facts")
        or state.get("collected_details")
        or workflow_status
        in {
            "GUARDRAIL_MEDICATION",
            "GUARDRAIL_DIAGNOSIS",
            "TRIAGED_READY_FOR_BOOKING",
            "FACILITY_DOCTORS",
            "DEPARTMENT_INFO",
        }
    ) and workflow_status not in {
        "SECURITY_BLOCKED",
        "SOCIAL_REDIRECT",
        "OUT_OF_SCOPE",
        "FAQ_ANSWERED",
        "LANGUAGE_CHANGED",
    }

    # Ca ưu tiên khám trong ngày (ATS 3) được hẹn sau → dặn dấu hiệu cần gọi cấp cứu khi chờ.
    safety_net = (
        get_same_day_safety_net(lang)
        if has_clinical_context and not is_emergency and state.get("ats_level") == 3
        else ""
    )
    full_response = response + safety_net + (disclaimer if has_clinical_context else "")

    # TẦNG 3: Post-Generation Medical Safety Validators (SAF-01 & SAF-02)
    from src.medical_assistant.domain.security.guardrail_validators import MedicalSafetyValidators

    med_val1 = MedicalSafetyValidators.validate_no_prescription(full_response)
    med_val2 = MedicalSafetyValidators.validate_no_definitive_diagnosis(med_val1.sanitized_content)
    full_response = med_val2.sanitized_content

    # TẦNG 3: Microsoft Presidio DLP & Medical Anonymizer
    from src.medical_assistant.domain.security.presidio_dlp_service import get_presidio_dlp_service

    presidio_svc = get_presidio_dlp_service()
    p_phone_clean = str(p_phone).replace(" ", "") if p_phone else None
    presidio_scan = presidio_svc.sanitize(
        full_response,
        user_id=state.get("user_id"),
        allowed_phone=p_phone_clean,
    )
    full_response = presidio_scan.sanitized_text

    from src.medical_assistant.domain.security.dlp_service import get_dlp_service

    dlp_service = get_dlp_service()
    dlp_scan = dlp_service.sanitize(
        full_response, allowed_user_id=state.get("user_id"), allowed_user_phone=p_phone_clean
    )
    full_response = dlp_scan.sanitized_text

    from src.medical_assistant.domain.token_counter import get_token_counter

    token_counter = get_token_counter()
    llm_fallback = bool(meta.get("llm_invoked")) and meta.get("llm_succeeded") is False
    zero_token = (
        bool(meta.get("tokens_saved"))
        or llm_fallback
        or (workflow_status == "VISIT_PURPOSE_CLARIFICATION" and not meta.get("describe_more_requested"))
        or workflow_status
        in {"SECURITY_BLOCKED", "FAQ_ANSWERED", "SOCIAL_REDIRECT", "OUT_OF_SCOPE", "LANGUAGE_CHANGED"}
    )
    token_metrics = token_counter.calculate_turn_metrics(
        state.get("query") or "", full_response, " ".join(state.get("collected_details") or []), zero_token
    )
    if llm_fallback:
        token_metrics["model"] = "fallback-rule"
        token_metrics["execution_mode"] = "llm_fallback_rule"
    from src.medical_assistant.infrastructure.llm import llm_usage_sink

    token_counter.apply_provider_usage(token_metrics, llm_usage_sink.get())
    meta["token_usage"] = token_metrics
    meta["quick_replies"] = quick_replies
    meta["booking_intake"] = None if workflow_status in {"FAQ_ANSWERED", "SECURITY_BLOCKED"} else booking_intake
    meta["dlp_leakage_detected"] = dlp_scan.has_leakage or presidio_scan.has_leakage

    # HOOK 6: on_agent_finish (Ghi nhận Telemetry chi phí & tài nguyên vào Supabase)
    from src.medical_assistant.domain.middleware_pipeline import get_middleware_pipeline

    middleware = get_middleware_pipeline()
    session_id = str(state.get("booking_id") or state.get("thread_id") or "session_default")
    turn_idx = int(state.get("probing_turn") or 1)
    prompt_tok = int(token_metrics.get("prompt_tokens") or 0)
    compl_tok = int(token_metrics.get("completion_tokens") or 0)
    cost_val = float(token_metrics.get("estimated_cost_usd") or token_metrics.get("cost_usd") or 0.0)
    latency_val = float(meta.get("elapsed_ms") or 0.0)

    telemetry_summary = middleware.execute_hook_6_on_finish(
        session_id=session_id,
        turn_index=turn_idx,
        prompt_tokens=prompt_tok,
        completion_tokens=compl_tok,
        latency_ms=latency_val,
        cost_usd=cost_val,
        workflow_status=workflow_status,
        metadata={"model": token_metrics.get("model")},
    )
    meta["telemetry"] = telemetry_summary

    import json

    llm_was_invoked = bool(meta.get("llm_invoked"))
    actual_llm_succeeded = meta.get("llm_succeeded") if llm_was_invoked else None
    actual_fallback_used = bool(meta.get("fallback_used") or llm_fallback) if llm_was_invoked else False

    structured_telemetry = {
        "route": meta.get("intent_route")
        or meta.get("route")
        or ("chitchat" if workflow_status == "SOCIAL_REDIRECT" else "clinical"),
        "workflow_status": workflow_status,
        "action": meta.get("action") or meta.get("proposed_action"),
        "tools_called": meta.get("tools_called") or [],
        "llm_succeeded": actual_llm_succeeded,
        "fallback_used": actual_fallback_used,
        "data_unavailable": bool(meta.get("data_unavailable", False)),
        "data_unavailable_reason": meta.get("data_unavailable_reason"),
        "latency_ms": latency_val,
        "tokens": {
            "prompt": prompt_tok,
            "completion": compl_tok,
            "total": prompt_tok + compl_tok,
        },
    }
    logger.info("TURN_TELEMETRY: %s", json.dumps(structured_telemetry, ensure_ascii=False))
    meta["structured_telemetry"] = structured_telemetry

    # Cập nhật và lưu giữ lịch sử hội thoại với cơ chế Compaction + SOAP Notes
    from src.medical_assistant.domain.compaction_service import get_compaction_service

    history = list(state.get("messages") or [])
    user_q = state.get("query") or ""
    if user_q:
        history.append({"role": "user", "content": user_q})
    history.append({"role": "assistant", "content": full_response})

    compaction_res = get_compaction_service().compact_conversation(history, state, recent_window_size=4)
    compacted_history = compaction_res["recent_messages"]
    durable_soap_note = compaction_res["durable_soap_note"]

    meta["quick_replies"] = quick_replies

    return {
        "response": full_response,
        "quick_replies": quick_replies,
        "disclaimer": disclaimer,
        "token_usage": token_metrics,
        "metadata": meta,
        "messages": compacted_history,
        "durable_soap_note": durable_soap_note,
        "last_assistant_response": full_response,
        "booking_intake": booking_intake,
    }
