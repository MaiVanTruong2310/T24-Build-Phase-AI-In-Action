# Tổng quan Cơ sở dữ liệu — VCare+ (P-124)

> Danh sách bảng, khóa chính, khóa ngoại của PostgreSQL.
> Căn cứ: `develop` commit `d867dfd` (11/10/2026). Danh sách bảng/khóa được lấy **tự động** bằng cách nạp toàn bộ model SQLAlchemy trong `src/models/` và đọc `Base.metadata`; chuỗi migration được kiểm tra bằng lệnh `alembic heads`.

## Tóm tắt

| Chỉ số | Giá trị |
|---|---|
| Bảng có model ORM (`src/models/`) | **41** |
| Bảng chỉ có trong migration, không có model | **2**: `chat_conversations`, `chat_turns` (truy cập bằng SQL thuần trong `src/services/chat_history.py`) |
| Tổng số bảng | **43** |
| Khóa ngoại | **91** |
| Bảng được tham chiếu nhiều nhất | `users` (39 khóa ngoại), `facilities` (7), `doctors` (7), `services` (6), `patient_profiles` (6), `conversations` (5) |
| Khóa chính | Hầu hết là `id` (UUID). Ngoại lệ: `coordinator_members` (khóa `user_id`), `patient_chat_context` và `staff_agent_context` (khóa `conversation_id`) |
| Migration Alembic | 27 revision, **1 head**: `0024_schedule_service_and_busy_reason` |

## Chuỗi migration

```text
0001 → 0002 → 0003 → 0004 → 3c5a170017bb → 44837e30b196 → 0005 → … → 0020_reconcile_model_schema
                                                                          ├─ 0021_chat_history_tables → 0022_booking_expired_at ─┐
                                                                          └─ 0021_workbench_takeover_compatibility ──────────────┴─ 0023_merge (gộp 2 nhánh) → 0024 (head)
```

- Có **2 file cùng số `0021`** do hai nhánh phát triển song song, được gộp lại ở `0023_merge_workbench_booking_heads`.
- Hai file `3c5a170017bb_*` và `44837e30b196_*` dùng mã tự sinh thay vì số thứ tự, nằm giữa `0004` và `0005`.

Chạy migration: `alembic upgrade head`.

## Danh sách bảng theo nhóm

Ký hiệu khóa ngoại: `cột->bảng.cột[hành vi khi xóa bản ghi cha]`. `CASCADE` = xóa theo; `SET NULL` = đặt rỗng; `RESTRICT`/`-` = chặn xóa nếu còn tham chiếu.
⚠️ = bảng **không được migration Alembic tạo ra** (xem mục cuối).
Cột `UNIQUE` khai báo trực tiếp trên cột (ví dụ `users.email`, `users.phone`) không hiển thị trong cột "Ràng buộc UNIQUE".

### Tài khoản & xác thực

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `users` | 14 | `id` | — | — |
| `otp_challenges` | 9 | `id` | `user_id->users.id[CASCADE]` | — |
| `refresh_sessions` | 9 | `id` | `user_id->users.id[CASCADE]` | — |

### Hồ sơ bệnh nhân & bộ nhớ

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `patient_profiles` ⚠️ | 11 | `id` | `linked_user_id->users.id[RESTRICT]`<br>`patient_user_id->users.id[RESTRICT]` | `patient_user_id`<br>`linked_user_id` |
| `patient_relationships` ⚠️ | 9 | `id` | `patient_profile_id->patient_profiles.id[RESTRICT]`<br>`user_id->users.id[RESTRICT]` | `user_id,patient_profile_id` |
| `patient_memory_items` ⚠️ | 12 | `id` | `user_id->users.id[CASCADE]` | — |
| `patient_open_loops` ⚠️ | 7 | `id` | `user_id->users.id[CASCADE]` | — |
| `patient_chat_context` ⚠️ | 7 | `conversation_id` | `conversation_id->conversations.id[CASCADE]`<br>`patient_id->users.id[RESTRICT]` | — |

### Danh mục y tế

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `specialties` | 7 | `id` | — | — |
| `services` | 15 | `id` | — | — |
| `facilities` | 9 | `id` | — | — |
| `doctors` | 21 | `id` | — | — |
| `doctor_specialties` | 4 | `id` | `doctor_id->doctors.id[CASCADE]`<br>`specialty_id->specialties.id[RESTRICT]` | `doctor_id,specialty_id` |
| `doctor_facilities` | 9 | `id` | `doctor_id->doctors.id[CASCADE]`<br>`facility_id->facilities.id[RESTRICT]` | `doctor_id,facility_id` |
| `doctor_services` | 4 | `id` | `doctor_id->doctors.id[CASCADE]`<br>`service_id->services.id[RESTRICT]` | `doctor_id,service_id` |
| `catalog_audit_events` | 7 | `id` | `actor_id->users.id[SET NULL]` | — |

### Lịch bác sĩ

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `doctor_schedules` | 18 | `id` | `created_by->users.id[SET NULL]`<br>`doctor_id->doctors.id[RESTRICT]`<br>`facility_id->facilities.id[RESTRICT]`<br>`service_id->services.id[RESTRICT]`<br>`updated_by->users.id[SET NULL]` | `source_system,external_schedule_id` |
| `weekly_shifts` | 11 | `id` | `doctor_id->doctors.id[RESTRICT]`<br>`facility_id->facilities.id[RESTRICT]` | `doctor_id,weekday,period` |
| `consultation_sessions` | 8 | `id` | `doctor_id->doctors.id[RESTRICT]`<br>`facility_id->facilities.id[RESTRICT]`<br>`weekly_shift_id->weekly_shifts.id[RESTRICT]` | `doctor_id,session_date,period` |
| `consultation_slots` | 4 | `id` | `schedule_id->doctor_schedules.id[RESTRICT]`<br>`session_id->consultation_sessions.id[RESTRICT]` | `schedule_id`<br>`session_id,ordinal` |

### Đặt lịch

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `bookings` | 25 | `id` | `doctor_id->doctors.id[RESTRICT]`<br>`facility_id->facilities.id[RESTRICT]`<br>`hold_id->booking_holds.id[SET NULL]`<br>`patient_profile_id->patient_profiles.id[RESTRICT]`<br>`requested_by_user_id->users.id[RESTRICT]`<br>`reviewed_by->users.id[SET NULL]`<br>`schedule_id->doctor_schedules.id[RESTRICT]`<br>`service_id->services.id[RESTRICT]`<br>`specialty_id->specialties.id[RESTRICT]`<br>`user_id->users.id[RESTRICT]` | — |
| `booking_holds` | 12 | `id` | `patient_profile_id->patient_profiles.id[RESTRICT]`<br>`requested_by_user_id->users.id[RESTRICT]`<br>`schedule_id->doctor_schedules.id[RESTRICT]`<br>`service_id->services.id[RESTRICT]`<br>`specialty_id->specialties.id[RESTRICT]`<br>`user_id->users.id[CASCADE]` | — |
| `consultation_requests` | 18 | `id` | `assigned_slot_id->consultation_slots.id[RESTRICT]`<br>`booking_id->bookings.id[RESTRICT]`<br>`patient_id->users.id[RESTRICT]`<br>`patient_profile_id->patient_profiles.id[RESTRICT]`<br>`requested_by_user_id->users.id[RESTRICT]`<br>`reviewed_by->users.id[SET NULL]`<br>`service_id->services.id[RESTRICT]`<br>`session_id->consultation_sessions.id[RESTRICT]`<br>`specialty_id->specialties.id[RESTRICT]` | `booking_id` |
| `consultation_request_events` | 6 | `id` | `actor_id->users.id[SET NULL]`<br>`request_id->consultation_requests.id[RESTRICT]` | — |
| `package_requests` ⚠️ | 18 | `id` | `facility_id->facilities.id[RESTRICT]`<br>`patient_id->users.id[RESTRICT]`<br>`patient_profile_id->patient_profiles.id[RESTRICT]`<br>`requested_by_user_id->users.id[RESTRICT]`<br>`service_id->services.id[RESTRICT]` | — |

### Điều phối (HITL Workbench)

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `coordinator_members` | 6 | `user_id` | `user_id->users.id[CASCADE]` | — |
| `coordination_policy` | 6 | `id` | — | — |
| `coordination_cases` | 24 | `id` | `assigned_to->users.id[SET NULL]`<br>`booking_id->bookings.id[RESTRICT]`<br>`facility_id->facilities.id[RESTRICT]`<br>`patient_id->users.id[RESTRICT]`<br>`patient_profile_id->patient_profiles.id[RESTRICT]`<br>`requested_by_user_id->users.id[RESTRICT]` | `legacy_takeover_case_id`<br>`owner_key,session_id`<br>`source,source_id` |
| `coordination_events` | 7 | `id` | `actor_id->users.id[SET NULL]`<br>`case_id->coordination_cases.id[RESTRICT]` | — |
| `coordination_messages` | 7 | `id` | `actor_id->users.id[SET NULL]`<br>`case_id->coordination_cases.id[RESTRICT]` | `case_id,client_id` |
| `coordination_deposits` | 13 | `id` | `case_id->coordination_cases.id[RESTRICT]`<br>`verified_by->users.id[SET NULL]` | `refund_reference`<br>`transaction_reference` |

### Hội thoại & tiếp quản

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `conversations` ⚠️ | 10 | `id` | `patient_id->users.id[RESTRICT]` | — |
| `conversation_participants` ⚠️ | 7 | `id` | `conversation_id->conversations.id[CASCADE]` | — |
| `messages` ⚠️ | 8 | `id` | `conversation_id->conversations.id[CASCADE]` | — |
| `handoffs` ⚠️ | 13 | `id` | `assigned_staff_id->users.id[SET NULL]`<br>`conversation_id->conversations.id[CASCADE]` | — |
| `staff_agent_context` ⚠️ | 9 | `conversation_id` | `context_patient_id->users.id[SET NULL]`<br>`conversation_id->conversations.id[CASCADE]`<br>`staff_id->users.id[RESTRICT]` | — |
| `chat_takeover_cases` | 12 | `id` | `assigned_staff_id->users.id[SET NULL]`<br>`patient_user_id->users.id[CASCADE]` | `patient_user_id,session_id` |
| `chat_takeover_messages` | 8 | `id` | `author_user_id->users.id[SET NULL]`<br>`case_id->chat_takeover_cases.id[CASCADE]` | `case_id,client_message_id` |
| `chat_takeover_audit_events` | 6 | `id` | `actor_user_id->users.id[SET NULL]`<br>`case_id->chat_takeover_cases.id[CASCADE]` | — |

### Thông báo & kênh ngoài

| Bảng | Số cột | Khóa chính | Khóa ngoại (cột → bảng.cột, ON DELETE) | Ràng buộc UNIQUE |
|---|---|---|---|---|
| `notifications` | 13 | `id` | `booking_id->bookings.id[SET NULL]`<br>`user_id->users.id[CASCADE]` | — |
| `zalo_user_mappings` | 7 | `id` | `user_id->users.id[SET NULL]` | — |

### Chỉ có trong migration (không có model ORM)

| Bảng | Tạo bởi | Truy cập |
|---|---|---|
| `chat_conversations` | `alembic/versions/0021_chat_history_tables.py` (SQL thuần) | `src/services/chat_history.py` |
| `chat_turns` | như trên | như trên |

## ⚠️ Lệch giữa model và migration

**11 bảng có model nhưng không có migration Alembic nào tạo ra:**

| Bảng | Được tạo ở đâu |
|---|---|
| `patient_profiles`, `patient_relationships` | `scripts/supabase/migrations/20261005000000_patient_family_profiles.sql` |
| `package_requests` | `scripts/_archive/create_package_requests_table.py` |
| `conversations`, `conversation_participants`, `messages`, `handoffs`, `patient_chat_context`, `staff_agent_context`, `patient_memory_items`, `patient_open_loops` | Chỉ qua `Base.metadata.create_all` khi bật `DATABASE_AUTO_CREATE=true` (`src/db/session.py`), hoặc script cũ trong `scripts/_archive/` |

**Hệ quả:** một database mới dựng **chỉ bằng `alembic upgrade head`** sẽ **thiếu 11 bảng** này, trong đó có bảng hội thoại, bộ nhớ bệnh nhân và hồ sơ người thân. Ứng dụng hiện chạy được nhờ `DATABASE_AUTO_CREATE=true`. Nhưng `create_all` chỉ tạo bảng còn thiếu, **không cập nhật** bảng đã có, nên cấu trúc dễ lệch dần giữa các môi trường.

**Đề xuất:** viết một migration Alembic `0025` tạo đủ 11 bảng (dùng `alembic revision --autogenerate` rồi rà lại), sau đó tắt `DATABASE_AUTO_CREATE` ở production.

Ngoài ra, migration `0020` tạo khóa ngoại tới `patient_profiles`, nên nhiều khả năng `alembic upgrade head` trên database trống sẽ **lỗi ngay ở `0020`**. Chi tiết: [migrations.md](migrations.md).
