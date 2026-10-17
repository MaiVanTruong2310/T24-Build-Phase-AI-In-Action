"""Deterministic lightweight routing before Staff agent tool execution."""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.agents.staff_agent_planner import decompose_and_evaluate_tasks, plan_staff_goal
from src.agents.staff_guardrails import _normalize_staff_input, staff_input_refusal

_CHITCHAT = {
    "hi",
    "hello",
    "xin chao",
    "chao",
    "chao ban",
    "chao tro ly",
    "cam on",
    "cam on ban",
    "ban khoe khong",
    "how are you",
    "good morning",
    "thanks",
    "thank you",
    "thank you very much",
}
_COMPLEX_TERMS = (
    "so sanh",
    "tong hop",
    "dong thoi",
    "va cho biet",
    "ket hop",
    "bao nhieu",
    "thong ke",
    "danh sach",
    "phan tich",
)
_AVAILABILITY_TERMS = ("lich trong", "con lich", "lich bac si", "availability", "available slot")
_DOCTOR_TERMS = ("bac si", "doctor", "physician", "chuyen khoa", "specialty")
_PATIENT_TERMS = ("benh nhan", "ho so", "patient", "medical record")
_BOOKING_TERMS = ("booking", "dat kham", "lich kham", "appointment", "tham kham", "luot kham")
_BOOKING_PHRASE_PATTERN = re.compile(r"\blich\b.{0,32}\bkham\b")
_SCHEDULE_KEYWORD_PATTERN = re.compile(r"\blich\b(?!\s+su\b)")
_CASE_TERMS = (
    "case",
    "dieu phoi",
    "sla",
    "ho tro",
    "dang duoc tu van",
    "agent dang tu van",
    "agent tu van",
    "duyet ca",
    "phieu kham",
    "consultation form",
)
_CLAIM_CASE_TERMS = ("nhan ca", "tiep nhan", "claim", "handle", "duyet ca", "approve case")
_EMERGENCY_CASE_TERMS = ("cap cuu", "emergency", "is_emergency", "nguy cap")
_INTAKE_CASE_TERMS = ("ca tiep nhan", "cac ca", "danh sach ca", "ca dieu phoi", "ca cua")
_PROCEDURE_TERMS = ("quy trinh", "sop", "procedure")
_TIME_TERMS = (
    "hom nay",
    "hom qua",
    "hom kia",
    "ngay mai",
    "tuan nay",
    "tuan toi",
    "tuan sau",
    "tuan truoc",
    "thang nay",
    "thang sau",
    "thang truoc",
    "tieng toi",
    "from",
    "today",
    "yesterday",
    "tomorrow",
    "this week",
    "next week",
)
_DATE_PATTERN = re.compile(r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/20\d{2})\b")
_SPECIALTY_TERMS = (
    "tim mach",
    "nhi khoa",
    "noi khoa",
    "ngoai khoa",
    "san khoa",
    "mat",
    "da lieu",
    "than kinh",
    "tai mui hong",
    "ung buou",
    "co xuong khop",
    "khoa ",
    "chuyen khoa ",
)


@dataclass(frozen=True)
class StaffRoute:
    category: str
    reason_code: str
    tool_names: tuple[str, ...] = ()
    reply: str | None = None
    language: str = "vi"
    tasks: list[dict[str, object]] | None = None
    goal_plan: dict[str, object] | None = None

    @property
    def task_domains(self) -> list[str]:
        return [str(task["domain"]) for task in self.tasks or []]


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_booking_phrase(text: str) -> bool:
    return _BOOKING_PHRASE_PATTERN.search(text) is not None


def _has_schedule_keyword(text: str) -> bool:
    return _SCHEDULE_KEYWORD_PATTERN.search(text) is not None


def has_explicit_staff_lookup_intent(message: str) -> bool:
    normalized = _normalize_staff_input(message)
    return (
        _has_any(
            normalized,
            (
                *_PATIENT_TERMS,
                *_BOOKING_TERMS,
                *_CASE_TERMS,
                *_EMERGENCY_CASE_TERMS,
                *_INTAKE_CASE_TERMS,
                *_DOCTOR_TERMS,
                *_PROCEDURE_TERMS,
            ),
        )
        or _has_any(normalized, _AVAILABILITY_TERMS)
        or _has_booking_phrase(normalized)
        or _has_schedule_keyword(normalized)
    )


def _chitchat_reply(text: str, language: str) -> str:
    if language == "en":
        return "Hello! I can help with staff lookups for patients, bookings, doctors, schedules, and cases."
    if text in {"cam on", "cam on ban"}:
        return "Không có gì. Tôi có thể hỗ trợ tra cứu thông tin vận hành cho staff."
    return "Xin chào! Tôi có thể hỗ trợ staff tra cứu bệnh nhân, booking, bác sĩ, lịch khám và case."


def route_staff_request(message: str, context: str = "", *, safety_checked: bool = False) -> StaffRoute:
    """Classify safe input and select a narrow tool set without database access."""
    normalized = _normalize_staff_input(message)
    has_current_domain = has_explicit_staff_lookup_intent(normalized)
    routing_text = normalized if has_current_domain else _normalize_staff_input(f"{context}\n{message}")
    language = (
        "en" if any(term in normalized for term in ("in english", "english please", "reply in english")) else "vi"
    )
    chitchat_text = normalized
    for language_hint in (
        "reply in english please",
        "in english please",
        "english please",
        "reply in english",
        "in english",
        "bang tieng anh",
        "tra loi tieng anh",
    ):
        chitchat_text = chitchat_text.replace(language_hint, " ").strip(" ,.!?")
    chitchat_text = re.sub(r"\s+(?:em|emd|anh|chi|ban|tro ly)(?:\s+(?:nhe|nha))?$", "", chitchat_text).strip()

    if chitchat_text in _CHITCHAT:
        return StaffRoute("chitchat", "smalltalk", reply=_chitchat_reply(chitchat_text, language), language=language)
    if refusal := staff_input_refusal(routing_text, safety_checked=safety_checked):
        return StaffRoute("unsupported", "outside_staff_scope", reply=refusal, language=language)

    is_availability = _has_any(routing_text, _AVAILABILITY_TERMS)
    has_patient = _has_any(routing_text, _PATIENT_TERMS)
    has_booking = (
        _has_any(routing_text, _BOOKING_TERMS)
        or _has_booking_phrase(routing_text)
        or (_has_schedule_keyword(routing_text) and not is_availability)
    )
    has_doctor = _has_any(routing_text, _DOCTOR_TERMS)
    has_emergency_cases = _has_any(routing_text, _EMERGENCY_CASE_TERMS)
    has_case = _has_any(routing_text, _CASE_TERMS) or has_emergency_cases
    has_agent_consultation = _has_any(
        routing_text, ("dang duoc tu van", "agent dang tu van", "agent tu van", "tro ly dang tu van")
    )
    has_submitted_exam_forms = _has_any(routing_text, ("phieu kham", "consultation form", "exam form"))
    has_case_claim = has_case and _has_any(routing_text, _CLAIM_CASE_TERMS)
    has_intake_cases = _has_any(routing_text, _INTAKE_CASE_TERMS)
    has_today = _has_any(routing_text, ("hom nay", "today"))
    has_procedure = _has_any(routing_text, _PROCEDURE_TERMS)
    has_case_booking = has_case and has_booking and _has_any(routing_text, ("tao", "dat", "book", "chot", "xep"))

    if has_submitted_exam_forms:
        return StaffRoute(
            "simple",
            "submitted_exam_form_case_lookup",
            ("search_staff_cases", "get_staff_case"),
            language=language,
            tasks=[
                {
                    "id": "coordination_cases",
                    "domain": "coordination_cases",
                    "depends_on": [],
                    "filters": {"submitted_exam_forms": True},
                }
            ],
        )

    if has_case_claim and has_case_booking:
        return StaffRoute(
            "simple",
            "claim_case_before_booking",
            ("search_staff_cases", "get_staff_case", "prepare_case_claim"),
            language=language,
            tasks=[
                {
                    "id": "coordination_cases",
                    "domain": "coordination_cases",
                    "depends_on": [],
                    "filters": {"continue_to_booking": True},
                }
            ],
        )

    if has_intake_cases and not (has_patient or has_booking or has_case):
        return StaffRoute(
            "ambiguous",
            "intake_case_type_required",
            reply=(
                "Bạn muốn tra ca điều phối/HITL được tạo hôm nay, hay booking/lượt khám hôm nay? "
                "Vui lòng chọn một loại để tôi tra đúng dữ liệu."
            ),
            language=language,
        )

    if is_availability:
        has_specialty = _has_any(routing_text, _SPECIALTY_TERMS) or _has_named_doctor(routing_text)
        has_date = _has_any(routing_text, _TIME_TERMS) or _DATE_PATTERN.search(routing_text) is not None
        if not has_specialty and not has_date:
            return StaffRoute(
                "ambiguous",
                "availability_missing_specialty_and_time",
                reply="Bạn muốn tra lịch cho bác sĩ hoặc chuyên khoa nào, và trong ngày/khoảng ngày nào?",
                language=language,
            )
        if not has_specialty:
            return StaffRoute(
                "ambiguous",
                "availability_missing_doctor_or_specialty",
                reply="Bạn vui lòng cho biết tên bác sĩ hoặc chuyên khoa cần tra cứu.",
                language=language,
            )
        if not has_date:
            return StaffRoute(
                "ambiguous",
                "availability_missing_time",
                reply="Bạn muốn tra lịch trong ngày hoặc khoảng ngày nào?",
                language=language,
            )

    tool_names: list[str] = []
    if has_patient:
        tool_names.extend(("search_staff_patients", "get_staff_patient_profile"))
    if has_booking:
        tool_names.extend(("search_staff_bookings", "get_staff_booking"))
        if _has_any(routing_text, ("duyet", "tu choi", "approve", "reject")):
            tool_names.append("prepare_booking_review")
    if has_case or has_intake_cases:
        tool_names.extend(("search_staff_cases", "get_staff_case"))
    if has_case_claim:
        tool_names.append("prepare_case_claim")
    if has_case_booking:
        tool_names.extend(("search_staff_availability", "prepare_case_booking"))
    if is_availability:
        tool_names.append("search_staff_availability")
    elif has_doctor:
        tool_names.append("search_staff_doctors")
    if has_procedure:
        tool_names.append("search_approved_staff_procedures")

    if not tool_names and not has_patient:
        tool_names.append("query_staff_operations")
    tool_names = list(dict.fromkeys(tool_names))

    intent_groups = sum(
        (has_patient, has_booking, has_case or has_intake_cases, is_availability or has_doctor, has_procedure)
    )
    domains = [
        domain
        for active, domain in (
            (has_patient, "patient_profile"),
            (has_booking, "bookings"),
            (
                (has_intake_cases or has_case) and has_today,
                "today_coordination_cases",
            ),
            (
                (has_case or has_intake_cases) and not has_today,
                "coordination_cases",
            ),
            (is_availability, "availability"),
            (has_doctor and not is_availability, "doctors"),
            (has_procedure, "procedures"),
        )
        if active
    ]
    booking_date = _booking_date_filter(routing_text, current_text=normalized) if has_booking else None
    if (
        has_booking
        and _is_booking_creation_request(normalized)
        and booking_date is None
        and not _DATE_PATTERN.search(normalized)
    ):
        return StaffRoute(
            "ambiguous",
            "booking_creation_period_required",
            reply="Bạn muốn tra các booking mới được tạo trong ngày hoặc khoảng thời gian nào?",
            language=language,
        )
    if len(domains) > 4:
        return StaffRoute(
            "unsupported",
            "too_many_lookup_tasks",
            reply="Yêu cầu có quá nhiều phần tra cứu cùng lúc. Vui lòng chia thành tối đa bốn tác vụ.",
            language=language,
        )
    visit_profile_flow = (
        has_patient
        and has_booking
        and _has_any(routing_text, ("benh nhan den tham kham", "benh nhan tham kham", "den tham kham", "den kham"))
        and has_today
    )
    explicitly_related = visit_profile_flow or _has_any(
        routing_text,
        (
            "cua nguoi nay",
            "cua benh nhan nay",
            "cua benh nhan a",
            "cua booking nay",
            "booking cua benh nhan",
            "case cua benh nhan",
            "lien quan den cung",
            "cung benh nhan",
        ),
    )
    if intent_groups > 1 and not explicitly_related:
        plan = decompose_and_evaluate_tasks(routing_text, context)
        if plan.is_multi_intent and plan.all_executable:
            tasks = [task.model_dump() for task in plan.tasks]
            booking_task = next((task for task in tasks if task.get("domain") == "bookings"), None)
            if booking_task and booking_date:
                booking_task["filters"] = {**booking_task.get("filters", {}), **booking_date}
            return StaffRoute(
                "complex",
                "multi_intent_auto_execute",
                tuple(tool_names),
                language=language,
                tasks=tasks,
            )
        if has_intake_cases and has_patient:
            reply = (
                "Bạn muốn tra cả hồ sơ của một bệnh nhân cụ thể và danh sách ca điều phối/HITL được tạo hôm nay "
                "chứ (không phải booking/lượt khám)? Nếu đúng, hãy xác nhận; nếu ‘ca tiếp nhận’ có nghĩa khác, "
                "vui lòng nói rõ. Tôi sẽ cần tên hoặc mã bệnh nhân để tra hồ sơ."
            )
        else:
            labels = {
                "patient_profile": "hồ sơ bệnh nhân",
                "bookings": "booking/lịch khám",
                "coordination_cases": "ca điều phối/HITL",
                "availability": "lịch trống",
                "doctors": "bác sĩ/chuyên khoa",
                "procedures": "quy trình nội bộ",
            }
            summary = " và ".join(labels[domain] for domain in domains)
            reply = f"Tôi hiểu bạn muốn tra {summary}. Bạn xác nhận thực hiện các phần này chứ?"
        return StaffRoute(
            "confirmation",
            "independent_tasks_need_scope_confirmation",
            reply=reply,
            language=language,
            tasks=_build_tasks(
                domains,
                emergency_only=has_emergency_cases,
                agent_consulting=has_agent_consultation,
                booking_date=booking_date,
            ),
        )
    needs_detail = has_patient and _has_any(routing_text, ("ho so", "thong tin", "profile", "chi tiet"))
    needs_detail = needs_detail or (
        has_patient and _has_any(routing_text, ("nguy cap", "cap cuu", "triage", "assessment", "danh gia"))
    )
    needs_detail = needs_detail or (has_booking and _has_any(routing_text, ("chi tiet", "detail")))
    needs_detail = needs_detail or (has_case and _has_any(routing_text, ("chi tiet", "detail")))
    complex_request = intent_groups > 1 or needs_detail or _has_any(routing_text, _COMPLEX_TERMS)
    return StaffRoute(
        "complex" if complex_request else "simple",
        "multi_tool_or_reasoning" if complex_request else "single_lookup",
        tuple(tool_names),
        language=language,
        tasks=_build_tasks(
            domains,
            visit_profile_flow=visit_profile_flow,
            emergency_only=has_emergency_cases,
            agent_consulting=has_agent_consultation,
            booking_date=booking_date,
        ),
    )


async def route_staff_request_with_planner(
    message: str, context: str = "", llm=None, *, route: StaffRoute | None = None
) -> StaffRoute:
    """Attach a validated goal plan to eligible reads without widening routing."""
    route = route or route_staff_request(message, context)
    if route.category not in {"simple", "complex"} or any(
        name in route.tool_names for name in ("prepare_booking_review", "prepare_case_claim", "prepare_case_booking")
    ):
        return route
    if any(
        task.get("domain") == "bookings"
        and task.get("filters", {}).get("booking_date_field") in {"starts_at", "created_at"}
        and (task.get("filters", {}).get("booking_date") or task.get("filters", {}).get("booking_date_from"))
        for task in route.tasks or []
    ):
        return route
    if any(task.get("filters", {}).get("agent_consulting") for task in route.tasks or []):
        return route
    domains = route.task_domains
    if not domains and "query_staff_operations" in route.tool_names:
        domains = ["staff_operations"]
    if not domains:
        return route

    plan = await plan_staff_goal(message, domains, llm, context=context)
    if plan is None:
        return route
    if plan.clarification_question or any(not task.is_executable for task in plan.tasks):
        question = plan.clarification_question or next(
            (task.missing_reason for task in plan.tasks if not task.is_executable), None
        )
        return StaffRoute(
            "ambiguous",
            "goal_clarification",
            reply=question or "Bạn muốn đạt kết quả gì từ yêu cầu tra cứu này?",
            language=route.language,
            tasks=route.tasks,
        )
    return StaffRoute(
        route.category,
        route.reason_code,
        route.tool_names,
        route.reply,
        route.language,
        route.tasks,
        {
            "goal": plan.goal,
            "completion_criteria": plan.completion_criteria,
            "domains": domains,
        },
    )


def _build_tasks(
    domains: list[str],
    *,
    visit_profile_flow: bool = False,
    emergency_only: bool = False,
    agent_consulting: bool = False,
    booking_date: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    tasks = [{"id": domain, "domain": domain, "depends_on": []} for domain in domains]
    case_task = next((task for task in tasks if "coordination_cases" in str(task["domain"])), None)
    if case_task:
        filters = {}
        if case_task["domain"] == "today_coordination_cases":
            filters["received_today"] = True
        if emergency_only:
            filters["emergency_only"] = True
        if agent_consulting:
            filters["agent_consulting"] = True
        if filters:
            case_task["filters"] = filters
    booking_task = next((task for task in tasks if task["domain"] == "bookings"), None)
    if booking_task and booking_date:
        booking_task["filters"] = {**(booking_task.get("filters") or {}), **booking_date}
    if visit_profile_flow:
        bookings = next(task for task in tasks if task["domain"] == "bookings")
        profile = next(task for task in tasks if task["domain"] == "patient_profile")
        profile["depends_on"] = [bookings["id"]]
        tasks.remove(bookings)
        tasks.insert(0, bookings)
    return tasks


def _booking_date_filter(text: str, *, current_text: str = "", today: date | None = None) -> dict[str, str] | None:
    """Resolve relative booking dates deterministically in Vietnam local time."""
    current_has_relative_date = _has_any(
        current_text,
        (
            "hom nay",
            "today",
            "ngay mai",
            "tomorrow",
            "hom qua",
            "yesterday",
            "hom kia",
            "day before yesterday",
            "tuan nay",
            "this week",
            "tuan toi",
            "tuan sau",
            "next week",
            "tuan truoc",
            "last week",
            "thang nay",
            "this month",
            "thang sau",
            "next month",
            "thang truoc",
            "last month",
        ),
    )
    date_text = current_text if current_has_relative_date else text
    local_today = today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    if _has_any(date_text, ("ngay mai", "tomorrow")):
        selected = local_today + timedelta(days=1)
        end = selected + timedelta(days=1)
    elif _has_any(date_text, ("hom kia", "day before yesterday")):
        selected = local_today - timedelta(days=2)
        end = selected + timedelta(days=1)
    elif _has_any(date_text, ("tuan toi", "tuan sau", "next week")):
        selected = local_today + timedelta(days=7 - local_today.weekday())
        end = selected + timedelta(days=7)
    elif _has_any(date_text, ("tuan truoc", "last week")):
        selected = local_today - timedelta(days=local_today.weekday() + 7)
        end = selected + timedelta(days=7)
    elif _has_any(date_text, ("tuan nay", "this week")):
        selected = local_today - timedelta(days=local_today.weekday())
        end = selected + timedelta(days=7)
    elif _has_any(date_text, ("thang nay", "this month")):
        selected = local_today.replace(day=1)
        end = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
    elif _has_any(date_text, ("thang sau", "next month")):
        selected = local_today.replace(day=1)
        selected = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
    elif _has_any(date_text, ("thang truoc", "last month")):
        end = local_today.replace(day=1)
        selected = (end - timedelta(days=1)).replace(day=1)
    elif _has_any(date_text, ("hom qua", "yesterday")):
        selected = local_today - timedelta(days=1)
        end = selected + timedelta(days=1)
    elif _has_any(date_text, ("hom nay", "today")):
        selected = local_today
        end = selected + timedelta(days=1)
    else:
        match = _DATE_PATTERN.search(current_text) or _DATE_PATTERN.search(text)
        if not match:
            return None
        raw_date = match.group(0)
        try:
            if raw_date[:4].startswith("20"):
                selected = date.fromisoformat(raw_date.replace("/", "-"))
            else:
                day, month, year = raw_date.split("/")
                selected = date(int(year), int(month), int(day))
        except ValueError:
            return None
        end = selected + timedelta(days=1)
    appointment_time = not _is_booking_creation_request(text) and _is_appointment_time_request(text)
    result = {"booking_date_field": "starts_at" if appointment_time else "created_at"}
    if appointment_time and not _has_explicit_nonconfirmed_status(text):
        result["booking_status"] = "confirmed"
    if end - selected > timedelta(days=1):
        result.update({"booking_date_from": selected.isoformat(), "booking_date_to": end.isoformat()})
    else:
        result["booking_date"] = selected.isoformat()
    return result


def _is_booking_creation_request(text: str) -> bool:
    return _has_any(
        text,
        (
            "moi",
            "duoc tao",
            "ghi nhan",
            "dang ky",
            "dat lich",
            "dat kham",
            "duoc dat",
            "placed",
            "created",
            "recorded",
        ),
    )


def _has_explicit_nonconfirmed_status(text: str) -> bool:
    return _has_any(
        text,
        (
            "tu choi",
            "rejected",
            "huy",
            "cancelled",
            "cho duyet",
            "pending",
            "attended",
            "da kham",
            "tat ca trang thai",
            "all statuses",
        ),
    )


def _is_appointment_time_request(text: str) -> bool:
    return (
        _has_schedule_keyword(text)
        or _has_booking_phrase(text)
        or _has_any(
            text,
            (
                "ngay kham",
                "gio kham",
                "thoi gian kham",
                "khung gio kham",
                "co lich kham",
                "lich kham trong",
                "lich kham vao",
                "lich hen",
                "hen vao",
                "hen luc",
                "dien ra",
                "appointment date",
                "appointment time",
                "starts_at",
                "ends_at",
            ),
        )
    )


def _has_named_doctor(text: str) -> bool:
    for marker in ("bac si ", "doctor ", "physician "):
        if marker not in text:
            continue
        candidate = text.split(marker, 1)[1].split()[0]
        if candidate not in {"nao", "dang", "con", "co", "ten", "khoa", "o", "tai", "trong"}:
            return True
    return False
