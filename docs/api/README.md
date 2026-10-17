# Tài liệu API — VCare+ (P-124)

> Tổng quan API backend: địa chỉ, cách xác thực, định dạng phản hồi và mã lỗi.
> Căn cứ: code nhánh `develop` (commit `42c909e`, 10/10/2026). Định dạng phản hồi và lỗi trong tài liệu này được **chụp từ request thật** gửi tới ứng dụng.

## Mục lục tài liệu API

| File | Nội dung |
|---|---|
| [endpoints.md](endpoints.md) | Danh sách đầy đủ 130 endpoint, kèm mức quyền |
| README.md (file này) | Tổng quan, xác thực, định dạng phản hồi, mã lỗi |
| [auth.md](auth.md) | Đăng ký, xác nhận email, đăng nhập, phiên, hồ sơ người dùng |
| [chat.md](chat.md) | Chat AI, streaming SSE, lịch sử hội thoại |
| [booking.md](booking.md) | Giữ chỗ, đặt lịch, hủy, đổi lịch, duyệt lịch, sơ đồ trạng thái |
| [staff.md](staff.md) | Bàn điều phối, tiếp quản chat, lịch tư vấn, danh mục, gói khám |
| [zalo.md](zalo.md) | Zalo Bot: webhook, cấu hình, giới hạn tin nhắn, vấn đề bảo mật |

---

## 1. Tổng quan

- **Kiểu API:** REST (JSON), cộng thêm **SSE** cho chat streaming và **WebSocket** cho tiếp quản chat.
- **Framework:** FastAPI. Tài liệu tương tác tự sinh ở `/docs` (Swagger UI) và `/openapi.json`.
- **Tiền tố:** mọi endpoint nghiệp vụ nằm dưới `/api/v1`. Ngoại lệ: `/`, `/health`, `/health/ready`.
- **Định dạng thời gian:** ISO 8601, múi giờ UTC (ví dụ `2026-10-10T09:24:25.501682Z`).
- **Ngôn ngữ thông báo:** phần lớn là tiếng Việt; một số lỗi chung là tiếng Anh (ví dụ `Request validation failed`).

## 2. Base URL

| Môi trường | Base URL | Ghi chú |
|---|---|---|
| Máy cá nhân | `http://localhost:8000/api/v1` | Chạy `uvicorn src.main:app --port 8000` |
| Dev / Production | Theo biến `VITE_API_BASE_URL` của frontend | Frontend tự thêm `/api/v1` (`frontend/src/app/apiClient.ts`) |

Kiểm tra dịch vụ:

| Endpoint | Ý nghĩa | Phản hồi mẫu |
|---|---|---|
| `GET /health` | Tiến trình còn sống | `{"status": "ok", "env": "test"}` |
| `GET /health/ready` | Kết nối được database | `200 {"status": "ready", "database": "connected"}`; mất database → `503` với `error_code` `INTERNAL_ERROR` |
| `GET /api/v1/status` | Trạng thái agent và nhà cung cấp LLM | `{"status": "ready", "agent": "...", "features": [...], "llm_health": {...}}` |

## 3. Xác thực

Hệ thống hỗ trợ **2 cách gửi token**. Backend chấp nhận cả hai cách cho cùng một endpoint.

### 3.1. Cookie (cách frontend web đang dùng)

1. Gửi `POST /api/v1/auth/login` kèm header `X-Auth-Transport: cookie`.
2. Backend đặt 2 cookie và trả `{"authenticated": true, "expires_in": ...}` (không trả token trong body):

| Cookie | Nội dung | Thuộc tính |
|---|---|---|
| `p124_access` | Access token (JWT), hết hạn theo `expires_in` do Supabase cấp (mặc định 1 giờ) | `HttpOnly`; `Secure` trên production; `SameSite` theo cấu hình |
| `p124_refresh` | Refresh token, sống **30 ngày** | Như trên |

3. Các request sau gửi kèm cookie (trên trình duyệt: `credentials: 'include'`).
4. Khi nhận **401**, gọi `POST /api/v1/auth/refresh-token` để lấy access token mới rồi gửi lại request. Frontend đã tự làm việc này.
5. `POST /api/v1/auth/logout` hủy phiên và xóa cookie.

**Chống giả mạo request (CSRF):** request **ghi dữ liệu** (khác `GET`/`HEAD`/`OPTIONS`) dùng cookie phải có header `Origin` nằm trong `CORS_ORIGINS`. Nếu sai, backend trả **403** (xem mục 5.3).

### 3.2. Bearer token (ứng dụng khác, Postman, test)

1. Gửi `POST /api/v1/auth/login` **không** kèm `X-Auth-Transport`. Body trả về chứa token:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "....",
  "token_type": "bearer",
  "expires_in": 900
}
```

2. Gửi các request sau với header:

```
Authorization: Bearer <access_token>
```

### 3.3. Khách chưa đăng nhập

Một số endpoint (chat, gửi yêu cầu đặt lịch, SOS, theo dõi phiên) cho phép khách. Backend tự cấp cookie **`coordination_guest`** để nhận diện khách qua các request, nên khách không cần làm gì thêm.

### 3.4. WebSocket tiếp quản chat

Trình duyệt không gửi header `Authorization` được qua WebSocket, nên:
1. Gọi `GET /api/v1/staff/chat-takeover/ticket` (cần đăng nhập) để lấy vé.
2. Mở WebSocket kèm `?token=<vé>`.

### 3.5. Mức quyền

| Mức | Ai được gọi |
|---|---|
| Công khai | Mọi người |
| Khách / đăng nhập | Khách (cookie `coordination_guest`) hoặc người đã đăng nhập |
| Đăng nhập | Mọi tài khoản đã đăng nhập |
| Bệnh nhân | `role = "patient"` |
| Staff | `role = "staff"` |
| Quản trị | Staff có `is_admin`, không giới hạn cơ sở |

Chi tiết từng endpoint: [endpoints.md](endpoints.md).

## 4. Định dạng phản hồi thành công

Phần lớn endpoint trả về **khung chung**:

```json
{
  "timestamp": "2026-10-10T09:24:25.501682Z",
  "error": null,
  "message": "Success",
  "status": 200,
  "data": { "...": "dữ liệu thật nằm ở đây" }
}
```

| Trường | Ý nghĩa |
|---|---|
| `timestamp` | Thời điểm tạo phản hồi (UTC) |
| `error` | Luôn `null` khi thành công |
| `message` | Thông điệp ngắn |
| `status` | Mã HTTP (lặp lại để client tiện đọc) |
| `data` | Dữ liệu trả về (object, mảng hoặc `null`) |

**Ngoại lệ, endpoint trả object trực tiếp không bọc khung:** `POST /chat` (trả `ChatResponse`), `GET /status`, `GET /zalo/status`, `GET /health`, và luồng SSE `POST /chat/stream`. Client cần xử lý riêng các endpoint này.

## 5. Định dạng lỗi

### 5.1. Định dạng chuẩn

Mọi lỗi (trừ trường hợp ở 5.3) có dạng:

```json
{
  "error_code": "NOT_AUTHENTICATED",
  "message": "Vui lòng đăng nhập."
}
```

| Trường | Ý nghĩa |
|---|---|
| `error_code` | Mã lỗi **ổn định**, dùng để lập trình xử lý (xem mục 6) |
| `message` | Thông báo cho người dùng, có thể thay đổi |

Client nên dựa vào **`error_code` + mã HTTP**, không dựa vào nội dung `message`.

### 5.2. Ví dụ thật

| Tình huống | HTTP | Phản hồi |
|---|---|---|
| Gọi API cần đăng nhập mà không có token | 401 | `{"error_code": "NOT_AUTHENTICATED", "message": "Vui lòng đăng nhập."}` |
| Body sai cấu trúc | 400 | `{"error_code": "VALIDATION_ERROR", "message": "Request validation failed"}` |
| Đường dẫn không tồn tại | 404 | `{"error_code": "NOT_FOUND", "message": "Not Found"}` |
| Database không kết nối được | 503 | `{"error_code": "DATABASE_UNAVAILABLE", "message": "Service temporarily unavailable"}` |
| Dịch vụ xác thực không kết nối được | 503 | `{"error_code": "AUTH_UNAVAILABLE", "message": "Không thể kết nối dịch vụ xác thực. Vui lòng thử lại sau."}` |
| Xung đột nghiệp vụ (ví dụ ca đã có người nhận) | 409 | `{"error_code": "CONFLICT", "message": "Ca đã có người phụ trách."}` |

### 5.3. Ngoại lệ: lỗi chặn Origin

Lỗi CSRF từ `CookieOriginMiddleware` dùng **định dạng khác**:

```json
{ "code": 403, "message": "Nguồn yêu cầu không hợp lệ.", "data": null }
```

### 5.4. Lưu ý khi xử lý lỗi

- **Lỗi kiểm tra dữ liệu trả 400, không phải 422** như mặc định của FastAPI, và **không cho biết trường nào sai**. Khi debug, đối chiếu body với schema trong `/docs`.
- Các lỗi nghiệp vụ trong phần điều phối dùng `HTTPException`. Mã HTTP được chuyển thành `error_code` như sau:

| HTTP | `error_code` |
|---|---|
| 401 | `UNAUTHORIZED` (thiếu token ở dependency xác thực thì là `NOT_AUTHENTICATED`) |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 422 | `HTTP_ERROR` (lý do cụ thể nằm trong `message`) |
| 429 | `RATE_LIMITED` |
| 500, 503 và các lỗi 5xx khác | `INTERNAL_ERROR`, message luôn là "Đã có lỗi xảy ra. Vui lòng thử lại sau." (không lộ chi tiết lỗi nội bộ). Ngoại lệ: lỗi do code tự phân loại vẫn giữ mã riêng, ví dụ `DATABASE_UNAVAILABLE`, `AUTH_UNAVAILABLE` |

Bảng trên được kiểm chứng bằng cách gọi thật từng mã lỗi.

## 6. Mã lỗi

Toàn bộ **78 mã lỗi** được định nghĩa trong `src/core/error_codes.py` (`ErrorCode`). Các mã thường gặp:

### Chung

| Mã | HTTP thường gặp | Ý nghĩa |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Dữ liệu gửi lên không đúng cấu trúc |
| `HTTP_ERROR` | 422 | Lỗi nghiệp vụ không có mã riêng; xem `message` |
| `NOT_FOUND` | 404 | Không tìm thấy đối tượng / đường dẫn |
| `CONFLICT` | 409 | Xung đột trạng thái |
| `FORBIDDEN` | 403 | Không đủ quyền |
| `RATE_LIMITED` | 429 | Gọi quá nhiều lần |
| `DATABASE_UNAVAILABLE` | 503 | Mất kết nối database |
| `INTERNAL_ERROR` | 500 | Lỗi không mong muốn |

### Xác thực & tài khoản

| Mã | Ý nghĩa |
|---|---|
| `NOT_AUTHENTICATED` | Chưa đăng nhập |
| `INVALID_TOKEN` | Access token không hợp lệ |
| `INVALID_CREDENTIALS` | Sai tài khoản hoặc mật khẩu |
| `INVALID_REFRESH_TOKEN`, `REFRESH_TOKEN_EXPIRED`, `REFRESH_TOKEN_REUSE` | Refresh token sai, hết hạn hoặc bị dùng lại (dấu hiệu bị đánh cắp) |
| `INVALID_OTP`, `OTP_EXPIRED`, `OTP_ATTEMPTS_EXCEEDED` | OTP sai, hết hạn, nhập sai quá số lần |
| `ACCOUNT_EXISTS`, `PHONE_EXISTS` | Tài khoản / số điện thoại đã tồn tại |
| `ACCOUNT_DISABLED`, `ACCOUNT_INACTIVE`, `EMAIL_NOT_CONFIRMED` | Tài khoản bị khóa, chưa kích hoạt, chưa xác nhận email |
| `AUTH_UNAVAILABLE` | Không kết nối được dịch vụ xác thực |
| `SESSION_NOT_FOUND` | Phiên đăng nhập không tồn tại |

### Đặt lịch

| Mã | Ý nghĩa |
|---|---|
| `BOOKING_ALREADY_CANCELLED` | Lịch đã hủy |
| `BOOKING_NOT_CANCELLABLE` | Lịch không hủy được (ví dụ đã bị từ chối) |
| `BOOKING_NOT_RESCHEDULABLE` | Lịch không đổi được |
| `BOOKING_ALREADY_REVIEWED` | Lịch đã được duyệt / từ chối |
| `BOOKING_EXPIRED` | Lịch đã hết hạn |
| `BOOKING_CREATE_CONFLICT` | Xung đột khi tạo lịch |
| `CAPACITY_EXCEEDED` | Khung giờ đã hết chỗ |
| `IDEMPOTENCY_KEY_REQUIRED`, `IDEMPOTENCY_KEY_REUSED` | Thiếu hoặc dùng lại khóa chống tạo trùng |
| `DOCTOR_BUSY`, `DOCTOR_UNAVAILABLE`, `DOCTOR_BOOKING_DISABLED`, `DOCTOR_INACTIVE` | Bác sĩ bận, không có lịch, tắt nhận lịch, ngừng hoạt động |
| `FACILITY_INACTIVE`, `FACILITY_NOT_AVAILABLE`, `FACILITY_UNAVAILABLE` | Cơ sở không khả dụng |
| `GROUP_SERVICE_BOOKING_NOT_ALLOWED` | Không đặt được dịch vụ nhóm theo cách này |

### Danh mục & hồ sơ

| Mã | Ý nghĩa |
|---|---|
| `CODE_EXISTS`, `FACILITY_CODE_EXISTS`, `LICENSE_EXISTS` | Mã / số giấy phép đã tồn tại |
| `DOCTOR_CREATE_CONFLICT`, `FACILITY_ASSIGNMENT_UPDATE_CONFLICT` | Xung đột khi tạo / cập nhật |
| `PROFILE_BOUND`, `PROFILE_CONFLICT`, `PATIENT_IDENTITY_CONFLICT` | Xung đột hồ sơ bệnh nhân |
| `PATIENT_REQUIRED`, `PATIENT_NOT_ALLOWED` | Thiếu / không được phép với hồ sơ bệnh nhân này |

Danh sách đầy đủ: `src/core/error_codes.py`.

## 7. Điểm chưa thống nhất trong API

| # | Vấn đề | Ảnh hưởng |
|---|---|---|
| 1 | Một số endpoint không dùng khung phản hồi chung (mục 4) | Client phải viết code đọc riêng cho từng loại |
| 2 | Lỗi chặn Origin dùng định dạng `{code, message, data}` khác các lỗi khác (mục 5.3) | Client đọc `error_code` sẽ không thấy |
| 3 | Lỗi kiểm tra dữ liệu trả 400 và không có chi tiết trường sai (mục 5.4) | Khó debug, giao diện không chỉ ra được ô nhập sai |
| 4 | `HTTPException(422)` chuyển thành mã chung `HTTP_ERROR` | Client không phân biệt được các lỗi 422 khác nhau |

## 8. Kiểm chứng với server thật

Ngày 10/10/2026, nhóm chạy `uvicorn src.main:app` (develop `42c909e`) trên máy cá nhân, **không kết nối database và không có key LLM**, rồi gọi 15 request tới 8 nhóm endpoint chính:

| # | Request | Kết quả thật | Khớp tài liệu |
|---|---|---|---|
| 1 | `GET /health` | `200 {"status":"ok","env":"development"}` | ✅ |
| 2 | `GET /health/ready` (không có DB) | `503 INTERNAL_ERROR` | ⚠️ đã sửa (trước ghi `DATABASE_UNAVAILABLE`) |
| 3 | `GET /api/v1/status` | `200`, `llm_health` báo chưa cấu hình LLM | ✅ |
| 4 | `GET /api/v1/users/me` (không token) | `401 NOT_AUTHENTICATED` | ✅ |
| 5 | `POST /api/v1/auth/login` thiếu mật khẩu | `400 VALIDATION_ERROR` | ✅ |
| 6 | `POST /api/v1/auth/login` có trường thừa | `400 VALIDATION_ERROR` | ✅ |
| 7 | `POST /api/v1/chat` (không có DB) | `503 INTERNAL_ERROR` | ⚠️ đã sửa (trước ghi message chi tiết) |
| 8 | `POST /api/v1/chat/stream` (không có DB) | `200`, sự kiện `init` rồi `error`, không có `[DONE]` | ⚠️ đã bổ sung |
| 9 | `POST /api/v1/chat`, `session_id` có dấu | `400 VALIDATION_ERROR` | ✅ |
| 10 | `POST /api/v1/bookings` (không token) | `401 NOT_AUTHENTICATED` | ✅ |
| 11 | `POST /api/v1/booking-requests`, `consent_to_contact=false` | `422 HTTP_ERROR` "Cần đồng ý để điều phối viên liên hệ." | ✅ |
| 12 | `GET /api/v1/staff/bookings` (không token) | `401 NOT_AUTHENTICATED` | ✅ |
| 13 | `GET /api/v1/zalo/status` | `200`, đúng 5 trường như tài liệu | ✅ |
| 14 | `POST /api/v1/auth/logout` với `Origin` lạ | `403 {"code":403,"message":"Nguồn yêu cầu không hợp lệ.","data":null}` | ✅ |
| 15 | `GET /docs` | `200`, Swagger UI | ✅ |

**Giới hạn của lần kiểm chứng:** máy thử không có PostgreSQL (Docker chưa chạy) và không có Supabase. Vì vậy **luồng thành công** của chat, đặt lịch, bàn điều phối và đăng nhập chưa được gọi thật: phần đó trong tài liệu được lập từ code và schema. Cần chạy lại khi có môi trường đầy đủ (`docker compose up`).
