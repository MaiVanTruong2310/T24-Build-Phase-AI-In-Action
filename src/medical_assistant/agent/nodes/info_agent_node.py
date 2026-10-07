"""Info Agent Node (ReAct architecture for grounded knowledge retrieval).

Node xử lý các câu hỏi tra cứu thông tin (bác sĩ, chuyên khoa, bệnh học, cơ sở y tế)
sử dụng LLM kết hợp với bộ công cụ Read-Only tools, đảm bảo:
- Grounded 100% trên dữ liệu DB / Datalake (Zero Hallucination).
- Tối đa 4 vòng lặp gọi tool (ReAct loop), timeout 20s.
- Lưu trữ state["last_tool_results"] (<= 2KB) để phục vụ hỏi tiếp (follow-up).
- Lọc bảo mật rò rỉ dữ liệu qua DLPService.sanitize().
- Đầy đủ Telemetry metadata: tools_called, tool_errors, tokens, data_unavailable.
- Gộp metadata (merge), duy trì tin nhắn với CompactionService, giữ quick_replies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.agent.tools import ALL_TOOLS
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.security.dlp_service import get_dlp_service
from src.medical_assistant.domain.token_counter import TokenCounter
from src.medical_assistant.infrastructure.llm import get_llm

logger = logging.getLogger(__name__)

MEDICAL_DISCLAIMER_VI = (
    "\n\nKhuyến cáo y tế: Thông tin chỉ mang tính chất định hướng và hỗ trợ đặt lịch khám, "
    "không thay thế cho chẩn đoán hoặc chỉ định điều trị của bác sĩ chuyên khoa."
)

INFO_AGENT_SYSTEM_PROMPT = """Bạn là Trợ Lý Y Tế Tiếp Đón Thông Minh (P-124 Smart Medical Assistant) thuộc Hệ thống Y tế Đa khoa Quốc tế Vinmec.
Nhiệm vụ của bạn là tra cứu và giải đáp các câu hỏi thông tin của người bệnh một cách chính xác, trung thực và thấu cảm.

QUY TẮC BẮT BUỘC (NON-NEGOTIABLE RULES):
1. PHONG CÁCH VÀ XƯNG HÔ (AGENT.MD):
   - Luôn xưng "em" và gọi người dùng là "bác" (hoặc "anh/chị" nếu người dùng xưng hô trẻ).
   - Giữ thái độ ân cần, tôn kính, điềm tĩnh và thấu hiểu.

2. NGUYÊN TẮC ZERO-HALLUCINATION & GROUNDING:
   - CHỈ trả lời dựa trên thông tin thực tế trả về từ các công cụ (tools).
   - Nếu công cụ báo không tìm thấy hoặc dữ liệu không có, hãy nói rõ trung thực: "Dạ em chưa tìm thấy thông tin phù hợp trong hệ thống..." và gợi ý bước tiếp theo (hỏi chuyên khoa khác, liên hệ hotline 1900 232 389, hoặc đến cơ sở gần nhất).
   - TUYỆT ĐỐI KHÔNG tự bịa tên bác sĩ, số năm kinh nghiệm, giá dịch vụ, giờ làm việc hay cơ sở không có trong kết quả tool.

3. QUY TẮC TRA CỨU BÁC SĨ & CHUYÊN KHOA (CHỦ ĐỘNG GỌI TOOL):
   - Với yêu cầu "xem hồ sơ bác sĩ khoa X", "bác sĩ khoa X gồm những ai", "danh sách bác sĩ khoa X", BẮT BUỘC PHẢI GỌI TOOL search_doctors NGAY LẬP TỨC với tham số phù hợp, TUYỆT ĐỐI KHÔNG hỏi lại người dùng khi đã có tên khoa/chuyên khoa.
   - Với yêu cầu tìm "trưởng khoa" hoặc "bác sĩ đầu ngành", PHẢI THỬ GỌI search_doctors trước khi kết luận không có.

4. AN TOÀN LÂM SÀNG (RULES.MD):
   - Tuyệt đối KHÔNG chẩn đoán xác định bệnh (không khẳng định "bác bị bệnh X").
   - Tuyệt đối KHÔNG kê đơn thuốc, liều dùng hay hướng dẫn dùng thuốc điều trị.

5. NGUỒN VÀ ĐƯỜNG DẪN TRUY CẬP (QUY TẮC BẮT BUỘC VỀ URL THỰC TẾ):
   - TUYỆT ĐỐI KHÔNG HIỂN THỊ tên kỹ thuật cơ sở dữ liệu nội bộ như "supabase.facilities", "datalake.hospitals", "supabase.doctors" trong câu trả lời người dùng.
   - Khi giới thiệu cơ sở bệnh viện/phòng khám, BẮT BUỘC PHẢI DÙNG ĐƯỜNG DẪN URL THẬT và định dạng Markdown link có thể nhấn chuyển tiếp được:
     Ví dụ: 👉 [Xem chi tiết Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng](url_thật_từ_tool)
   - Khi giới thiệu bác sĩ có `source_url`, PHẢI đính kèm đường link dẫn đến hồ sơ bác sĩ:
     Ví dụ: [Hồ sơ nguồn Vinmec](url_thật_từ_tool)
   - Luôn sử dụng URL thật từ dữ liệu trả về của công cụ, tuyệt đối không để chuỗi kỹ thuật thô.

6. BỘ CÔNG CỤ KHẢ DỤNG (CHỈ SỬ DỤNG 6 TOOLS NÀY):
   - search_doctors: Tìm kiếm danh sách bác sĩ chuyên khoa thực tế từ cơ sở dữ liệu.
   - get_doctor_detail: Xem hồ sơ chi tiết, quá trình đào tạo, kinh nghiệm công tác của một bác sĩ.
   - get_doctor_slots: Tra cứu lịch khám/slot còn trống thực tế của bác sĩ.
   - get_department_info: Tra cứu thông tin, chức năng nhiệm vụ, kỹ thuật mũi nhọn của chuyên khoa.
   - search_disease_knowledge: Tra cứu kiến thức bệnh học, nguyên nhân, triệu chứng từ kho y khoa.
   - list_facilities: Tra cứu danh sách các bệnh viện và phòng khám trong Hệ thống Y tế Vinmec.
"""


def _clean_tool_data(data: Any) -> Any:
    """Rút gọn dữ liệu tool, giữ trọn các thực thể quan trọng (tên, học vị, cơ sở, chuyên khoa, URL)."""
    if isinstance(data, dict):
        if "doctors" in data and isinstance(data["doctors"], list):
            return {
                "found": data.get("found", True),
                "count": data.get("count"),
                "doctors": [
                    {
                        "full_name": d.get("full_name") or d.get("name"),
                        "title": d.get("title"),
                        "specialties": d.get("specialties"),
                        "workplace": d.get("workplace"),
                        "years_of_experience": d.get("years_of_experience"),
                        "source_url": d.get("source_url"),
                    }
                    for d in data["doctors"]
                ],
            }
        if "facilities" in data and isinstance(data["facilities"], list):
            return {
                "found": data.get("found", True),
                "facilities": [
                    {
                        "name": f.get("name"),
                        "facility_type": f.get("facility_type"),
                        "address": f.get("address"),
                        "phone": f.get("phone"),
                        "detail_url": f.get("detail_url"),
                        "key_specialties": f.get("key_specialties"),
                    }
                    for f in data["facilities"]
                ],
            }
        return {k: (v[:200] if isinstance(v, str) and len(v) > 200 else v) for k, v in data.items()}
    return data


def _compact_tool_results(results: list[dict[str, Any]], max_bytes: int = 2048) -> list[dict[str, Any]]:
    """Nén gọn kết quả tool xuống dưới giới hạn dung lượng để lưu vào state phục vụ follow-up."""
    if not results:
        return []
    compacted: list[dict[str, Any]] = []
    current_size = 0

    for item in results:
        cleaned = _clean_tool_data(item.get("data"))
        simplified = {
            "tool": item.get("tool"),
            "data": cleaned,
        }
        item_bytes = len(json.dumps(simplified, ensure_ascii=False).encode("utf-8"))
        if current_size + item_bytes <= max_bytes:
            compacted.append(simplified)
            current_size += item_bytes
        else:
            # Nếu một item vượt 2048 bytes, vẫn lưu tối thiểu danh sách thực thể
            compacted.append({
                "tool": item.get("tool"),
                "data": {"compacted": True, "summary": str(cleaned)[:1000]},
            })
            break
    return compacted


async def _run_react_loop(
    model_with_tools: Any,
    tools_map: dict[str, Any],
    messages: list[Any],
    max_turns: int = 4,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Thực thi vòng lặp ReAct tối đa 4 lượt gọi tool."""
    tools_called: list[dict[str, Any]] = []
    collected_results: list[dict[str, Any]] = []
    tool_errors: list[str] = []
    final_text = ""

    for _ in range(max_turns):
        ai_msg = await model_with_tools.ainvoke(messages)
        messages.append(ai_msg)

        # Nếu model không gọi tool nữa -> đã có câu trả lời cuối cùng
        if not getattr(ai_msg, "tool_calls", None):
            final_text = str(ai_msg.content or "")
            break

        # Thực thi lần lượt các tool calls
        for tool_call in ai_msg.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call["args"]
            t_id = tool_call.get("id") or f"call_{t_name}"

            tools_called.append({"tool": t_name, "args": t_args})

            if t_name in tools_map:
                tool_instance = tools_map[t_name]
                try:
                    res = await asyncio.to_thread(tool_instance.invoke, t_args)
                    res_str = json.dumps(res, ensure_ascii=False)
                    collected_results.append({"tool": t_name, "data": res})
                except Exception as exc:
                    err_msg = f"Lỗi khi thực thi tool '{t_name}': {exc}"
                    logger.error(err_msg, exc_info=True)
                    tool_errors.append(err_msg)
                    err_data = {"found": False, "error": str(exc), "data_unavailable": True}
                    collected_results.append({"tool": t_name, "data": err_data})
                    res_str = json.dumps(err_data, ensure_ascii=False)
            else:
                err_msg = f"Tool '{t_name}' không tồn tại."
                tool_errors.append(err_msg)
                err_data = {"found": False, "error": err_msg, "data_unavailable": True}
                collected_results.append({"tool": t_name, "data": err_data})
                res_str = json.dumps(err_data, ensure_ascii=False)

            messages.append(ToolMessage(content=res_str, tool_call_id=t_id, name=t_name))
    else:
        # Nếu đã hết số vòng lặp tối đa mà model vẫn gọi tool
        last_msg = messages[-1]
        final_text = str(getattr(last_msg, "content", "") or "Dạ, em đã tra cứu thông tin theo yêu cầu của bác.")

    return final_text, tools_called, collected_results, tool_errors, ai_msg


async def info_agent_node(state: AgentState, llm: Any = None) -> dict[str, Any]:
    """LangGraph node thực thi tra cứu thông tin qua ReAct Agent có grounding."""
    start_time = time.monotonic()

    query = state.get("query") or state.get("user_input", "")
    language = state.get("language") or "vi"
    last_tool_results = state.get("last_tool_results") or []

    # Chuẩn bị model và tools
    active_llm = llm or get_llm()
    tools_map = {t.name: t for t in ALL_TOOLS}
    model_with_tools = active_llm.bind_tools(ALL_TOOLS)

    # Xây dựng chuỗi hội thoại
    system_prompt = INFO_AGENT_SYSTEM_PROMPT
    if language == "en":
        system_prompt += "\nIMPORTANT: The patient prefers English. Reply in English."

    messages: list[Any] = [SystemMessage(content=system_prompt)]

    # Bổ sung dữ liệu tra cứu từ lượt trước để giải quyết câu hỏi tiếp (follow-up)
    if last_tool_results:
        context_str = json.dumps(last_tool_results, ensure_ascii=False)
        messages.append(
            SystemMessage(
                content=f"Dữ liệu tra cứu từ lượt hội thoại trước (dùng để giải quyết tham chiếu nếu người dùng hỏi tiếp):\n{context_str}"
            )
        )

    messages.append(HumanMessage(content=query))

    token_counter = TokenCounter()
    all_prompt_texts = [str(getattr(m, "content", "") or "") for m in messages]
    prompt_tokens = token_counter.count_tokens(" ".join(all_prompt_texts))

    llm_succeeded: bool = False
    fallback_used: bool = False
    has_data_unavailable: bool = False
    data_unavailable_reason: str | None = None
    last_ai_msg: Any = None

    try:
        # Thực thi ReAct loop với timeout tối đa 20s
        final_text, tools_called, collected_results, tool_errors, last_ai_msg = await asyncio.wait_for(
            _run_react_loop(model_with_tools, tools_map, messages, max_turns=4),
            timeout=20.0,
        )
        llm_succeeded = True

        # Đọc winner metadata từ model failover
        winner_info = {}
        for m in [model_with_tools, active_llm]:
            if hasattr(m, "get_last_winner") and callable(m.get_last_winner):
                try:
                    res_winner = m.get_last_winner()
                    if isinstance(res_winner, dict) and res_winner:
                        winner_info = res_winner
                        break
                except Exception:
                    pass

        is_fallback_provider = (
            int(winner_info.get("provider_index", 0) or 0) != 0
            or int(winner_info.get("providers_attempted", 1) or 1) > 1
        )

        # Kiểm tra xem có tool nào dùng crawl hoặc báo data_unavailable hoặc error không
        used_crawl = any(
            isinstance(res_item.get("data"), dict) and (
                res_item["data"].get("source") == "vinmec_crawl"
                or any(d.get("data_source") == "vinmec_crawl" for d in res_item["data"].get("doctors", []))
            )
            for res_item in collected_results
        )
        fallback_used = bool(is_fallback_provider or used_crawl)

        for res_item in collected_results:
            data_dict = res_item.get("data")
            if isinstance(data_dict, dict):
                if data_dict.get("data_unavailable"):
                    has_data_unavailable = True
                    data_unavailable_reason = data_dict.get("reason") or data_dict.get("warning") or "TOOL_DATA_UNAVAILABLE"
                elif data_dict.get("found") is False and data_dict.get("error"):
                    has_data_unavailable = True
                    data_unavailable_reason = f"TOOL_ERROR: {data_dict.get('error')}"

    except asyncio.TimeoutError:
        logger.warning("info_agent_node timed out after 20 seconds for query: %s", query)
        final_text = (
            "Dạ, quá trình tra cứu thông tin chi tiết đang mất nhiều thời gian hơn dự kiến. "
            "Bác vui lòng thử lại hoặc liên hệ tổng đài 1900 232 389 để được hỗ trợ tức thì ạ."
        )
        tools_called = []
        collected_results = []
        tool_errors = ["Execution timed out after 20.0s"]
        llm_succeeded = False
        fallback_used = True
        has_data_unavailable = True
        data_unavailable_reason = "LLM_TIMEOUT"
    except Exception as exc:
        logger.error("Error executing info_agent_node: %s", exc, exc_info=True)
        llm_succeeded = False
        fallback_used = True
        tool_errors = [str(exc)]

        # Graceful degradation: Thử tra cứu thông tin chuyên khoa qua domain service khi LLM không khả dụng
        guardrail = get_guardrail_service()
        dept_resp = None
        if state.get("workflow_status") == "DEPARTMENT_INFO" or any(
            kw in query.lower() for kw in ["thông tin về", "chuyên khoa", "khoa ", "khia "]
        ):
            try:
                dept_resp, _ = guardrail.get_department_info_response(
                    dept_name_query=query,
                    language=state.get("language") or "vi",
                    enable_citation=True,
                )
            except Exception as d_exc:
                logger.warning("Department info fallback failed: %s", d_exc)
                dept_resp = None

        if dept_resp:
            final_text = dept_resp
            tools_called = [{"tool": "get_department_info", "input": {"department_key": query}}]
            collected_results = [{"tool": "get_department_info", "result": dept_resp}]
            has_data_unavailable = False
            data_unavailable_reason = None
        else:
            final_text = (
                "Dạ, hệ thống tra cứu thông tin đang gặp trục trặc tạm thời. "
                "Em chưa thể lấy dữ liệu ngay lúc này. Bác vui lòng thử lại sau ít phút nhé ạ."
            )
            tools_called = []
            collected_results = []
            has_data_unavailable = True
            data_unavailable_reason = f"ERROR: {type(exc).__name__}"

    # Yêu cầu 6: Disclaimer chỉ gắn khi dùng search_disease_knowledge hoặc nội dung bệnh học
    PATHOLOGY_KEYWORDS = [
        "bệnh lý", "bệnh học", "chẩn đoán", "phác đồ điều trị", "nguyên nhân gây bệnh",
        "triệu chứng bệnh", "biến chứng", "thuốc điều trị", "tác dụng phụ của thuốc",
    ]
    is_pathology = (
        any(tc["tool"] == "search_disease_knowledge" for tc in tools_called)
        or any(k in query.lower() for k in PATHOLOGY_KEYWORDS)
        or any(k in final_text.lower() for k in PATHOLOGY_KEYWORDS)
    )
    if is_pathology:
        if "Khuyến cáo y tế" not in final_text and "Medical Disclaimer" not in final_text:
            final_text += MEDICAL_DISCLAIMER_VI

    # Kiểm duyệt an toàn đầu ra qua DLPService
    dlp_service = get_dlp_service()
    sanitized_response = dlp_service.sanitize(final_text).sanitized_text

    # Yêu cầu 3: Đếm tokens và đọc usage_metadata của provider nếu có
    completion_tokens = token_counter.count_tokens(sanitized_response)
    if last_ai_msg and hasattr(last_ai_msg, "usage_metadata") and isinstance(last_ai_msg.usage_metadata, dict):
        u_meta = last_ai_msg.usage_metadata
        if u_meta.get("input_tokens"):
            prompt_tokens = int(u_meta["input_tokens"])
        if u_meta.get("output_tokens"):
            completion_tokens = int(u_meta["output_tokens"])

    total_tokens = prompt_tokens + completion_tokens
    latency_ms = round((time.monotonic() - start_time) * 1000, 2)

    # Yêu cầu 4: workflow_status nếu LLM lỗi/timeout đặt INFO_UNAVAILABLE
    workflow_status = "INFO_ANSWERED" if llm_succeeded else "INFO_UNAVAILABLE"

    # Lưu lại kết quả tool gần nhất (rút gọn <= 2KB)
    compacted_history_tools = _compact_tool_results(collected_results, max_bytes=2048)

    # Cập nhật và lưu giữ lịch sử hội thoại với cơ chế Compaction + SOAP Notes (RULE-CONV-00)
    from src.medical_assistant.domain.compaction_service import get_compaction_service

    history = list(state.get("messages") or [])
    if query:
        history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": sanitized_response})

    compaction_res = get_compaction_service().compact_conversation(
        history, state, recent_window_size=4
    )
    compacted_messages = compaction_res["recent_messages"]
    durable_soap_note = compaction_res["durable_soap_note"]

    # Yêu cầu 5: quick_replies sinh theo kết quả tra cứu hiện tại, không kế thừa metadata cũ
    if any(tc.get("tool") == "search_doctors" for tc in tools_called):
        quick_replies = ["Đặt lịch khám bác sĩ này", "Xem chi tiết bác sĩ", "Tra cứu bác sĩ khác"]
    elif any(tc.get("tool") == "list_facilities" for tc in tools_called):
        quick_replies = ["Danh sách chuyên khoa tại cơ sở", "Xem bác sĩ tại cơ sở", "Đặt lịch khám"]
    elif any(tc.get("tool") == "search_disease_knowledge" for tc in tools_called):
        quick_replies = ["Đặt lịch khám chuyên khoa", "Xem bác sĩ điều trị", "Tư vấn thêm triệu chứng"]
    elif has_data_unavailable:
        quick_replies = ["Gọi tổng đài 1900 232 389", "Thử lại sau ít phút", "Tra cứu thông tin khác"]
    else:
        quick_replies = ["Đặt lịch khám", "Tra cứu bác sĩ khác", "Cơ sở gần nhất"]

    structured_telemetry = {
        "route": "info_agent",
        "workflow_status": workflow_status,
        "action": "info_lookup",
        "tools_called": [tc["tool"] for tc in tools_called],
        "tool_errors": tool_errors,
        "llm_succeeded": llm_succeeded,
        "fallback_used": fallback_used,
        "data_unavailable": has_data_unavailable,
        "data_unavailable_reason": data_unavailable_reason,
        "latency_ms": latency_ms,
        "tokens": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens,
        },
    }
    logger.info("TURN_TELEMETRY: %s", json.dumps(structured_telemetry, ensure_ascii=False))

    new_meta = {
        "route": "info_agent",
        "tools_called": [tc["tool"] for tc in tools_called],
        "tools_details": tools_called,
        "tool_errors": tool_errors,
        "tokens": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "llm_succeeded": llm_succeeded,
        "fallback_used": fallback_used,
        "data_unavailable": has_data_unavailable,
        "data_unavailable_reason": data_unavailable_reason,
        "workflow_status": workflow_status,
        "quick_replies": quick_replies,
        "structured_telemetry": structured_telemetry,
        "latency_ms": latency_ms,
        "full_tool_results": collected_results,
    }

    # Yêu cầu 5: metadata merge chỉ giữ các khóa phiên cần bảo toàn
    existing_meta = dict(state.get("metadata") or {})
    PRESERVED_METADATA_KEYS = {"session_id", "patient_id", "patient_profile", "user_id", "thread_id", "client_ip", "locale", "device"}
    preserved_meta = {k: v for k, v in existing_meta.items() if k in PRESERVED_METADATA_KEYS}
    merged_meta = {**preserved_meta, **new_meta}

    return {
        "response": sanitized_response,
        "workflow_status": workflow_status,
        "last_tool_results": compacted_history_tools,
        "full_tool_results": collected_results,
        "metadata": merged_meta,
        "messages": compacted_messages,
        "durable_soap_note": durable_soap_note,
        "last_assistant_response": sanitized_response,
    }
