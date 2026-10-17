"""Staff assistant with isolated prompts, scoped tools, and confirmed operations."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.staff_agent import StaffAgentGraph
from src.agents.staff_agent_cache import get_case_lookup_template, set_case_lookup_template
from src.agents.staff_agent_router import (
    StaffRoute,
    has_explicit_staff_lookup_intent,
    route_staff_request,
    route_staff_request_with_planner,
)
from src.agents.staff_agent_runtime import reset_session, set_session
from src.agents.staff_guardrails import (
    STAFF_UNSUPPORTED_REPLY,
    SYSTEM_PROMPT,
    _normalize_staff_input,
    staff_tool_result_refusal,
)
from src.agents.staff_nemo_guardrails import staff_input_allowed, staff_output_allowed
from src.agents.tools.staff_agent_tools import build_staff_tools
from src.config import get_settings
from src.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ServiceUnavailableError
from src.core.logging import get_logger, log_event
from src.db.session import get_auth_session_factory, get_session_factory
from src.medical_assistant.infrastructure.llm import LLMProvidersUnavailableError, get_staff_agent_llm
from src.models.user import User
from src.repositories.staff_agent import StaffAgentRepository
from src.schemas.booking import StaffBookingStatusUpdate
from src.schemas.staff_agent import (
    StaffAgentActionRequest,
    StaffAgentActionResponse,
    StaffAgentChatRequest,
    StaffAgentChatResponse,
    StaffAgentToolState,
)
from src.schemas.workbench import CaseAction, CaseBookingInput
from src.services.booking import BookingService
from src.services.staff_agent_query import StaffAgentQueryService
from src.services.staff_patient import StaffPatientService

HISTORY_LIMIT = 12
HISTORY_CONTEXT_CHAR_LIMIT = 12000
logger = get_logger(__name__)


class StaffAgentService:
    """Handle one staff member's persistent assistant conversation."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        patient_session: AsyncSession | None = None,
        llm: Any | None = None,
        query_service: StaffAgentQueryService | None = None,
    ) -> None:
        self.session = session
        self.repository = StaffAgentRepository(session)
        self.patient_service = StaffPatientService(patient_session or session)
        self.llm = llm
        self.query_service = query_service or StaffAgentQueryService()

    @staticmethod
    def _require_staff(staff: User) -> None:
        if staff.role != "staff":
            raise AuthorizationError()

    async def chat(self, staff: User, request: StaffAgentChatRequest) -> StaffAgentChatResponse:
        self._require_staff(staff)

        context = await self.repository.get_or_create_context(staff.id)
        if request.conversation_id and request.conversation_id != context.conversation_id:
            raise NotFoundError("Staff conversation not found")
        conversation = await self.repository.conversation(context.conversation_id)
        if conversation is None:
            raise NotFoundError("Staff conversation not found")
        if conversation.status != "ACTIVE":
            raise ConflictError("This staff conversation is closed")
        conversation_id = context.conversation_id

        try:
            input_allowed = await staff_input_allowed(request.message)
        except Exception as exc:
            raise ServiceUnavailableError("Staff guardrails are temporarily unavailable") from exc
        if not input_allowed:
            return StaffAgentChatResponse(
                conversation_id=context.conversation_id,
                assistant_text=STAFF_UNSUPPORTED_REPLY,
                tool_states=[],
            )

        prior_messages = await self.repository.messages(context.conversation_id, limit=HISTORY_LIMIT)
        prior_messages = _bound_history(prior_messages)
        context_text = next(
            (
                item.content or ""
                for item in reversed(prior_messages)
                if item.sender_type == "STAFF" and has_explicit_staff_lookup_intent(item.content or "")
            ),
            "",
        )
        route = route_staff_request(request.message, context_text, safety_checked=True)
        if route.category == "chitchat":
            return await self._finish_direct_reply(staff, request, context, route)

        has_pending_task_plan = bool((getattr(context, "context_data", None) or {}).get("pending_task_plan"))
        if (
            not has_pending_task_plan
            and route.category == "complex"
            and not any(
                name in route.tool_names
                for name in ("prepare_booking_review", "prepare_case_claim", "prepare_case_booking")
            )
        ):
            planner_llm = self.llm
            if planner_llm is None:
                try:
                    planner_llm = get_staff_agent_llm()
                except Exception:
                    planner_llm = None
            route = await route_staff_request_with_planner(request.message, context_text, planner_llm, route=route)

        context_data = dict(getattr(context, "context_data", None) or {})
        pending_plan = context_data.pop("pending_task_plan", None)
        confirmed_domains: list[str] = []
        if pending_plan:
            decision = _scope_confirmation_decision(request.message)
            tasks = [task for task in pending_plan if isinstance(task, dict) and task.get("domain")]
            domains = [str(task["domain"]) for task in tasks]
            if decision == "cases_only":
                domains = [domain for domain in domains if "case" in domain]
            elif decision == "patient_only":
                domains = [domain for domain in domains if domain == "patient_profile"]
            context.context_data = context_data
            if decision in {"confirm", "cases_only"}:
                confirmed_domains = domains
                identifier = _confirmed_patient_identifier(request.message)
                if "patient_profile" in domains and not identifier:
                    domains.remove("patient_profile")
                tools = _tools_for_task_domains(domains)
                if not tools:
                    route = StaffRoute(
                        "ambiguous",
                        "patient_identifier_required",
                        reply="Vui lòng cung cấp tên hoặc mã bệnh nhân để tra đúng hồ sơ; tôi chưa tìm kiếm bệnh nhân.",
                    )
                else:
                    route = StaffRoute("complex" if len(tools) > 1 else "simple", "confirmed_case_lookup", tuple(tools))
            elif decision == "patient_only":
                route = StaffRoute(
                    "ambiguous",
                    "patient_identifier_required",
                    reply="Đã rõ, bạn chỉ muốn tra hồ sơ. Vui lòng cung cấp tên hoặc mã bệnh nhân để tôi tìm đúng hồ sơ.",
                )
            else:
                reply = (
                    "Bạn muốn thực hiện phần nào: tra hồ sơ bệnh nhân, tra ca điều phối/HITL hôm nay, "
                    "hay tra booking/lượt khám? Vui lòng nêu rõ phạm vi."
                    if decision == "unclear"
                    else "Đã rõ. Tôi chưa tra cứu dữ liệu. Hãy cho biết tác vụ nào bạn muốn thực hiện."
                )
                route = StaffRoute("ambiguous", "task_scope_not_confirmed", reply=reply)
        elif route.category == "confirmation":
            context_data["pending_task_plan"] = route.tasks or []
            context.context_data = context_data
        if route.reply is not None:
            return await self._finish_direct_reply(staff, request, context, route)

        pending = context_data.get("pending_action")
        if pending and pending.get("state") == "executing":
            raise ConflictError("A booking review is currently being processed")
        context_data.pop("pending_action", None)
        context.context_data = context_data

        await self.repository.add_message(
            context.conversation_id,
            sender_type="STAFF",
            sender_id=staff.id,
            content=request.message,
        )
        await self.session.commit()

        messages = _build_context_messages(prior_messages, request.message)
        if route.reason_code == "confirmed_case_lookup":
            identifier = _confirmed_patient_identifier(request.message)
            messages.insert(
                1,
                SystemMessage(
                    content=(
                        "Chỉ dùng các tool đã được route cho phạm vi staff vừa xác nhận. "
                        + (
                            "Gọi search_staff_cases với received_today=true cho ca tạo hôm nay. "
                            if "today_coordination_cases" in confirmed_domains
                            else ""
                        )
                        + (
                            "Tin nhắn xác nhận có định danh bệnh nhân; dùng chính xác định danh đó với "
                            "search_staff_patients, chỉ đọc hồ sơ khi đã xác định đúng một bệnh nhân. "
                            "Nếu có nhiều kết quả, hỏi staff chọn; không tự đoán."
                            if identifier and "patient_profile" in confirmed_domains
                            else (
                                "Sau khi trả kết quả ca, hỏi tên/mã bệnh nhân để tiếp tục tra hồ sơ; "
                                "không tìm hoặc liệt kê bệnh nhân khi thiếu định danh."
                                if any("case" in domain for domain in confirmed_domains)
                                else "Chỉ tra hồ sơ khi đã có định danh bệnh nhân."
                            )
                        )
                    )
                ),
            )

        tool_states: list[StaffAgentToolState] = []
        pending_action: dict | None = None
        self._pending_action = None
        try:
            assistant_text = await self._run_agent(
                staff,
                messages,
                tool_states,
                route=route,
            )
            pending_action = getattr(self, "_pending_action", None)
            output_allowed = await staff_output_allowed(assistant_text.strip())
        except Exception as exc:
            if isinstance(exc, LLMProvidersUnavailableError):
                log_event(logger, logging.WARNING, "staff_agent.providers_unavailable")
                await self.session.rollback()
                answer = "Trợ lý đang tạm thời không thể xử lý yêu cầu. Chưa có thao tác nào được thực hiện; vui lòng thử lại sau ít phút."
                await self.repository.add_message(
                    conversation_id,
                    sender_type="AGENT",
                    sender_id=None,
                    content=answer,
                )
                await self.session.commit()
                return StaffAgentChatResponse(
                    conversation_id=conversation_id,
                    assistant_text=answer,
                    tool_states=[],
                )
            log_event(logger, logging.ERROR, "staff_agent.request_failed")
            await self.session.rollback()
            raise ServiceUnavailableError("Trợ lý hiện chưa khả dụng. Vui lòng thử lại sau.") from exc

        answer = assistant_text.strip() if output_allowed else STAFF_UNSUPPORTED_REPLY
        if not output_allowed:
            pending_action = None
            self._pending_action = None
        if not answer:
            raise ServiceUnavailableError("Trợ lý chưa tạo được câu trả lời. Vui lòng thử lại.")
        await self.repository.add_message(
            context.conversation_id,
            sender_type="AGENT",
            sender_id=None,
            content=answer,
        )
        if pending_action:
            context_data = dict(getattr(context, "context_data", None) or {})
            context_data["pending_action"] = pending_action
            context.context_data = context_data
        await self.session.commit()
        return StaffAgentChatResponse(
            conversation_id=context.conversation_id,
            assistant_text=answer,
            tool_states=tool_states,
            pending_action={key: value for key, value in pending_action.items() if key != "state"}
            if pending_action
            else None,
        )

    async def chat_stream(self, staff: User, request: StaffAgentChatRequest):
        """Stream assistant response events (status, tool, token, pending_action, done)."""
        import asyncio
        import json

        yield f"event: status\ndata: {json.dumps({'status': 'processing'})}\n\n"
        try:
            response = await self.chat(staff, request)
        except Exception:
            log_event(logger, logging.ERROR, "staff_agent.stream_failed")
            yield f"event: error\ndata: {json.dumps({'message': 'Không thể xử lý yêu cầu lúc này.'})}\n\n"
            return

        for state in response.tool_states:
            yield f"event: tool\ndata: {json.dumps({'tool': state.tool, 'status': state.status})}\n\n"

        text = response.assistant_text
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.01)

        if response.pending_action:
            yield f"event: pending_action\ndata: {json.dumps(response.pending_action)}\n\n"

        yield f"event: done\ndata: {json.dumps(response.model_dump(mode='json'))}\n\n"

    async def _run_agent(
        self,
        staff: User,
        messages: list[Any],
        tool_states: list[StaffAgentToolState],
        *,
        route: StaffRoute | None = None,
    ) -> str:
        llm = self.llm or get_staff_agent_llm()
        pending_action_ref: list[dict | None] = [None]
        facility_ids = await self.repository.get_staff_facility_scope(staff.id)
        facility_scope = ",".join(sorted(map(str, facility_ids)))
        factories = {}
        if get_settings().database_url:
            factories = {"application": get_session_factory(), "auth": get_auth_session_factory()}
        tools = build_staff_tools(
            staff,
            session=self.session,
            patient_service=self.patient_service,
            repository=self.repository,
            query_service=self.query_service,
            pending_action_ref=pending_action_ref,
            facility_scope=facility_scope,
            force_emergency_cases=bool(
                route and any(task.get("filters", {}).get("emergency_only") for task in route.tasks or [])
            ),
            force_agent_consulting_cases=bool(
                route and any(task.get("filters", {}).get("agent_consulting") for task in route.tasks or [])
            ),
            force_submitted_exam_forms=bool(
                route and any(task.get("filters", {}).get("submitted_exam_forms") for task in route.tasks or [])
            ),
            continue_case_booking_after_claim=bool(
                route and any(task.get("filters", {}).get("continue_to_booking") for task in route.tasks or [])
            ),
            forced_booking_date=next(
                (
                    task["filters"]
                    for task in (route.tasks if route else [])
                    if task.get("domain") == "bookings"
                    and (
                        task.get("filters", {}).get("booking_date") or task.get("filters", {}).get("booking_date_from")
                    )
                    and task.get("filters", {}).get("booking_date_field") in {"starts_at", "created_at"}
                ),
                None,
            ),
        )
        if route and route.tool_names:
            selected_names = set(route.tool_names)
            tools = [item for item in tools if item.name in selected_names]
        current_message = str(messages[-1].content) if messages else ""
        template_name = _case_lookup_template_name(route, current_message)
        if template_name:
            cached_args = await get_case_lookup_template(template_name)
            if cached_args is None:
                await set_case_lookup_template(template_name)
            else:
                tool = next((item for item in tools if item.name == "search_staff_cases"), None)
                if tool is not None:
                    factory = factories.get((tool.metadata or {}).get("database"))
                    if factory:
                        async with factory() as tool_session:
                            token = set_session(tool_session)
                            try:
                                tool_output = await tool.ainvoke(cached_args)
                            finally:
                                reset_session(token)
                    else:
                        tool_output = await tool.ainvoke(cached_args)
                    if staff_tool_result_refusal(tool_output):
                        raise ServiceUnavailableError("Kết quả tra cứu chưa thể xác minh an toàn; vui lòng thử lại.")
                    result = json.loads(tool_output)
                    answer = _format_case_lookup_result(result, template_name, route.language)
                    tool_states.append(StaffAgentToolState(tool="search_staff_cases", status="success"))
                    return answer
        answer, states = await StaffAgentGraph(
            llm,
            tools,
            factories,
        ).ainvoke(
            messages,
            tasks=route.tasks if route else None,
            goal_plan=route.goal_plan if route else None,
        )
        tool_states.extend(StaffAgentToolState.model_validate(item) for item in states)
        self._pending_action = pending_action_ref[0]
        return answer

    async def _finish_direct_reply(self, staff, request, context, route: StaffRoute):
        answer = route.reply or "Tôi có thể hỗ trợ tra cứu nghiệp vụ cho staff."
        try:
            allowed = await staff_output_allowed(answer)
        except Exception as exc:
            raise ServiceUnavailableError("Staff guardrails are temporarily unavailable") from exc
        if not allowed:
            answer = "Yêu cầu này chưa thể xử lý an toàn. Vui lòng diễn đạt lại yêu cầu nghiệp vụ."
        if route.category != "unsupported":
            await self.repository.add_message(
                context.conversation_id, sender_type="STAFF", sender_id=staff.id, content=request.message
            )
            await self.repository.add_message(
                context.conversation_id, sender_type="AGENT", sender_id=None, content=answer
            )
            await self.session.commit()
        return StaffAgentChatResponse(
            conversation_id=context.conversation_id,
            assistant_text=answer,
            tool_states=[],
        )

    async def _claim_action(self, staff: User, request: StaffAgentActionRequest) -> tuple[Any, dict]:
        context = await self.repository._context_for_staff(staff.id, lock=True)
        if context is None or context.conversation_id != request.conversation_id:
            raise NotFoundError("Staff conversation not found")
        data = dict(getattr(context, "context_data", None) or {})
        action = data.get("pending_action")
        if not action or action.get("id") != str(request.pending_action_id) or action.get("state") != "pending":
            raise ConflictError("This booking review proposal is no longer available")
        if action.get("kind") == "case_booking" and not request.patient_agreed:
            raise ConflictError("Patient agreement must be confirmed before booking")
        if datetime.fromisoformat(action["expires_at"]) <= datetime.now(UTC):
            data.pop("pending_action", None)
            context.context_data = data
            await self.session.commit()
            raise ConflictError("This booking review proposal has expired")
        action["state"] = "executing"
        data["pending_action"] = action
        context.context_data = data
        await self.session.commit()
        return context, action

    async def confirm_action(self, staff: User, request: StaffAgentActionRequest) -> StaffAgentActionResponse:
        self._require_staff(staff)
        context, action = await self._claim_action(staff, request)
        try:
            kind = action.get("kind", "booking_review")
            if kind == "booking_review":
                await BookingService(self.session).review(
                    UUID(action["booking_id"]),
                    staff.id,
                    StaffBookingStatusUpdate(status=action["decision"], note=action.get("reason")),
                )
                text = "Đã xác nhận lịch khám." if action["decision"] == "confirmed" else "Đã từ chối lịch khám."
            elif kind in {"case_claim", "case_booking"}:
                text = await self._confirm_case_operation(staff, action, request.patient_agreed)
            else:
                raise ConflictError("This staff assistant action is not supported")
        except Exception:
            await self._clear_action(context)
            raise
        await self._clear_action(context)
        await self.repository.add_message(request.conversation_id, sender_type="AGENT", sender_id=None, content=text)
        await self.session.commit()
        return StaffAgentActionResponse(conversation_id=request.conversation_id, assistant_text=text)

    async def _confirm_case_operation(self, staff: User, action: dict, patient_agreed: bool) -> str:
        from sqlalchemy import select

        from src.models.workbench import CoordinatorMember
        from src.services import workbench

        if action["kind"] == "case_booking" and not patient_agreed:
            raise ConflictError("Patient agreement must be confirmed before booking")
        patient_message = None
        async with self.session.begin():
            member = (
                await self.session.execute(
                    select(CoordinatorMember).where(CoordinatorMember.user_id == staff.id).with_for_update()
                )
            ).scalar_one_or_none()
            if not member or not member.enabled:
                raise AuthorizationError()
            case = await workbench.locked_case(self.session, UUID(action["case_id"]), member)
            if action["kind"] == "case_claim":
                patient_message = await workbench.action(
                    self.session,
                    case,
                    staff,
                    member,
                    CaseAction(version=action["version"], action="claim"),
                )
                text = (
                    "Đã tiếp nhận ca điều phối. Để tiếp tục đặt lịch, vui lòng cho biết ngày khám mong muốn "
                    "và chuyên khoa hoặc dịch vụ cần tìm."
                    if action.get("continue_to_booking")
                    else "Đã tiếp nhận ca điều phối."
                )
            else:
                payload_data = {**action["booking_payload"], "patient_agreed": True}
                await workbench.create_case_booking(
                    self.session,
                    case,
                    staff,
                    member,
                    CaseBookingInput.model_validate(payload_data),
                )
                text = "Đã tạo booking và lịch khám cho ca điều phối."
            await self.session.flush()
        from src.services.chat_takeover import publish_workbench_case_update, publish_workbench_message

        if patient_message is not None:
            await publish_workbench_message(case, patient_message)
        else:
            await publish_workbench_case_update(case)
        return text

    async def cancel_action(self, staff: User, request: StaffAgentActionRequest) -> StaffAgentActionResponse:
        self._require_staff(staff)
        context = await self.repository._context_for_staff(staff.id, lock=True)
        if context is None or context.conversation_id != request.conversation_id:
            raise NotFoundError("Staff conversation not found")
        data = dict(getattr(context, "context_data", None) or {})
        action = data.get("pending_action")
        if not action or action.get("id") != str(request.pending_action_id) or action.get("state") != "pending":
            raise ConflictError("This booking review proposal is no longer available")
        data.pop("pending_action", None)
        context.context_data = data
        text = "Đã hủy đề xuất; lịch khám chưa được thay đổi."
        await self.repository.add_message(request.conversation_id, sender_type="AGENT", sender_id=None, content=text)
        await self.session.commit()
        return StaffAgentActionResponse(conversation_id=request.conversation_id, assistant_text=text)

    async def _clear_action(self, context: Any) -> None:
        await self.session.refresh(context)
        data = dict(getattr(context, "context_data", None) or {})
        data.pop("pending_action", None)
        context.context_data = data
        await self.session.commit()


def _case_lookup_template_name(route: StaffRoute | None, message: str) -> str | None:
    if (
        route is None
        or route.category != "simple"
        or "search_staff_cases" not in route.tool_names
        or not set(route.tool_names).issubset({"search_staff_cases", "get_staff_case"})
        or len(route.tasks or []) != 1
    ):
        return None
    task = (route.tasks or [])[0]
    domain = task.get("domain")
    filters = task.get("filters") or {}
    if domain not in {"coordination_cases", "today_coordination_cases"}:
        return None
    if set(filters) - {"received_today", "emergency_only"}:
        return None
    received_today = filters.get("received_today", False)
    emergency_only = filters.get("emergency_only", False)
    current_text = _normalize_staff_input(message)
    if received_today is True and not any(term in current_text for term in ("hom nay", "today")):
        return None
    if emergency_only is True and not any(term in current_text for term in ("cap cuu", "emergency", "nguy cap")):
        return None
    if (domain == "today_coordination_cases") != (received_today is True):
        return None
    if received_today is not True and emergency_only is not True:
        return None
    return "today_emergency" if received_today and emergency_only else "today" if received_today else "emergency"


def _format_case_lookup_result(payload: Any, template: str, language: str) -> str:
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("items"), list)
        or type(payload.get("count")) is not int
        or payload["count"] != len(payload["items"])
        or not isinstance(payload.get("more_available"), bool)
        or (not payload["items"] and payload["more_available"])
    ):
        raise ServiceUnavailableError("Kết quả tra cứu ca chưa đúng định dạng; vui lòng thử lại.")
    is_vi = language != "en"
    emergency = "emergency" in template
    today = "today" in template
    if not payload["items"]:
        if is_vi:
            subject = "ca cấp cứu chưa được tiếp nhận" if emergency else "ca điều phối chưa được tiếp nhận"
            period = " được tạo hôm nay" if today else ""
            return f"Không tìm thấy {subject}{period} trong phạm vi cơ sở bạn được phép xem."
        subject = "emergency cases not yet accepted" if emergency else "coordination cases not yet accepted"
        period = " created today" if today else ""
        return f"No {subject}{period} were found in your authorized facility scope."

    if is_vi:
        title = "ca cấp cứu chưa được tiếp nhận" if emergency else "ca điều phối chưa được tiếp nhận"
        period = " được tạo hôm nay" if today else ""
        lines = [f"Tìm thấy {payload['count']} {title}{period} trong phạm vi cơ sở bạn được phép xem:"]
        case_label, patient_label, status_label, priority_label = "Mã ca", "Bệnh nhân", "Trạng thái", "Ưu tiên"
        more_text = "Còn kết quả khác; danh sách dưới đây mới hiển thị một phần."
    else:
        title = "emergency cases not yet accepted" if emergency else "coordination cases not yet accepted"
        period = " created today" if today else ""
        lines = [f"Found {payload['count']} {title}{period} in your authorized facility scope:"]
        case_label, patient_label, status_label, priority_label = "Case", "Patient", "Status", "Priority"
        more_text = "More results are available; this list is partial."

    for item in payload["items"]:
        if not isinstance(item, dict) or not all(key in item for key in ("id", "status", "priority")):
            raise ServiceUnavailableError("Kết quả tra cứu ca chưa đúng định dạng; vui lòng thử lại.")
        details = [f"{case_label}: {item['id']}"]
        if item.get("patient_name"):
            details.append(f"{patient_label}: {item['patient_name']}")
        details.extend((f"{status_label}: {item['status']}", f"{priority_label}: {item['priority']}"))
        lines.append("- " + "; ".join(details))
    if payload["more_available"]:
        lines.append(more_text)
    return "\n".join(lines)


def _bound_history(messages: list[Any]) -> list[Any]:
    """Keep the newest conversation context under a fixed character budget."""
    selected = list(messages[-HISTORY_LIMIT:])
    while len(selected) > 1 and sum(len(item.content or "") for item in selected) > HISTORY_CONTEXT_CHAR_LIMIT:
        selected.pop(0)
    if selected and len(selected[-1].content or "") > HISTORY_CONTEXT_CHAR_LIMIT:
        from types import SimpleNamespace

        latest = selected[-1]
        selected[-1] = SimpleNamespace(
            sender_type=latest.sender_type,
            content=(latest.content or "")[-HISTORY_CONTEXT_CHAR_LIMIT:],
        )
    return selected


def _build_context_messages(prior_messages: list[Any], current_message: str) -> list[Any]:
    """Keep a stable system prefix followed by bounded, changing conversation data."""
    messages: list[Any] = [
        SystemMessage(
            content=(
                f"{SYSTEM_PROMPT}\nNgày hiện tại tại Việt Nam (Asia/Ho_Chi_Minh): "
                f"{datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()}."
            )
        )
    ]
    messages.extend(
        HumanMessage(content=item.content or "")
        if item.sender_type == "STAFF"
        else AIMessage(content=item.content or "")
        for item in prior_messages
    )
    messages.append(HumanMessage(content=current_message))
    return messages


def _scope_confirmation_decision(message: str) -> str:
    normalized = " ".join(_normalize_staff_input(message).replace(",", " ").split()).strip(" .!?")
    if "chi" in normalized and any(term in normalized for term in ("case", "ca dieu phoi", "ca hitl")):
        return "cases_only"
    if "chi" in normalized and any(term in normalized for term in ("ho so", "benh nhan", "profile")):
        return "patient_only"
    affirmative = ("co", "dung", "dong y", "xac nhan", "ok", "oke", "yes", "sure")
    if normalized in set(affirmative) or normalized.startswith(tuple(f"{item} " for item in affirmative)):
        return "confirm"
    negative = ("khong", "khong can", "huy", "bo qua", "no", "cancel")
    if normalized in set(negative) or normalized.startswith(tuple(f"{item} " for item in negative)):
        return "reject"
    return "unclear"


def _tools_for_task_domains(domains: list[str]) -> list[str]:
    domain_tools = {
        "patient_profile": ("search_staff_patients", "get_staff_patient_profile"),
        "bookings": ("search_staff_bookings", "get_staff_booking"),
        "coordination_cases": ("search_staff_cases", "get_staff_case"),
        "today_coordination_cases": ("search_staff_cases", "get_staff_case"),
        "availability": ("search_staff_availability",),
        "doctors": ("search_staff_doctors",),
        "procedures": ("search_approved_staff_procedures",),
    }
    return list(dict.fromkeys(tool for domain in domains for tool in domain_tools.get(domain, ())))


def _confirmed_patient_identifier(message: str) -> str | None:
    normalized = _normalize_staff_input(message).replace(",", " ").split()
    if not normalized or normalized[0] not in {"co", "dung", "dong", "xac", "ok", "oke", "yes", "sure"}:
        return None
    ignored = {"roi", "nhe", "nha", "toi", "muon", "ten", "benh", "nhan", "la", "va"}
    identifier = [word for word in normalized[1:] if word not in ignored]
    return " ".join(identifier) if identifier else None
