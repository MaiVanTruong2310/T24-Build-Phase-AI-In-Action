# Sơ đồ quan hệ dữ liệu (ERD) — VCare+ (P-124)

> Căn cứ: `develop` commit `d867dfd` (11/10/2026). Sơ đồ được **sinh tự động** từ metadata của model SQLAlchemy (`src/models/`), nên tên cột, khóa và quan hệ khớp đúng với code.
> Danh sách đầy đủ 43 bảng và 91 khóa ngoại: [schema-overview.md](schema-overview.md).

## Đọc sơ đồ thế nào

Mỗi ô là một **bảng**. Các dòng trong ô là **cột**, cột `PK` là khóa chính, cột `FK` là khóa ngoại trỏ sang bảng khác.

Đường nối giữa hai bảng cho biết **một bản ghi bên này ứng với bao nhiêu bản ghi bên kia**. Ký hiệu nằm ở hai đầu đường nối:

| Ký hiệu ở đầu đường | Nghĩa |
|---|---|
| `\|\|` (hai vạch) | Đúng **một** |
| `o\|` (vòng + vạch) | **Không hoặc một** |
| `o{` (vòng + chân chim) | **Không, một hoặc nhiều** |

Ví dụ `doctors ||--o{ bookings`: một bác sĩ có thể có **nhiều** lịch hẹn, mỗi lịch hẹn thuộc **đúng một** bác sĩ. Nếu đầu phía bảng cha là `o|`, khóa ngoại được phép để trống (ví dụ lịch hẹn có thể không gắn giữ chỗ `hold_id`).

Chữ trên đường nối là **tên cột khóa ngoại** ở bảng con.

## Quy ước rút gọn để sơ đồ dễ đọc

- Chỉ hiện khóa chính, khóa ngoại và vài cột quan trọng (trạng thái, tên, thời gian…). Danh sách cột đầy đủ xem ở từ điển dữ liệu.
- Bảng đã vẽ chi tiết ở sơ đồ khác chỉ hiện khóa chính và tên.
- **Ẩn 16 khóa ngoại "ghi vết"** (cho biết *ai* tạo, duyệt, thao tác), vì chúng đều trỏ về `users` và làm sơ đồ rối:

  `booking_holds.requested_by_user_id`, `bookings.requested_by_user_id`, `bookings.reviewed_by`, `catalog_audit_events.actor_id`, `chat_takeover_messages.author_user_id`, `consultation_request_events.actor_id`, `consultation_requests.requested_by_user_id`, `consultation_requests.reviewed_by`, `coordination_cases.requested_by_user_id`, `coordination_deposits.verified_by`, `coordination_events.actor_id`, `coordination_messages.actor_id`, `doctor_schedules.created_by`, `doctor_schedules.updated_by`, `package_requests.requested_by_user_id`, `patient_profiles.linked_user_id` (tất cả trỏ về `users.id`).

## Những điểm cần nắm

1. **`users` là trung tâm**, được 39 khóa ngoại trỏ tới. Cả bệnh nhân lẫn nhân viên đều là một dòng trong `users`, phân biệt bằng cột `role`.
2. **Bệnh nhân và hồ sơ khám là hai khái niệm khác nhau.** Một tài khoản (`users`) có thể quản lý nhiều **hồ sơ người khám** (`patient_profiles`), ví dụ đặt lịch cho bố mẹ, con. Lịch hẹn ghi cả `user_id` (ai đặt) lẫn `patient_profile_id` (khám cho ai).
3. **Bác sĩ liên kết nhiều–nhiều** với chuyên khoa, cơ sở, dịch vụ qua 3 bảng trung gian `doctor_specialties`, `doctor_facilities`, `doctor_services`.
4. **Có 2 cơ chế đặt lịch**: lịch đặt trực tiếp (`bookings` + `booking_holds`) và ca điều phối (`coordination_cases`). Khi điều phối viên chốt lịch, ca gắn với một `bookings` qua `coordination_cases.booking_id`.
5. **Có 2 hệ thống tiếp quản chat** song song: `chat_takeover_*` và bộ `conversations` / `handoffs`.

## 0. Tổng quan

Các bảng nghiệp vụ chính và quan hệ giữa chúng: không hiện cột và khóa ngoại ghi vết; giữ chỗ, tin nhắn, gói khám được vẽ chi tiết ở sơ đồ 2 và 4.

```mermaid
erDiagram
    bookings |o--o{ coordination_cases : ""
    bookings |o--o{ notifications : ""
    coordination_cases ||--o{ coordination_deposits : ""
    doctor_schedules |o--o{ bookings : ""
    doctors ||--o{ bookings : ""
    doctors ||--o{ doctor_schedules : ""
    facilities |o--o{ coordination_cases : ""
    facilities ||--o{ bookings : ""
    facilities ||--o{ doctor_schedules : ""
    patient_profiles |o--o{ bookings : ""
    patient_profiles |o--o{ coordination_cases : ""
    services |o--o{ doctor_schedules : ""
    services ||--o{ bookings : ""
    specialties ||--o{ bookings : ""
    users |o--o{ conversations : ""
    users |o--o{ coordination_cases : ""
    users |o--o{ zalo_user_mappings : ""
    users ||--o{ bookings : ""
    users ||--o{ notifications : ""
    users ||--o{ patient_profiles : ""
```

## 1. Danh mục & lịch bác sĩ

Danh mục y tế và lịch làm việc. Bác sĩ liên kết nhiều-nhiều với chuyên khoa, cơ sở, dịch vụ qua 3 bảng trung gian.

```mermaid
erDiagram
    doctors ||--o{ doctor_facilities : "doctor_id"
    doctors ||--o{ doctor_schedules : "doctor_id"
    doctors ||--o{ doctor_services : "doctor_id"
    doctors ||--o{ doctor_specialties : "doctor_id"
    doctors ||--o{ weekly_shifts : "doctor_id"
    facilities ||--o{ doctor_facilities : "facility_id"
    facilities ||--o{ doctor_schedules : "facility_id"
    facilities ||--o{ weekly_shifts : "facility_id"
    services |o--o{ doctor_schedules : "service_id"
    services ||--o{ doctor_services : "service_id"
    specialties ||--o{ doctor_specialties : "specialty_id"
    specialties {
        uuid id PK
        string code
        string name
        string status
    }
    services {
        uuid id PK
        string code
        string name
        decimal price
        string booking_mode
        string status
    }
    facilities {
        uuid id PK
        string code
        string name
        string phone
        string status
    }
    doctors {
        uuid id PK
        string code
        string full_name
        string title
        string status
    }
    doctor_specialties {
        uuid id PK
        uuid doctor_id FK
        uuid specialty_id FK
    }
    doctor_facilities {
        uuid id PK
        uuid doctor_id FK
        uuid facility_id FK
    }
    doctor_services {
        uuid id PK
        uuid doctor_id FK
        uuid service_id FK
    }
    doctor_schedules {
        uuid id PK
        uuid doctor_id FK
        uuid facility_id FK
        datetime starts_at
        datetime ends_at
        int capacity
        string status
        int version
        uuid service_id FK
    }
    weekly_shifts {
        uuid id PK
        uuid doctor_id FK
        uuid facility_id FK
        int weekday
        string period
    }
```

## 2. Người dùng & đặt lịch

Bệnh nhân, hồ sơ người thân, giữ chỗ, lịch hẹn, yêu cầu gói khám và thông báo.

```mermaid
erDiagram
    booking_holds |o--o{ bookings : "hold_id"
    bookings |o--o{ notifications : "booking_id"
    doctor_schedules |o--o{ bookings : "schedule_id"
    doctor_schedules ||--o{ booking_holds : "schedule_id"
    doctors ||--o{ bookings : "doctor_id"
    doctors ||--o{ doctor_schedules : "doctor_id"
    facilities ||--o{ bookings : "facility_id"
    facilities ||--o{ doctor_schedules : "facility_id"
    facilities ||--o{ package_requests : "facility_id"
    patient_profiles |o--o{ booking_holds : "patient_profile_id"
    patient_profiles |o--o{ bookings : "patient_profile_id"
    patient_profiles |o--o{ package_requests : "patient_profile_id"
    patient_profiles ||--o{ patient_relationships : "patient_profile_id"
    services |o--o{ doctor_schedules : "service_id"
    services ||--o{ booking_holds : "service_id"
    services ||--o{ bookings : "service_id"
    services ||--o{ package_requests : "service_id"
    specialties ||--o{ booking_holds : "specialty_id"
    specialties ||--o{ bookings : "specialty_id"
    users |o--o{ package_requests : "patient_id"
    users ||--o{ booking_holds : "user_id"
    users ||--o{ bookings : "user_id"
    users ||--o{ notifications : "user_id"
    users ||--o{ patient_profiles : "patient_user_id"
    users ||--o{ patient_relationships : "user_id"
    users {
        uuid id PK
        string email
        string phone
        string role
        string status
        string full_name
    }
    patient_profiles {
        uuid id PK
        uuid patient_user_id FK
        string full_name
    }
    patient_relationships {
        uuid id PK
        uuid user_id FK
        uuid patient_profile_id FK
        string relationship
        string status
    }
    booking_holds {
        uuid id PK
        uuid user_id FK
        uuid patient_profile_id FK
        uuid schedule_id FK
        uuid service_id FK
        uuid specialty_id FK
        string status
        datetime expires_at
    }
    bookings {
        uuid id PK
        uuid user_id FK
        uuid patient_profile_id FK
        uuid schedule_id FK
        uuid hold_id FK
        uuid doctor_id FK
        uuid facility_id FK
        datetime starts_at
        datetime ends_at
        uuid service_id FK
        uuid specialty_id FK
        string encounter_type
        string status
        datetime expired_at
    }
    package_requests {
        uuid id PK
        uuid patient_id FK
        uuid patient_profile_id FK
        uuid service_id FK
        uuid facility_id FK
        date preferred_date
        string status
    }
    notifications {
        uuid id PK
        uuid user_id FK
        uuid booking_id FK
        string kind
        string status
        string title
    }
    doctor_schedules {
        uuid id PK
    }
    doctors {
        uuid id PK
        string full_name
    }
    facilities {
        uuid id PK
        string name
    }
    services {
        uuid id PK
        string name
    }
    specialties {
        uuid id PK
        string name
    }
```

## 3. Điều phối (HITL Workbench) & lịch tư vấn

Ca điều phối và mọi thứ gắn với ca: sự kiện, tin nhắn, tiền cọc. Kèm luồng yêu cầu tư vấn theo phiên.

```mermaid
erDiagram
    bookings |o--o{ consultation_requests : "booking_id"
    bookings |o--o{ coordination_cases : "booking_id"
    consultation_requests ||--o{ consultation_request_events : "request_id"
    consultation_sessions ||--o{ consultation_requests : "session_id"
    consultation_sessions ||--o{ consultation_slots : "session_id"
    consultation_slots |o--o{ consultation_requests : "assigned_slot_id"
    coordination_cases ||--o{ coordination_deposits : "case_id"
    coordination_cases ||--o{ coordination_events : "case_id"
    coordination_cases ||--o{ coordination_messages : "case_id"
    doctor_schedules |o--o{ bookings : "schedule_id"
    doctor_schedules ||--o{ consultation_slots : "schedule_id"
    patient_profiles |o--o{ bookings : "patient_profile_id"
    patient_profiles |o--o{ consultation_requests : "patient_profile_id"
    patient_profiles |o--o{ coordination_cases : "patient_profile_id"
    users |o--o{ coordination_cases : "assigned_to"
    users |o--o{ coordination_cases : "patient_id"
    users ||--o{ bookings : "user_id"
    users ||--o{ consultation_requests : "patient_id"
    users ||--o{ coordinator_members : "user_id"
    users ||--o{ patient_profiles : "patient_user_id"
    coordinator_members {
        uuid user_id PK,FK
        bool enabled
        bool is_admin
    }
    coordination_policy {
        int id PK
    }
    coordination_cases {
        uuid id PK
        string session_id
        uuid patient_id FK
        uuid patient_profile_id FK
        uuid facility_id FK
        uuid assigned_to FK
        string status
        int priority
        string control
        int version
        uuid booking_id FK
    }
    coordination_events {
        uuid id PK
        uuid case_id FK
        string action
    }
    coordination_messages {
        uuid id PK
        uuid case_id FK
    }
    coordination_deposits {
        uuid id PK
        uuid case_id FK
        int amount
        string status
        datetime expires_at
    }
    consultation_sessions {
        uuid id PK
        uuid weekly_shift_id FK
        uuid doctor_id FK
        uuid facility_id FK
        string period
        string status
    }
    consultation_slots {
        uuid id PK
        uuid session_id FK
        uuid schedule_id FK
    }
    consultation_requests {
        uuid id PK
        uuid patient_profile_id FK
        uuid patient_id FK
        uuid session_id FK
        uuid service_id FK
        uuid specialty_id FK
        string encounter_type
        string status
        uuid assigned_slot_id FK
        uuid booking_id FK
    }
    consultation_request_events {
        uuid id PK
        uuid request_id FK
        string action
    }
    users {
        uuid id PK
        string full_name
    }
    patient_profiles {
        uuid id PK
        string full_name
    }
    bookings {
        uuid id PK
    }
    doctor_schedules {
        uuid id PK
    }
```

## 4. Hội thoại, tiếp quản & bộ nhớ

Hội thoại hợp nhất (web, Zalo, nhân viên), tiếp quản chat và bộ nhớ dài hạn của bệnh nhân.

```mermaid
erDiagram
    chat_takeover_cases ||--o{ chat_takeover_audit_events : "case_id"
    chat_takeover_cases ||--o{ chat_takeover_messages : "case_id"
    conversations ||--o{ conversation_participants : "conversation_id"
    conversations ||--o{ handoffs : "conversation_id"
    conversations ||--o{ messages : "conversation_id"
    conversations ||--o{ patient_chat_context : "conversation_id"
    conversations ||--o{ staff_agent_context : "conversation_id"
    users |o--o{ chat_takeover_audit_events : "actor_user_id"
    users |o--o{ chat_takeover_cases : "assigned_staff_id"
    users |o--o{ conversations : "patient_id"
    users |o--o{ handoffs : "assigned_staff_id"
    users |o--o{ patient_chat_context : "patient_id"
    users |o--o{ staff_agent_context : "context_patient_id"
    users |o--o{ zalo_user_mappings : "user_id"
    users ||--o{ chat_takeover_cases : "patient_user_id"
    users ||--o{ patient_memory_items : "user_id"
    users ||--o{ patient_open_loops : "user_id"
    users ||--o{ patient_profiles : "patient_user_id"
    users ||--o{ staff_agent_context : "staff_id"
    conversations {
        uuid id PK
        string status
        uuid patient_id FK
    }
    conversation_participants {
        uuid id PK
        uuid conversation_id FK
        string role
    }
    messages {
        uuid id PK
        uuid conversation_id FK
        string sender_type
    }
    handoffs {
        uuid id PK
        uuid conversation_id FK
        uuid assigned_staff_id FK
        string status
    }
    patient_chat_context {
        uuid conversation_id PK,FK
        uuid patient_id FK
    }
    staff_agent_context {
        uuid conversation_id PK,FK
        uuid staff_id FK
        uuid context_patient_id FK
    }
    patient_memory_items {
        uuid id PK
        uuid user_id FK
    }
    patient_open_loops {
        uuid id PK
        uuid user_id FK
        string status
    }
    chat_takeover_cases {
        uuid id PK
        uuid patient_user_id FK
        string session_id
        string status
        string priority
        uuid assigned_staff_id FK
    }
    chat_takeover_messages {
        uuid id PK
        uuid case_id FK
    }
    chat_takeover_audit_events {
        uuid id PK
        uuid case_id FK
        uuid actor_user_id FK
    }
    zalo_user_mappings {
        uuid id PK
        uuid user_id FK
        string phone
    }
    users {
        uuid id PK
        string full_name
    }
    patient_profiles {
        uuid id PK
        string full_name
    }
```

## Bảng không có trong sơ đồ

| Bảng | Lý do |
|---|---|
| `catalog_audit_events` | Nhật ký thay đổi danh mục; chỉ trỏ về `users` (người thao tác) |
| `chat_conversations`, `chat_turns` | Không có model ORM (truy cập bằng SQL thuần trong `src/services/chat_history.py`), nên không sinh được từ metadata. `chat_turns.conversation_id` → `chat_conversations.id` |

> ⚠️ 11 bảng trong sơ đồ 2 và 4 (`patient_profiles`, `patient_relationships`, `package_requests`, `conversations`, `conversation_participants`, `messages`, `handoffs`, `patient_chat_context`, `staff_agent_context`, `patient_memory_items`, `patient_open_loops`) **không được migration Alembic tạo ra**. Chi tiết và đề xuất xử lý: [schema-overview.md](schema-overview.md#️-lệch-giữa-model-và-migration).
