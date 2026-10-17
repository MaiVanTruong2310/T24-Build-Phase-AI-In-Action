# API Chat AI — VCare+ (P-124)

> Endpoint trò chuyện với trợ lý y tế và quản lý lịch sử hội thoại. Base URL: `/api/v1`.
> Căn cứ: `src/medical_assistant/api/routes.py`, schema `src/medical_assistant/domain/schemas.py`, `src/services/chat_history.py` (develop `42c909e`).
> Cách xác thực và định dạng lỗi chung: xem [README.md](README.md).

## Danh sách endpoint

| Method | Path | Quyền | Mục đích |
|---|---|---|---|
| POST | `/chat` | Khách / đăng nhập | Gửi tin nhắn, nhận câu trả lời đầy đủ (JSON) |
| POST | `/chat/stream` | Khách / đăng nhập | Gửi tin nhắn, nhận câu trả lời qua SSE |
| GET | `/chat/conversations` | Đăng nhập | Danh sách hội thoại |
| GET | `/chat/conversations/{session_id}` | Đăng nhập | Các lượt chat trong một hội thoại |
| DELETE | `/chat/conversations/{session_id}` | Đăng nhập | Xóa một hội thoại |
| GET | `/status` | Công khai | Trạng thái agent và nhà cung cấp LLM |

Gửi yêu cầu đặt lịch từ chat (`POST /booking-requests`) được mô tả trong tài liệu API đặt lịch.

## Khái niệm cần biết

| Khái niệm | Ý nghĩa |
|---|---|
| `session_id` | Mã **một cuộc hội thoại**. Mọi tin nhắn cùng `session_id` thuộc cùng một mạch, nên agent nhớ những gì đã nói. Frontend tự sinh khi bắt đầu hội thoại mới |
| `request_id` | Mã **một lượt gửi**. Gửi lại cùng `request_id` (ví dụ khi mất mạng) sẽ nhận lại **đúng câu trả lời cũ**, agent không chạy lại |
| Khách | Không đăng nhập; được nhận diện bằng cookie `coordination_guest`. Ngữ cảnh vẫn giữ trong phiên, nhưng **không có lịch sử để xem lại** |
| Người đã đăng nhập | Mỗi lượt được **lưu vào database**: tin nhắn, câu trả lời và trạng thái agent. Xem lại được, và ngữ cảnh không mất khi máy chủ khởi động lại |

---

## POST `/chat`: Gửi tin nhắn (JSON)

**Request body** (`ChatRequest`)

| Trường | Kiểu | Bắt buộc | Ràng buộc / mặc định |
|---|---|---|---|
| `message` | string | **Có** | 1–5000 ký tự |
| `session_id` | string | Không | 1–200 ký tự, chỉ gồm `A-Z a-z 0-9 _ -`; bỏ trống thì tạo mới (UUID) |
| `request_id` | UUID | Không | Bỏ trống thì tạo mới. **Nên tự sinh** ở client để chống gửi trùng |
| `patient_profile` | object | Không | Thông tin khách: `name` (2–120 ký tự), `phone` (≤ 20), `date_of_birth`, `gender` |
| `patient_profile_id` | UUID | Không | Chat thay cho một hồ sơ người thân (người đã đăng nhập) |
| `enable_citation` | bool | Không | Mặc định `true`: hiện link nguồn (hồ sơ bác sĩ, tài liệu) |
| `user_id` | string | Không | Không cần gửi; backend lấy từ phiên đăng nhập |

**Ví dụ curl** (khách)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{
        "session_id": "demo-session-001",
        "request_id": "3f2b8c1e-5d4a-4e9b-8a7c-1d2e3f4a5b6c",
        "message": "Tôi bị đau đầu 3 ngày nay, hơi chóng mặt",
        "patient_profile": { "name": "Nguyễn Văn An", "phone": "0912345678" }
      }'
```

`-c/-b cookies.txt` giữ cookie khách `coordination_guest` giữa các lần gọi, để các tin nhắn sau được hiểu là cùng một người.

**Ví dụ curl** (đã đăng nhập bằng Bearer)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"session_id": "demo-session-002", "message": "Tôi muốn xem lịch khám Thần kinh tuần này"}'
```

**Response `200`** (`ChatResponse`, trả trực tiếp, **không** bọc khung `data` chung). Các con số dưới đây là **giá trị minh họa**:

```json
{
  "response": "Dạ, em đã ghi nhận triệu chứng của bác. Bác cho em hỏi cụ thể hơn: cơn đau đầu ở vị trí nào ...\n\n---\n*Khuyến cáo y tế: Thông tin chỉ mang tính chất định hướng ...*",
  "analysis": "",
  "session_id": "demo-session-001",
  "ats_level": 4,
  "max_booking_days": 7,
  "quick_replies": ["Đau nửa đầu", "Đau sau gáy", "Đau cả đầu"],
  "is_emergency": false,
  "token_usage": {
    "prompt_tokens": 412, "completion_tokens": 124, "total_tokens": 536,
    "tokens_saved": 0, "llm_calls": 1, "estimated_cost_usd": 0.00027,
    "model": "deepseek-chat", "execution_mode": "llm_or_estimated"
  },
  "workflow_status": "PROBING_IN_PROGRESS",
  "booking_intake": null,
  "suggested_department": "Thần kinh",
  "candidate_specialties": [],
  "conflict_reason": null,
  "acuity_status": null,
  "disposition": null,
  "elapsed_ms": 6817.6,
  "timings_ms": { "db_before_turn": 41.2, "agent_graph": 6720.5 }
}
```

### Các trường quan trọng trong phản hồi

| Trường | Dùng để |
|---|---|
| `response` | Nội dung hiển thị cho bệnh nhân (Markdown), đã kèm khuyến cáo y tế khi có ngữ cảnh lâm sàng |
| `is_emergency` | `true` → giao diện phải hiển thị cảnh báo cấp cứu và nút gọi 115, **ẩn mọi lựa chọn đặt lịch** |
| `ats_level` | Mức khẩn cấp 1–5 (1 gấp nhất) |
| `max_booking_days` | Được đặt lịch xa nhất bao nhiêu ngày. `0` nghĩa là không được đặt lịch thường |
| `quick_replies` | Các nút trả lời nhanh gợi ý cho bệnh nhân |
| `suggested_department` | Chuyên khoa được đề xuất |
| `candidate_specialties`, `conflict_reason` | Khi nhiều nhóm triệu chứng: các chuyên khoa đang cân nhắc và lý do cần hỏi thêm |
| `booking_intake` | Khác `null` → giao diện mở **form đặt lịch** với các trường AI đã điền sẵn |
| `workflow_status` | Trạng thái nghiệp vụ (xem bảng dưới) |
| `token_usage` | Số token và chi phí ước tính của lượt này |
| `elapsed_ms`, `timings_ms` | Thời gian xử lý; `timings_ms` gồm `db_before_turn` (chuẩn bị lượt chat trong database), `agent_graph` (agent xử lý) và thời gian từng bước |

### Các giá trị `workflow_status` thường gặp

| Giá trị | Ý nghĩa | Giao diện nên làm gì |
|---|---|---|
| `PROBING_IN_PROGRESS` | Đang hỏi làm rõ triệu chứng | Hiển thị câu hỏi + `quick_replies` |
| `TRIAGED_AWAITING_SCHEDULE` | Đã xác định chuyên khoa, chờ bệnh nhân muốn xem lịch | Gợi ý "Xem lịch khám" |
| `TRIAGED_READY_FOR_BOOKING` | Đã có danh sách bác sĩ / lịch | Hiển thị bác sĩ, khung giờ |
| `BOOKING_CONTACT_REQUIRED` | Cần thông tin liên hệ để đặt lịch | Mở form đặt lịch |
| `EMERGENCY` | **Cấp cứu** | Cảnh báo đỏ, nút gọi 115, khóa đặt lịch |
| `GUARDRAIL_DIAGNOSIS` / `GUARDRAIL_MEDICATION` | Bệnh nhân hỏi chẩn đoán / xin thuốc | Hiển thị câu từ chối + hướng chuyên khoa |
| `SECURITY_BLOCKED` | Nội dung tấn công bị chặn | Hiển thị câu trả lời an toàn |
| `VISIT_PURPOSE_CLARIFICATION` | Chưa rõ mục đích khám | Hiển thị các lựa chọn mục đích |
| `FAQ_ANSWERED`, `DEPARTMENT_INFO`, `FACILITY_INFO` | Trả lời thông tin chung | Hiển thị bình thường |
| `HUMAN_HELP_REQUESTED` | Bệnh nhân muốn gặp người thật | Chuyển sang luồng chờ điều phối viên |
| `HUMAN_TAKEOVER` | Điều phối viên đang tiếp quản | Hiển thị tin nhắn chờ, nhận trả lời của nhân viên qua WebSocket |

### Khi điều phối viên đang tiếp quản

Nếu phiên đang ở chế độ người thật tiếp quản, AI **không** trả lời. `/chat` trả `workflow_status = "HUMAN_TAKEOVER"` với `response`: "Tin nhắn đã được chuyển đến bác sĩ điều phối. Bạn sẽ nhận phản hồi trong cuộc hội thoại này." (`src/services/coordinator_chat.py`). Riêng **kiểm tra cấp cứu vẫn chạy**: tin nhắn có dấu hiệu nguy hiểm vẫn nhận cảnh báo cấp cứu ngay.

### Lỗi thường gặp

| HTTP | `error_code` | Khi nào |
|---|---|---|
| 400 | `VALIDATION_ERROR` | `message` rỗng hoặc dài quá 5000 ký tự, `session_id` có ký tự không hợp lệ |
| 401 | `UNAUTHORIZED` | Gửi kèm header `X-Session-Expected: 1` nhưng phiên đăng nhập đã hết hạn ("Cần gia hạn phiên đăng nhập.") |
| 409 | `CONFLICT` | "Cuộc trò chuyện đang xử lý một tin nhắn. Vui lòng đợi.": gửi tin mới khi tin trước chưa xử lý xong |
| 409 | `CONFLICT` | "Mã lượt chat đã được dùng cho một tin nhắn khác.": dùng lại `request_id` với nội dung khác |
| 409 | `CONFLICT` | "Hội thoại đã thuộc hồ sơ khác. Hãy mở hội thoại mới.": đổi `patient_profile_id` giữa chừng |
| 503 | `INTERNAL_ERROR` | "Đã có lỗi xảy ra. Vui lòng thử lại sau.": không lưu được lượt chat (ví dụ mất kết nối database). Code ném thông báo chi tiết hơn nhưng bộ xử lý lỗi **ẩn message của mọi lỗi 5xx** |

---

## POST `/chat/stream`: Gửi tin nhắn (SSE)

Request **giống hệt** `/chat`. Phản hồi là luồng **Server-Sent Events** (`Content-Type: text/event-stream`).

**Ví dụ curl** (`-N` để curl in từng sự kiện ngay khi nhận):

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -c cookies.txt -b cookies.txt \
  -d '{"session_id": "demo-session-003", "message": "tức ngực, khó thở, vã mồ hôi"}'
```

**Luồng sự kiện mẫu:**

```text
data: {"type": "init", "session_id": "demo-session-003"}

: keep-alive

data: {"type": "token", "content": "🚨 CẢNH BÁO CẤP TÍNH (...): Vui lòng gọi 115 hoặc đến ngay phòng Cấp cứu ...\n"}

data: {"type": "token", "content": "---\n"}

data: {"type": "metadata", "ats_level": 2, "is_emergency": true, "workflow_status": "EMERGENCY", "max_booking_days": 0, "quick_replies": ["Gọi cấp cứu 115 ngay", "Đến phòng Cấp cứu gần nhất"], ...}

data: [DONE]
```

### Các loại sự kiện

| Sự kiện | Khi nào | Nội dung |
|---|---|---|
| `{"type": "init"}` | Ngay khi bắt đầu | `session_id` của phiên |
| `: keep-alive` | Cứ **5 giây** một lần trong lúc agent đang xử lý | Dòng chú thích SSE, client **bỏ qua**. Giúp kết nối không bị proxy cắt |
| `{"type": "token"}` | Sau khi agent xử lý xong | `content` là **một dòng** của câu trả lời (giữ ký tự xuống dòng). Ghép lần lượt các `content` để có câu trả lời đầy đủ |
| `{"type": "metadata"}` | Sau token cuối | Mọi trường của `ChatResponse` **trừ** `response`, `analysis`, `session_id` |
| `[DONE]` | Kết thúc | Đóng luồng |
| `{"type": "error"}` | Khi lỗi | `message`: "Không thể hoàn tất hoặc lưu hội thoại. Vui lòng thử lại." Sau sự kiện này luồng **kết thúc luôn, không có `[DONE]`**. HTTP status vẫn là **200** vì luồng đã bắt đầu, nên client phải dựa vào sự kiện `error` để biết lỗi |

### Lưu ý quan trọng về streaming

- **Đây không phải streaming theo từng token của LLM.** Backend **xử lý xong và lưu toàn bộ lượt chat** rồi mới gửi câu trả lời, chia theo **từng dòng**. Mục đích là đảm bảo lượt chat luôn được lưu trước khi bệnh nhân thấy câu trả lời.
- Vì vậy thời gian chờ trước sự kiện `token` đầu tiên bằng thời gian xử lý của agent, thường 5–10 giây. Trong lúc đó client chỉ nhận `keep-alive`, nên giao diện nên hiển thị trạng thái "đang soạn trả lời".
- Nếu client **ngắt kết nối** giữa chừng, backend hủy việc xử lý của lượt đó.
- Header phản hồi có `Cache-Control: no-cache` và `X-Accel-Buffering: no` để Nginx không gom dữ liệu lại.

---

## GET `/chat/conversations`: Danh sách hội thoại

**Quyền:** đã đăng nhập. **Query:**

| Tham số | Mặc định | Ràng buộc |
|---|---|---|
| `limit` | 30 | 1–100 |
| `offset` | 0 | ≥ 0 |
| `patient_profile_id` | — | Lọc theo hồ sơ người thân |

```bash
curl http://localhost:8000/api/v1/chat/conversations?limit=10 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response `200`** (trả trực tiếp, không bọc khung chung):

```json
{
  "conversations": [
    {
      "id": "8d3f...",
      "session_id": "demo-session-002",
      "title": "Tôi muốn xem lịch khám Thần kinh tuần này",
      "created_at": "2026-10-10T08:12:03Z",
      "updated_at": "2026-10-10T08:14:40Z"
    }
  ],
  "has_more": false
}
```

`has_more = true` nghĩa là còn trang sau; gọi tiếp với `offset` tăng thêm `limit`.

---

## GET `/chat/conversations/{session_id}`: Nội dung hội thoại

**Quyền:** đã đăng nhập (chỉ xem được hội thoại của chính mình). **Query:** `limit` (mặc định 50, 1–100), `offset`.

```bash
curl http://localhost:8000/api/v1/chat/conversations/demo-session-002 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response `200`:**

```json
{
  "title": "Tôi muốn xem lịch khám Thần kinh tuần này",
  "turns": [
    {
      "id": "c1a2...",
      "request_id": "3f2b8c1e-5d4a-4e9b-8a7c-1d2e3f4a5b6c",
      "user_text": "Tôi muốn xem lịch khám Thần kinh tuần này",
      "assistant_text": "Dạ, em tìm được các bác sĩ Thần kinh ...",
      "result": { "response": "...", "workflow_status": "TRIAGED_READY_FOR_BOOKING", "...": "..." },
      "status": "completed",
      "created_at": "2026-10-10T08:12:03+00:00"
    }
  ],
  "has_more": false
}
```

- Mỗi phần tử `turns` là **một cặp** câu hỏi của bệnh nhân và câu trả lời của trợ lý.
- `result` chứa phản hồi đầy đủ của lượt đó, giúp giao diện dựng lại thẻ bác sĩ, nút trả lời nhanh… khi mở lại hội thoại.
- `limit` lấy các lượt **gần nhất**.
- Hội thoại không tồn tại vẫn trả `200` với `{"title": "Cuộc trò chuyện mới", "turns": [], "has_more": false}`.

---

## DELETE `/chat/conversations/{session_id}`: Xóa hội thoại

**Quyền:** đã đăng nhập (chỉ xóa hội thoại của chính mình).

```bash
curl -X DELETE http://localhost:8000/api/v1/chat/conversations/demo-session-002 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response `200`:** `{"deleted": true}`

---

## GET `/status`: Trạng thái agent

**Quyền:** công khai.

```json
{
  "status": "ready",
  "agent": "LangGraph Clinical Triage Agent v1.0",
  "features": ["session_memory", "sse_streaming", "ats_triage"],
  "llm_health": { "...": "trạng thái từng nhà cung cấp LLM" }
}
```

Khi chưa cấu hình key LLM, `llm_health` chứa thông báo lỗi tương ứng.

> ⚠️ `POST /chat` và `GET /status` còn được khai báo **trùng** trong `src/api/routes.py` (agent cũ). Bản đó không bao giờ chạy vì FastAPI dùng route khai báo trước. Xem [endpoints.md](endpoints.md).

---

## Gợi ý tích hợp phía giao diện

1. **Sinh `request_id` mới cho mỗi tin nhắn** và giữ nguyên khi gửi lại do lỗi mạng, để không tạo câu trả lời trùng.
2. **Khóa ô nhập** trong lúc chờ câu trả lời; gửi chồng sẽ nhận 409.
3. **Luôn xử lý `is_emergency = true` trước tiên**: hiện cảnh báo đỏ, nút gọi 115, ẩn đặt lịch.
4. Với SSE, **bỏ qua dòng bắt đầu bằng `:`** (keep-alive), và dùng sự kiện `metadata` để cập nhật giao diện (chuyên khoa, nút trả lời nhanh, form đặt lịch).
