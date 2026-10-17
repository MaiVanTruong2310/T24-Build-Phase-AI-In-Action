# Danh sách Endpoint — VCare+ (P-124)

> Toàn bộ endpoint mà `src/main.py` gắn vào ứng dụng FastAPI, nhánh `develop` (commit `42c909e`, 10/10/2026).
>
> **Cách lập:** nạp trực tiếp ứng dụng FastAPI rồi duyệt cây dependency của từng route (không đọc code thủ công), sau đó đọc thêm các handler tự kiểm tra quyền bên trong. Mọi endpoint có tiền tố `/api/v1`, trừ nhóm "Hệ thống".

## Mức quyền

| Mức quyền | Nghĩa | Dependency trong code |
|---|---|---|
| Công khai | Ai cũng gọi được | — |
| Khách / đăng nhập | Khách (nhận diện bằng mã khách) hoặc người đã đăng nhập | `optional_chat_user`, `get_optional_user`, `patient_identity` |
| Đăng nhập | Mọi tài khoản đã đăng nhập (bệnh nhân hoặc nhân viên) | `get_current_user` |
| Bệnh nhân | Tài khoản `role = "patient"` | `require_patient`, `require_patient_for_hold` |
| Staff | Tài khoản `role = "staff"` | `require_staff` |
| Staff (thành viên điều phối) | Staff và là thành viên điều phối đang hoạt động | `access` (`src/api/endpoints/workbench.py`) |
| Quản trị | Staff có `is_admin`, không giới hạn cơ sở | `require_coordination_admin` hoặc kiểm tra trong handler |
| Zalo (secret header) | Chỉ nền tảng Zalo, xác thực bằng header `x-bot-api-secret-token` | Kiểm tra trong handler |

Ký hiệu: ⚠️ = vấn đề phân quyền cần xem lại (xem mục cuối) · 🔁 = đường dẫn bị khai báo trùng, route này **không bao giờ được gọi**.

## Tổng hợp

| Mức quyền | Số endpoint |
|---|---|
| Công khai | 26 (3 ⚠️) |
| Khách / đăng nhập | 10 |
| Đăng nhập | 20 (1 ⚠️) |
| Bệnh nhân | 13 |
| Staff | 32 |
| Staff (thành viên điều phối) | 17 |
| Quản trị | 11 |
| Zalo (secret header) | 1 |
| **Tổng** | **130** |

## Danh sách theo module

### Chat AI (8)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/chat` | Khách / đăng nhập | `chat` |
| POST | `/api/v1/chat/stream` | Khách / đăng nhập | `chat_stream` |
| GET | `/api/v1/chat/conversations` | Đăng nhập | `conversations` |
| DELETE | `/api/v1/chat/conversations/{session_id}` | Đăng nhập | `delete_conversation` |
| GET | `/api/v1/chat/conversations/{session_id}` | Đăng nhập | `conversation_messages` |
| POST | `/api/v1/booking-requests` | Khách / đăng nhập | `create_booking_request` |
| GET | `/api/v1/status` | Công khai | `agent_status` |
| GET | `/api/v1/admin/metrics/daily` | Công khai ⚠️ | `daily_metrics` |

### Agent dự phòng (route trùng) (2)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/chat` 🔁 | Công khai | `chat` |
| GET | `/api/v1/status` 🔁 | Công khai | `agent_status` |

### Xác thực & người dùng (15)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Công khai | `register` |
| POST | `/api/v1/auth/otp/send` | Công khai | `send_otp` |
| POST | `/api/v1/auth/otp/verify` | Công khai | `verify_otp` |
| POST | `/api/v1/auth/forgot-password` | Công khai | `forgot_password` |
| POST | `/api/v1/auth/reset-password` | Công khai | `reset_password` |
| PUT | `/api/v1/auth/password` | Đăng nhập | `change_password` |
| POST | `/api/v1/auth/login` | Công khai | `login` |
| POST | `/api/v1/auth/refresh-token` | Công khai | `refresh_token` |
| POST | `/api/v1/auth/logout` | Công khai | `logout` |
| GET | `/api/v1/users/me` | Đăng nhập | `get_me` |
| PATCH | `/api/v1/users/me` | Bệnh nhân | `update_me` |
| GET | `/api/v1/users/me/portrait` | Đăng nhập | `get_portrait` |
| PATCH | `/api/v1/users/me/portrait` | Bệnh nhân | `update_portrait` |
| GET | `/api/v1/users/{user_id}` | Staff | `get_user_by_id` |
| GET | `/api/v1/patients/me` | Đăng nhập | `get_me` |

### Hồ sơ người thân (4)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/patient-profiles` | Bệnh nhân | `profiles` |
| POST | `/api/v1/patient-profiles` | Bệnh nhân | `add_profile` |
| PATCH | `/api/v1/patient-profiles/{profile_id}` | Bệnh nhân | `edit_profile` |
| DELETE | `/api/v1/patient-profiles/{profile_id}` | Bệnh nhân | `archive_profile` |

### Đặt lịch (10)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/bookings` | Bệnh nhân | `create_booking` |
| POST | `/api/v1/bookings/hold` | Bệnh nhân | `create_booking_hold` |
| DELETE | `/api/v1/bookings/holds/{hold_id}` | Đăng nhập | `release_booking_hold` |
| GET | `/api/v1/bookings` | Đăng nhập | `list_bookings` |
| GET | `/api/v1/bookings/{booking_id}` | Đăng nhập | `get_booking` |
| POST | `/api/v1/bookings/{booking_id}/cancel` | Đăng nhập | `cancel_booking` |
| POST | `/api/v1/bookings/{booking_id}/reschedule` | Bệnh nhân | `reschedule_booking` |
| GET | `/api/v1/staff/bookings` | Staff | `staff_list_bookings` |
| GET | `/api/v1/staff/bookings/{booking_id}` | Staff | `staff_get_booking` |
| PATCH | `/api/v1/staff/bookings/{booking_id}/status` | Staff | `staff_update_booking_status` |

### Bàn điều phối (24)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/staff/workbench/me` | Staff (thành viên điều phối) | `me` |
| POST | `/api/v1/staff/workbench/duty/start` | Staff (thành viên điều phối) | `start_duty` |
| POST | `/api/v1/staff/workbench/duty/handover` | Staff (thành viên điều phối) | `handover_duty` |
| POST | `/api/v1/staff/workbench/duty/end` | Staff (thành viên điều phối) | `end_duty` |
| GET | `/api/v1/staff/workbench/catalog` | Staff (thành viên điều phối) | `catalog` |
| GET | `/api/v1/staff/workbench/cases` | Staff (thành viên điều phối) | `cases` |
| GET | `/api/v1/staff/workbench/dashboard` | Staff (thành viên điều phối) | `dashboard` |
| GET | `/api/v1/staff/workbench/cases/{case_id}` | Staff (thành viên điều phối) | `case_detail` |
| POST | `/api/v1/staff/workbench/cases/{case_id}/actions` | Staff (thành viên điều phối) | `case_action` |
| POST | `/api/v1/staff/workbench/cases/bulk-actions` | Staff (thành viên điều phối) | `bulk_case_actions` |
| PUT | `/api/v1/staff/workbench/cases/{case_id}/plan` | Staff (thành viên điều phối) | `plan` |
| POST | `/api/v1/staff/workbench/cases/{case_id}/deposits` | Staff (thành viên điều phối) | `deposit` |
| POST | `/api/v1/staff/workbench/cases/{case_id}/verify-deposit` | Staff (thành viên điều phối) | `verify` |
| POST | `/api/v1/staff/workbench/cases/{case_id}/confirm` | Staff (thành viên điều phối) | `confirm` |
| POST | `/api/v1/staff/workbench/cases/{case_id}/messages` | Staff (thành viên điều phối) | `message` |
| GET | `/api/v1/staff/workbench/members` | Staff (thành viên điều phối) | `members` |
| PUT | `/api/v1/staff/workbench/members` | Quản trị | `save_member` |
| GET | `/api/v1/staff/workbench/policy` | Staff (thành viên điều phối) | `policy` |
| PUT | `/api/v1/staff/workbench/policy` | Quản trị | `save_policy` |
| GET | `/api/v1/coordination/live/mine` | Khách / đăng nhập | `my_cases` |
| GET | `/api/v1/coordination/live/{session_id}` | Khách / đăng nhập | `updates` |
| POST | `/api/v1/coordination/live/{session_id}/request-human` | Khách / đăng nhập | `request_human` |
| POST | `/api/v1/coordination/live/{session_id}/sos` | Khách / đăng nhập | `patient_sos` |
| POST | `/api/v1/coordination/live/{session_id}/messages` | Khách / đăng nhập | `patient_message` |

### Lịch tư vấn & quy tắc ca (11)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/coordination/sessions` | Công khai | `list_sessions` |
| POST | `/api/v1/coordination/requests` | Khách / đăng nhập | `create_request` |
| GET | `/api/v1/coordination/requests/mine` | Bệnh nhân | `my_requests` |
| POST | `/api/v1/coordination/requests/{request_id}/cancel` | Bệnh nhân | `cancel_request` |
| GET | `/api/v1/staff/coordination/rules` | Quản trị | `list_rules` |
| POST | `/api/v1/staff/coordination/rules/standard-week` | Quản trị | `create_standard_week` |
| POST | `/api/v1/staff/coordination/rules` | Quản trị | `create_rule` |
| POST | `/api/v1/staff/coordination/publish` | Quản trị | `publish_sessions` |
| GET | `/api/v1/staff/coordination/requests` | Quản trị | `staff_requests` |
| POST | `/api/v1/staff/coordination/requests/{request_id}/assign` | Quản trị | `assign_request` |
| POST | `/api/v1/staff/coordination/requests/{request_id}/reject` | Quản trị | `reject_request` |

### Tiếp quản chat (9)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/staff/chat-takeover/ticket` | Đăng nhập | `get_takeover_ticket` |
| GET | `/api/v1/staff/chat-takeover/cases` | Staff | `list_cases` |
| GET | `/api/v1/staff/chat-takeover/cases/{case_id}` | Staff | `get_case` |
| POST | `/api/v1/staff/chat-takeover/cases/{case_id}/claim` | Staff | `claim_case` |
| POST | `/api/v1/staff/chat-takeover/cases/{case_id}/release` | Staff | `release_case` |
| POST | `/api/v1/staff/chat-takeover/cases/{case_id}/resolve` | Staff | `resolve_case` |
| POST | `/api/v1/staff/chat-takeover/cases/{case_id}/messages` | Staff | `send_message` |
| WS | `/api/v1/staff/chat-takeover/ws/staff` | Staff | `staff_socket` |
| WS | `/api/v1/staff/chat-takeover/ws/{session_id}` | Đăng nhập ⚠️ | `patient_socket` |

### Thông báo (3)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/notifications` | Đăng nhập | `list_notifications` |
| POST | `/api/v1/notifications/{notification_id}/read` | Đăng nhập | `mark_notification_read` |
| POST | `/api/v1/notifications/read-all` | Đăng nhập | `mark_all_notifications_read` |

### Gói khám (5)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/packages/requests` | Khách / đăng nhập | `create_package_request` |
| GET | `/api/v1/packages/requests/mine` | Bệnh nhân | `list_my_package_requests` |
| PATCH | `/api/v1/packages/requests/{request_id}/reschedule` | Bệnh nhân | `patient_reschedule_package_request` |
| GET | `/api/v1/staff/packages/requests` | Quản trị | `staff_list_package_requests` |
| PATCH | `/api/v1/staff/packages/requests/{request_id}` | Quản trị | `staff_update_package_request` |

### Bác sĩ (8)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/doctors` | Công khai | `list_doctors` |
| GET | `/api/v1/doctors/facets` | Công khai | `doctor_facets` |
| GET | `/api/v1/doctors/{doctor_id}` | Đăng nhập | `get_doctor` |
| GET | `/api/v1/staff/doctors` | Staff | `staff_list_doctors` |
| POST | `/api/v1/staff/doctors` | Staff | `staff_create_doctor` |
| GET | `/api/v1/staff/doctors/{doctor_id}` | Staff | `staff_get_doctor` |
| PATCH | `/api/v1/staff/doctors/{doctor_id}` | Staff | `staff_update_doctor` |
| PATCH | `/api/v1/staff/doctors/{doctor_id}/toggle-booking` | Staff | `staff_toggle_booking` |

### Lịch bác sĩ (7)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/doctors/{doctor_id}/availability` | Công khai | `doctor_availability` |
| GET | `/api/v1/staff/schedules` | Staff | `staff_list_schedules` |
| GET | `/api/v1/staff/schedule-activity` | Staff | `staff_schedule_activity` |
| POST | `/api/v1/staff/schedules` | Staff | `staff_create_schedule` |
| PUT | `/api/v1/staff/schedules/{schedule_id}` | Staff | `staff_update_schedule` |
| POST | `/api/v1/staff/schedules/import` | Staff | `staff_import_schedules` |
| DELETE | `/api/v1/staff/schedules/{schedule_id}/cancel` | Staff | `staff_cancel_schedule` |

### Dịch vụ (6)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/services` | Công khai | `list_public_services` |
| GET | `/api/v1/services/categories` | Công khai | `list_service_categories` |
| GET | `/api/v1/services/{service_id}` | Đăng nhập | `get_public_service` |
| GET | `/api/v1/staff/services` | Staff | `staff_list_services` |
| POST | `/api/v1/staff/services` | Staff | `staff_create_service` |
| PATCH | `/api/v1/staff/services/{service_id}` | Staff | `staff_update_service` |

### Chuyên khoa (4)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/specialties` | Công khai | `list_specialties` |
| GET | `/api/v1/specialties/{specialty_id}` | Đăng nhập | `get_specialty` |
| POST | `/api/v1/staff/specialties` | Staff | `staff_create_specialty` |
| PATCH | `/api/v1/staff/specialties/{specialty_id}` | Staff | `staff_update_specialty` |

### Cơ sở (4)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/facilities` | Công khai | `list_facilities` |
| GET | `/api/v1/facilities/{facility_id}` | Đăng nhập | `get_facility` |
| POST | `/api/v1/staff/facilities` | Staff | `staff_create_facility` |
| PATCH | `/api/v1/staff/facilities/{facility_id}` | Staff | `staff_update_facility` |

### Tổng quan nhân viên (1)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/staff/dashboard/summary` | Staff | `summary` |

### Bệnh nhân (nhân viên) (2)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/api/v1/staff/patients` | Staff | `search_patients` |
| GET | `/api/v1/staff/patients/{patient_id}` | Staff | `get_patient_detail` |

### Zalo (4)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| POST | `/api/v1/zalo/webhook` | Zalo (secret header) | `handle_zalo_webhook` |
| GET | `/api/v1/zalo/status` | Công khai | `get_zalo_bot_status` |
| POST | `/api/v1/zalo/setup-webhook` | Công khai ⚠️ | `setup_zalo_webhook` |
| GET | `/api/v1/zalo/setup-webhook` | Công khai ⚠️ | `setup_zalo_webhook` |

### Hệ thống (3)

| Method | Path | Quyền | Hàm xử lý |
|---|---|---|---|
| GET | `/` | Công khai | `root` |
| GET | `/health` | Công khai | `health` |
| GET | `/health/ready` | Công khai | `readiness` |

## Vấn đề phân quyền phát hiện được

| # | Endpoint | Vấn đề | Mức độ | Đề xuất |
|---|---|---|---|---|
| 1 | `WS /api/v1/staff/chat-takeover/ws/{session_id}` | Chỉ kiểm tra người kết nối đã đăng nhập, **không kiểm tra `session_id` có thuộc về họ không** (`src/api/endpoints/chat_takeover.py:166-171`). Người dùng biết `session_id` của người khác có thể nghe tin nhắn tiếp quản của phiên đó | Trung bình (session_id ngẫu nhiên, khó đoán) | Kiểm tra chủ sở hữu phiên trước khi `connect_session` |
| 2 | `GET /api/v1/admin/metrics/daily` | Không yêu cầu đăng nhập; trả số liệu vận hành (tỷ lệ fallback, clarify…) | Thấp (số liệu tổng hợp) | Thêm `require_coordination_admin` |
| 3 | `GET` / `POST /api/v1/zalo/setup-webhook` | Ai cũng kích hoạt được việc đăng ký lại webhook Zalo | Thấp | Chỉ cho quản trị gọi, hoặc chỉ chạy lúc deploy |
| 4 | `POST /api/v1/chat`, `GET /api/v1/status` (module `api.routes`) | Trùng đường dẫn với `medical_assistant.api.routes`. FastAPI luôn dùng route khai báo trước, nên agent trong `src/agents/` không bao giờ chạy; OpenAPI cảnh báo `Duplicate Operation ID` | Thấp (code chết) | Xóa `agent_core_router` khỏi `src/main.py` hoặc đổi đường dẫn |

`GET /api/v1/zalo/status` chỉ trả cờ cấu hình (đã cấu hình token/secret hay chưa), không lộ giá trị bí mật.
