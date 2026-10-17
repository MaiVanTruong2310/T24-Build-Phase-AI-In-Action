# Từ điển dữ liệu — VCare+ (P-124)

> Mô tả **từng cột của từng bảng** trong PostgreSQL: kiểu dữ liệu, ràng buộc, ý nghĩa và mức độ nhạy cảm.
> Căn cứ: `develop` commit `69e5833` (12/10/2026). Kiểu dữ liệu, khóa, ràng buộc và mặc định được **lấy tự động** từ model SQLAlchemy (`src/models/`). Riêng `chat_conversations`, `chat_turns` lấy từ migration `0021_chat_history_tables.py`. Cột "Ý nghĩa" do nhóm viết, vì code không có comment mô tả cột.
> Xem kèm: [schema-overview.md](schema-overview.md) (danh sách bảng, khóa ngoại), [erd.md](erd.md) (sơ đồ quan hệ).

## Cách đọc

| Cột trong bảng | Nghĩa |
|---|---|
| **Kiểu** | Kiểu PostgreSQL. `UUID` = mã định danh ngẫu nhiên; `VARCHAR(n)` = chuỗi tối đa n ký tự; `TEXT` = chuỗi dài; `TIMESTAMPTZ` = ngày giờ có múi giờ; `JSONB` = dữ liệu dạng JSON |
| **Trống được** | `Có` = được để `NULL` |
| **Khóa / ràng buộc** | `PK` khóa chính · `FK → bảng.cột` khóa ngoại · `UNIQUE` không được trùng |
| **Mặc định** | Giá trị tự gán khi không truyền vào; "tự sinh" = do ứng dụng tạo (ví dụ UUID mới) |

### Phân loại dữ liệu

| Nhãn | Nghĩa | Ví dụ |
|---|---|---|
| **PII** | Thông tin **định danh cá nhân**: xác định được một người cụ thể | Họ tên, SĐT, email, CCCD, mã BHYT, ngày sinh, địa chỉ |
| **PHI** | Thông tin **sức khỏe** gắn với một người | Triệu chứng, tiền sử bệnh, nội dung chat, lý do khám, kết quả AI |
| **🔐 Bí mật** | Dữ liệu xác thực / bảo mật, **không bao giờ** hiển thị hay ghi log | Mã OTP đã băm, refresh token đã băm |
| **Công khai** | Thông tin chủ đích hiển thị công khai | Họ tên, giới thiệu, ảnh của bác sĩ |
| **—** | Dữ liệu kỹ thuật hoặc danh mục, không nhạy cảm | Khóa, trạng thái, thời gian, danh mục khoa |

Mã khóa ngoại trỏ tới bệnh nhân (`user_id`, `patient_profile_id`…) được xếp **—** vì bản thân mã không lộ thông tin, nhưng **mọi bảng có cột này đều là dữ liệu cá nhân** khi ghép với bảng `users`.

## Tổng hợp dữ liệu nhạy cảm

| Nhãn | Số cột | Cột |
|---|---|---|
| **PII** | 25 | `users`: `full_name`, `phone`, `email`, `date_of_birth`, `gender`, `citizen_id`, `health_insurance_code` · `patient_profiles`: `full_name`, `contact_phone`, `date_of_birth`, `gender`, `citizen_id`, `health_insurance_code`, `address` · `package_requests`: `patient_name`, `patient_phone`, `patient_email`, `date_of_birth`, `gender` · `coordination_cases.patient` · `otp_challenges.target` · `refresh_sessions.user_agent` · `zalo_user_mappings`: `zalo_chat_id`, `zalo_display_name`, `phone` |
| **PHI** | 29 | `users.patient_details` (hồ sơ sức khỏe) · nội dung chat: `chat_turns.user_text/assistant_text/result`, `chat_conversations.checkpoint`, `messages.content/metadata`, `chat_takeover_messages.content`, `coordination_messages.body` · kết quả AI và ngữ cảnh: `coordination_cases.ai_snapshot/checkpoint/plan`, `patient_chat_context.context_data`, `staff_agent_context.context_data`, `chat_takeover_cases.summary` · bộ nhớ dài hạn: `patient_memory_items.fact_key/fact_value`, `patient_open_loops.payload` · lý do khám và ghi chú: `bookings.reason/patient_note/staff_note`, `consultation_requests.reason/patient_note/staff_note`, `package_requests.note/staff_note`, `coordination_events.note`, `consultation_request_events.note`, `handoffs.reason` |
| **🔐 Bí mật** | 4 | `otp_challenges.code_hash`, `refresh_sessions.token_hash`, `bookings.idempotency_hash`, `chat_conversations.lease_token` |

### Hiện trạng bảo vệ dữ liệu nhạy cảm

| Biện pháp | Có chưa | Ghi chú |
|---|---|---|
| Băm OTP và refresh token | ✅ | Chỉ lưu bản băm (`code_hash`, `token_hash`) |
| Che CCCD / BHYT khi nhân viên xem danh sách bệnh nhân | ✅ | `citizen_id_masked`, `health_insurance_code_masked` (`src/schemas/staff_patient.py`) |
| Tách ảnh chân dung khỏi response hồ sơ | ✅ | `portrait_image` trong `patient_details` chỉ lấy qua API riêng |
| Phân quyền truy cập theo vai trò | ✅ | Xem `docs/api/endpoints.md` |
| **Mã hóa cột khi lưu** (CCCD, BHYT, `patient_details`, nội dung chat) | ❌ | Không có mã hóa ở mức cột: dữ liệu lưu dạng thường trong PostgreSQL. Đề bài yêu cầu "mã hóa" PII/PHI |
| Thời hạn lưu trữ / xóa dữ liệu cũ | ❌ | Chưa có cơ chế tự xóa hội thoại, bộ nhớ dài hạn sau một thời gian |
| Ghi log không chứa PII/PHI | ⚠️ | Webhook Zalo ghi toàn bộ nội dung tin nhắn vào log (xem `docs/api/zalo.md`) |

**Đề xuất:** mã hóa ở mức cột cho `citizen_id`, `health_insurance_code`, `patient_details` (dùng `pgcrypto` hoặc mã hóa ở tầng ứng dụng); bật mã hóa ổ đĩa của database trên server; đặt thời hạn lưu trữ cho `chat_turns`, `messages`, `patient_memory_items`.

---

# Chi tiết từng bảng

## Tài khoản & xác thực

### `users`

Tài khoản người dùng (bệnh nhân và nhân viên) và hồ sơ ứng dụng.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `auth_user_id` | UUID | Có | UNIQUE |  | Mã người dùng bên Supabase Auth | — |
| `email` | VARCHAR(320) | Có | UNIQUE |  | Email | PII |
| `phone` | VARCHAR(32) | Có | UNIQUE |  | Số điện thoại | PII |
| `role` | VARCHAR(32) | Không |  | patient | `patient` / `staff` | — |
| `status` | VARCHAR(32) | Không |  | pending_verification | Ví dụ `pending_verification`, `active` | — |
| `full_name` | VARCHAR(200) | Có |  |  | Họ tên | PII |
| `date_of_birth` | DATE | Có |  |  | Ngày sinh | PII |
| `gender` | VARCHAR(16) | Có |  |  | Giới tính | PII |
| `citizen_id` | VARCHAR(12) | Có |  |  | Số CCCD (12 số) | PII |
| `health_insurance_code` | VARCHAR(32) | Có |  |  | Mã thẻ BHYT | PII |
| `patient_details` | JSONB | Có |  |  | Hồ sơ sức khỏe (JSON): tiền sử bệnh, nhóm máu, dị ứng, thuốc đang dùng, chỉ số sinh tồn, liên hệ khẩn cấp, ảnh chân dung | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `otp_challenges`

Mã OTP đã phát (lưu dạng băm).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Có | FK → `users.id` |  | Tài khoản sở hữu | — |
| `target` | VARCHAR(320) | Không |  |  | Email / SĐT nhận OTP | PII |
| `purpose` | VARCHAR(32) | Không |  |  | Mục đích: đăng ký, đăng nhập, đặt lại mật khẩu | — |
| `code_hash` | VARCHAR(128) | Không |  |  | Mã OTP đã băm | 🔐 Bí mật |
| `expires_at` | TIMESTAMPTZ | Không |  |  | Thời điểm hết hạn | — |
| `attempts` | INTEGER | Không |  | 0 | Số lần nhập sai | — |
| `consumed_at` | TIMESTAMPTZ | Có |  |  | Thời điểm đã dùng | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `refresh_sessions`

Phiên đăng nhập (refresh token, lưu dạng băm).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `token_hash` | VARCHAR(128) | Không | UNIQUE |  | Refresh token đã băm | 🔐 Bí mật |
| `expires_at` | TIMESTAMPTZ | Không |  |  | Thời điểm hết hạn | — |
| `revoked_at` | TIMESTAMPTZ | Có |  |  | Thời điểm thu hồi | — |
| `replaced_by` | UUID | Có |  |  | Phiên mới thay thế (xoay vòng token) | — |
| `user_agent` | VARCHAR(512) | Có |  |  | Trình duyệt / thiết bị | PII |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `last_used_at` | TIMESTAMPTZ | Có |  |  | Lần dùng gần nhất | — |


## Hồ sơ bệnh nhân & bộ nhớ

### `patient_profiles`

Hồ sơ người khám (bản thân hoặc người thân) do một tài khoản quản lý.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `patient_user_id` | UUID | Không | FK → `users.id`, UNIQUE |  | Tài khoản bệnh nhân | — |
| `linked_user_id` | UUID | Có | FK → `users.id`, UNIQUE |  | Tài khoản riêng của người khám (nếu có) | — |
| `full_name` | VARCHAR(120) | Có |  |  | Họ tên | PII |
| `date_of_birth` | DATE | Có |  |  | Ngày sinh | PII |
| `gender` | VARCHAR(24) | Có |  |  | Giới tính | PII |
| `contact_phone` | VARCHAR(20) | Có |  |  | SĐT liên hệ của người khám | PII |
| `citizen_id` | VARCHAR(12) | Có |  |  | Số CCCD (12 số) | PII |
| `health_insurance_code` | VARCHAR(32) | Có |  |  | Mã thẻ BHYT | PII |
| `address` | VARCHAR(500) | Có |  |  | Địa chỉ | PII |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `patient_relationships`

Quan hệ và quyền của tài khoản với hồ sơ người khám.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `patient_profile_id` | UUID | Không | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `relationship` | VARCHAR(24) | Không |  |  | Quan hệ: bản thân, bố/mẹ, con… | — |
| `status` | VARCHAR(16) | Không |  | active | Trạng thái | — |
| `can_book` | BOOLEAN | Không |  | True | Được đặt lịch hộ | — |
| `can_view_medical` | BOOLEAN | Không |  | False | Được xem hồ sơ y tế | — |
| `consent_at` | TIMESTAMPTZ | Có |  |  | Thời điểm đồng ý | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `patient_memory_items`

Bộ nhớ dài hạn của bệnh nhân (dữ kiện agent ghi nhớ qua nhiều phiên).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `category` | VARCHAR(50) | Không |  |  | Phân loại | — |
| `fact_key` | VARCHAR(100) | Không |  |  | Tên dữ kiện được ghi nhớ | PHI |
| `fact_value` | JSONB | Không |  | tự sinh | Giá trị dữ kiện (JSON) | PHI |
| `provenance` | VARCHAR(50) | Không |  | patient_reported | Nguồn gốc dữ kiện | — |
| `confidence` | FLOAT | Không |  | 0.8 | Độ tin cậy 0–1 | — |
| `taint_status` | VARCHAR(30) | Không |  | clean | Mức tin cậy nguồn (chống nhiễm dữ liệu sai) | — |
| `source_session_id` | VARCHAR(100) | Có |  |  | Phiên chat tạo ra dữ kiện | — |
| `valid_until` | TIMESTAMPTZ | Có |  |  | Hết hiệu lực lúc | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `patient_open_loops`

Việc còn dang dở với bệnh nhân (cần nhắc lại ở phiên sau).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `loop_type` | VARCHAR(50) | Không |  |  | Loại việc dang dở | — |
| `payload` | JSONB | Không |  | tự sinh | Dữ liệu việc dang dở (JSON) | PHI |
| `status` | VARCHAR(30) | Không |  | open | Trạng thái | — |
| `due_at` | TIMESTAMPTZ | Có |  |  | Hạn xử lý | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `patient_chat_context`

Ngữ cảnh hiện tại của một hội thoại bệnh nhân.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `conversation_id` | UUID | Không | PK, FK → `conversations.id` |  | Hội thoại | — |
| `patient_id` | UUID | Có | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `booking_id` | UUID | Có |  |  | Lịch hẹn liên quan | — |
| `specialty_id` | UUID | Có |  |  | Chuyên khoa | — |
| `current_stage` | VARCHAR(64) | Không |  | GENERAL_SUPPORT | Bước hiện tại của hội thoại | — |
| `context_data` | JSONB | Có |  |  | Ngữ cảnh (JSON): triệu chứng, lựa chọn… | PHI |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |


## Danh mục y tế

### `specialties`

Danh mục chuyên khoa.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `code` | VARCHAR(64) | Không | UNIQUE |  | Mã định danh nghiệp vụ (duy nhất) | — |
| `name` | VARCHAR(200) | Không |  |  | Tên | — |
| `description` | TEXT | Có |  |  | Mô tả | — |
| `status` | VARCHAR(16) | Không |  | active | Trạng thái | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `services`

Danh mục dịch vụ / gói khám.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `code` | VARCHAR(64) | Không | UNIQUE |  | Mã định danh nghiệp vụ (duy nhất) | — |
| `name` | VARCHAR(200) | Không |  |  | Tên | — |
| `description` | TEXT | Có |  |  | Mô tả | — |
| `duration_minutes` | INTEGER | Có |  |  | Thời lượng (phút) | — |
| `price` | NUMERIC(12, 2) | Có |  |  | Giá (VNĐ) | — |
| `original_price` | NUMERIC(12, 2) | Có |  |  | Giá gốc trước giảm | — |
| `category` | VARCHAR(100) | Có |  |  | Phân loại | — |
| `booking_mode` | VARCHAR(20) | Không |  | group | `doctor_visit` (khám riêng) / `group` (khám nhóm) | — |
| `features` | JSON | Có |  |  | Danh sách đặc điểm (JSON) | — |
| `patient_count` | INTEGER | Có |  | 0 | Số bệnh nhân đã dùng (hiển thị) | — |
| `satisfaction_rate` | FLOAT | Có |  |  | Tỷ lệ hài lòng (hiển thị) | — |
| `status` | VARCHAR(16) | Không |  | active | Trạng thái | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `facilities`

Danh mục cơ sở y tế.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `code` | VARCHAR(64) | Không | UNIQUE |  | Mã định danh nghiệp vụ (duy nhất) | — |
| `name` | VARCHAR(200) | Không |  |  | Tên | — |
| `description` | TEXT | Có |  |  | Mô tả | — |
| `address` | VARCHAR(500) | Có |  |  | Địa chỉ | — |
| `phone` | VARCHAR(32) | Có |  |  | Số điện thoại | — |
| `status` | VARCHAR(16) | Không |  | active | Trạng thái | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `doctors`

Hồ sơ bác sĩ.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `code` | VARCHAR(64) | Không | UNIQUE |  | Mã định danh nghiệp vụ (duy nhất) | — |
| `full_name` | VARCHAR(200) | Không |  |  | Họ tên | Công khai |
| `bio` | TEXT | Có |  |  | Giới thiệu | Công khai |
| `avatar_url` | VARCHAR(500) | Có |  |  | Ảnh đại diện | Công khai |
| `title` | VARCHAR(64) | Có |  |  | Học hàm / học vị viết tắt | — |
| `professional_role` | VARCHAR(40) | Không |  | Bác sĩ | Vai trò chuyên môn (mặc định `Bác sĩ`) | — |
| `honors` | VARCHAR(80)[] | Không |  | tự sinh | Danh hiệu | — |
| `academic_ranks` | VARCHAR(80)[] | Không |  | tự sinh | Học hàm | — |
| `degrees` | VARCHAR(80)[] | Không |  | tự sinh | Học vị | — |
| `languages` | TEXT[] | Không |  | tự sinh | Ngôn ngữ | — |
| `position` | VARCHAR(160) | Có |  |  | Chức vụ | — |
| `experience_years` | INTEGER | Có |  |  | Số năm kinh nghiệm | — |
| `education` | TEXT[] | Không |  | tự sinh | Quá trình đào tạo | — |
| `work_history` | TEXT[] | Không |  | tự sinh | Quá trình công tác | — |
| `awards` | TEXT[] | Không |  | tự sinh | Giải thưởng | — |
| `status` | VARCHAR(16) | Không |  | active | Trạng thái | — |
| `review_status` | VARCHAR(32) | Không |  | approved | Trạng thái duyệt hồ sơ (`approved`…) | — |
| `booking_enabled` | BOOLEAN | Không |  | True | Có nhận đặt lịch không | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `doctor_specialties`

Bác sĩ – chuyên khoa (nhiều–nhiều).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `specialty_id` | UUID | Không | FK → `specialties.id` |  | Chuyên khoa | — |
| `is_primary` | BOOLEAN | Không |  | False | Là mục chính | — |

### `doctor_facilities`

Bác sĩ – cơ sở làm việc (nhiều–nhiều).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `department` | VARCHAR(160) | Có |  |  | Khoa / phòng ban | — |
| `room` | VARCHAR(64) | Có |  |  | Phòng khám | — |
| `active_from` | DATE | Có |  |  | Làm việc từ ngày | — |
| `active_to` | DATE | Có |  |  | Làm việc đến ngày | — |
| `position` | VARCHAR(160) | Có |  |  | Chức vụ tại cơ sở | — |
| `is_primary` | BOOLEAN | Không |  | False | Là mục chính | — |

### `doctor_services`

Bác sĩ – dịch vụ thực hiện (nhiều–nhiều).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `service_id` | UUID | Không | FK → `services.id` |  | Dịch vụ | — |
| `active` | BOOLEAN | Không |  | True | Đang hiệu lực | — |

### `catalog_audit_events`

Nhật ký thay đổi danh mục và lịch.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `actor_id` | UUID | Có | FK → `users.id` |  | Người thực hiện thao tác | — |
| `entity_type` | VARCHAR(64) | Không |  |  | Loại đối tượng bị thay đổi | — |
| `entity_id` | UUID | Không |  |  | Mã đối tượng bị thay đổi | — |
| `action` | VARCHAR(64) | Không |  |  | Loại thao tác | — |
| `payload` | JSON | Không |  | tự sinh | Dữ liệu (JSON) | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |


## Lịch bác sĩ

### `doctor_schedules`

Khung giờ làm việc / khám của bác sĩ.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `starts_at` | TIMESTAMPTZ | Không |  |  | Giờ bắt đầu | — |
| `ends_at` | TIMESTAMPTZ | Không |  |  | Giờ kết thúc | — |
| `capacity` | INTEGER | Không |  |  | Sức chứa (1 với khám riêng) | — |
| `status` | VARCHAR(16) | Không |  | available | `available` / `cancelled` / … | — |
| `version` | INTEGER | Không |  | 1 | Phiên bản (khóa lạc quan, chống ghi đè) | — |
| `source_system` | VARCHAR(64) | Có |  |  | Hệ thống nguồn khi nhập lịch | — |
| `external_schedule_id` | VARCHAR(128) | Có |  |  | Mã lịch ở hệ thống nguồn | — |
| `created_by` | UUID | Có | FK → `users.id` |  | Người tạo | — |
| `updated_by` | UUID | Có | FK → `users.id` |  | Người cập nhật gần nhất | — |
| `cancellation_reason` | TEXT | Có |  |  | Lý do hủy | — |
| `service_id` | UUID | Có | FK → `services.id` |  | Dịch vụ | — |
| `busy_reason` | VARCHAR(32) | Có |  |  | Lý do bận | — |
| `note` | TEXT | Có |  |  | Ghi chú | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `weekly_shifts`

Khung trực lặp lại hằng tuần (sinh phiên tư vấn).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `weekday` | INTEGER | Không |  |  | Thứ trong tuần (0 = thứ Hai) | — |
| `period` | VARCHAR(12) | Không |  |  | Buổi: `morning` / `afternoon` | — |
| `start_time` | TIME | Không |  |  | Giờ bắt đầu | — |
| `slot_minutes` | INTEGER | Không |  | 30 | Độ dài mỗi khung (phút) | — |
| `slot_count` | INTEGER | Không |  | 5 | Số khung mỗi buổi | — |
| `effective_from` | DATE | Không |  |  | Áp dụng từ ngày | — |
| `effective_until` | DATE | Có |  |  | Áp dụng đến ngày | — |
| `active` | BOOLEAN | Không |  | True | Đang hiệu lực | — |

### `consultation_sessions`

Phiên tư vấn theo ngày, sinh từ khung trực tuần.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `weekly_shift_id` | UUID | Không | FK → `weekly_shifts.id` |  | Khung trực tuần sinh ra phiên | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `session_date` | DATE | Không |  |  | Ngày của phiên | — |
| `period` | VARCHAR(12) | Không |  |  | Buổi: `morning` / `afternoon` | — |
| `status` | VARCHAR(16) | Không |  | open | Trạng thái | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `consultation_slots`

Khung giờ con trong một phiên tư vấn.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `session_id` | UUID | Không | FK → `consultation_sessions.id` |  | Phiên tư vấn | — |
| `schedule_id` | UUID | Không | FK → `doctor_schedules.id` |  | Khung giờ của bác sĩ | — |
| `ordinal` | INTEGER | Không |  |  | Thứ tự khung trong phiên | — |


## Đặt lịch

### `bookings`

Lịch hẹn khám.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `requested_by_user_id` | UUID | Có | FK → `users.id` |  | Tài khoản thực hiện yêu cầu (có thể đặt hộ) | — |
| `schedule_id` | UUID | Có | FK → `doctor_schedules.id` |  | Khung giờ của bác sĩ | — |
| `hold_id` | UUID | Có | FK → `booking_holds.id`, UNIQUE |  | Chỗ giữ đã dùng để đặt | — |
| `doctor_id` | UUID | Không | FK → `doctors.id` |  | Bác sĩ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `starts_at` | TIMESTAMPTZ | Không |  |  | Giờ bắt đầu | — |
| `ends_at` | TIMESTAMPTZ | Không |  |  | Giờ kết thúc | — |
| `service_id` | UUID | Không | FK → `services.id` |  | Dịch vụ | — |
| `specialty_id` | UUID | Không | FK → `specialties.id` |  | Chuyên khoa | — |
| `encounter_type` | VARCHAR(20) | Không |  |  | Hình thức khám: `in_person` / `telehealth` | — |
| `reason` | TEXT | Không |  |  | Lý do khám / lý do | PHI |
| `patient_note` | TEXT | Có |  |  | Ghi chú của bệnh nhân | PHI |
| `status` | VARCHAR(24) | Không |  | pending_approval | `pending_approval` / `confirmed` / `rejected` / `cancelled` / `expired` | — |
| `expired_at` | TIMESTAMPTZ | Có |  |  | Hạn duyệt (tạo + 24 giờ) | — |
| `cancellation_reason` | TEXT | Có |  |  | Lý do hủy | — |
| `staff_note` | TEXT | Có |  |  | Ghi chú của nhân viên | PHI |
| `idempotency_key` | VARCHAR(128) | Có |  |  | Khóa chống tạo trùng (header `Idempotency-Key`) | — |
| `idempotency_hash` | VARCHAR(64) | Có |  |  | Băm nội dung request đi kèm khóa chống trùng | 🔐 Bí mật |
| `reviewed_by` | UUID | Có | FK → `users.id` |  | Nhân viên duyệt | — |
| `reviewed_at` | TIMESTAMPTZ | Có |  |  | Thời điểm duyệt | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `booking_holds`

Giữ chỗ tạm một khung giờ trước khi đặt.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `requested_by_user_id` | UUID | Có | FK → `users.id` |  | Tài khoản thực hiện yêu cầu (có thể đặt hộ) | — |
| `schedule_id` | UUID | Không | FK → `doctor_schedules.id` |  | Khung giờ của bác sĩ | — |
| `service_id` | UUID | Không | FK → `services.id` |  | Dịch vụ | — |
| `specialty_id` | UUID | Không | FK → `specialties.id` |  | Chuyên khoa | — |
| `status` | VARCHAR(16) | Không |  | active | `active` / `consumed` / `released` / `expired` | — |
| `expires_at` | TIMESTAMPTZ | Không |  |  | Thời điểm hết hạn | — |
| `released_at` | TIMESTAMPTZ | Có |  |  | Thời điểm trả chỗ | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `consultation_requests`

Yêu cầu tư vấn của bệnh nhân vào một phiên.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `requested_by_user_id` | UUID | Có | FK → `users.id` |  | Tài khoản thực hiện yêu cầu (có thể đặt hộ) | — |
| `patient_id` | UUID | Không | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `session_id` | UUID | Không | FK → `consultation_sessions.id` |  | Phiên tư vấn được chọn | — |
| `service_id` | UUID | Không | FK → `services.id` |  | Dịch vụ | — |
| `specialty_id` | UUID | Không | FK → `specialties.id` |  | Chuyên khoa | — |
| `encounter_type` | VARCHAR(20) | Không |  | in_person | Hình thức khám: `in_person` / `telehealth` | — |
| `reason` | TEXT | Không |  |  | Lý do khám / lý do | PHI |
| `patient_note` | TEXT | Có |  |  | Ghi chú của bệnh nhân | PHI |
| `status` | VARCHAR(16) | Không |  | pending | Trạng thái | — |
| `assigned_slot_id` | UUID | Có | FK → `consultation_slots.id` |  | Khung giờ được phân công | — |
| `booking_id` | UUID | Có | FK → `bookings.id`, UNIQUE |  | Lịch hẹn liên quan | — |
| `staff_note` | TEXT | Có |  |  | Ghi chú của nhân viên | PHI |
| `reviewed_by` | UUID | Có | FK → `users.id` |  | Nhân viên duyệt | — |
| `reviewed_at` | TIMESTAMPTZ | Có |  |  | Thời điểm duyệt | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `consultation_request_events`

Lịch sử xử lý yêu cầu tư vấn.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `request_id` | UUID | Không | FK → `consultation_requests.id` |  | Yêu cầu tư vấn | — |
| `actor_id` | UUID | Có | FK → `users.id` |  | Người thực hiện thao tác | — |
| `action` | VARCHAR(32) | Không |  |  | Loại thao tác | — |
| `note` | TEXT | Có |  |  | Ghi chú | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `package_requests`

Yêu cầu đăng ký gói khám.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `patient_id` | UUID | Có | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `requested_by_user_id` | UUID | Có | FK → `users.id` |  | Tài khoản thực hiện yêu cầu (có thể đặt hộ) | — |
| `service_id` | UUID | Không | FK → `services.id` |  | Dịch vụ | — |
| `facility_id` | UUID | Không | FK → `facilities.id` |  | Cơ sở | — |
| `preferred_date` | DATE | Không |  |  | Ngày khám mong muốn | — |
| `preferred_period` | VARCHAR(12) | Không |  | morning | Buổi mong muốn | — |
| `patient_name` | VARCHAR(120) | Có |  |  | Họ tên người khám | PII |
| `patient_phone` | VARCHAR(20) | Có |  |  | SĐT người khám | PII |
| `patient_email` | VARCHAR(320) | Có |  |  | Email người khám | PII |
| `gender` | VARCHAR(16) | Có |  |  | Giới tính | PII |
| `date_of_birth` | DATE | Có |  |  | Ngày sinh | PII |
| `note` | TEXT | Có |  |  | Ghi chú | PHI |
| `status` | VARCHAR(16) | Không |  | pending | Trạng thái | — |
| `staff_note` | TEXT | Có |  |  | Ghi chú của nhân viên | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |


## Điều phối (HITL Workbench)

### `coordinator_members`

Thành viên điều phối và quyền hạn.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `user_id` | UUID | Không | PK, FK → `users.id` |  | Tài khoản nhân viên (khóa chính) | — |
| `enabled` | BOOLEAN | Không |  | True | Còn quyền điều phối | — |
| `is_admin` | BOOLEAN | Không |  | False | Là quản trị điều phối | — |
| `on_duty` | BOOLEAN | Không |  | False | Đang trực | — |
| `facility_ids` | JSONB | Không |  | tự sinh | Danh sách cơ sở được phụ trách (rỗng = tất cả) | — |
| `clinical_qualification` | VARCHAR(200) | Không |  |  | Trình độ chuyên môn | — |

### `coordination_policy`

Chính sách điều phối (một dòng duy nhất).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | INTEGER | Không | PK |  | Luôn = 1 | — |
| `hold_minutes` | INTEGER | Không |  |  | Phút giữ chỗ khi lên phương án | — |
| `response_minutes` | INTEGER | Không |  |  | Hạn phản hồi ca thường (phút) | — |
| `emergency_response_minutes` | INTEGER | Không |  |  | Hạn phản hồi ca cấp cứu (phút) | — |
| `payment_instructions` | TEXT | Không |  |  | Hướng dẫn chuyển cọc | — |
| `refund_policy` | TEXT | Không |  |  | Chính sách hoàn cọc | — |

### `coordination_cases`

Ca điều phối trên bàn điều phối (HITL).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `source` | VARCHAR(30) | Không |  |  | Nguồn tạo ca (chat, gói khám, tư vấn…) | — |
| `source_id` | VARCHAR(200) | Không |  |  | Mã đối tượng nguồn | — |
| `owner_key` | VARCHAR(100) | Có |  |  | Khóa chủ sở hữu (tài khoản hoặc mã khách) | — |
| `session_id` | VARCHAR(200) | Có |  |  | Mã phiên chat | — |
| `patient_id` | UUID | Có | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `requested_by_user_id` | UUID | Có | FK → `users.id` |  | Tài khoản thực hiện yêu cầu (có thể đặt hộ) | — |
| `patient` | JSONB | Không |  | tự sinh | Thông tin liên hệ bệnh nhân (JSON): họ tên, SĐT, ngày sinh… | PII |
| `ai_snapshot` | JSONB | Không |  | tự sinh | Ảnh chụp kết quả AI (JSON): triệu chứng, chuyên khoa, mức ATS, tóm tắt bàn giao | PHI |
| `checkpoint` | JSONB | Không |  | tự sinh | Trạng thái agent của phiên chat (JSON) | PHI |
| `plan` | JSONB | Không |  | tự sinh | Phương án khám (JSON): chuyên khoa, dịch vụ, khung giờ, bệnh nhân đồng ý | PHI |
| `facility_id` | UUID | Có | FK → `facilities.id` |  | Cơ sở | — |
| `assigned_to` | UUID | Có | FK → `users.id` |  | Điều phối viên phụ trách | — |
| `status` | VARCHAR(24) | Không |  | new | 13 trạng thái vòng đời ca (xem `docs/api/staff.md`) | — |
| `priority` | INTEGER | Không |  | 3 | 0 = cấp cứu … 3 | — |
| `control` | VARCHAR(12) | Không |  | ai | `ai` / `human`: ai đang trả lời chat | — |
| `version` | INTEGER | Không |  | 1 | Phiên bản (khóa lạc quan, chống ghi đè) | — |
| `due_at` | TIMESTAMPTZ | Có |  |  | Hạn xử lý | — |
| `follow_up_at` | TIMESTAMPTZ | Có |  |  | Hẹn nhắc việc | — |
| `booking_id` | UUID | Có | FK → `bookings.id` |  | Lịch hẹn liên quan | — |
| `legacy_takeover_case_id` | UUID | Có | UNIQUE |  | Ca tiếp quản cũ tương ứng | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `coordination_events`

Nhật ký thao tác trên ca điều phối.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `case_id` | UUID | Không | FK → `coordination_cases.id` |  | Ca điều phối / ca tiếp quản | — |
| `actor_id` | UUID | Có | FK → `users.id` |  | Người thực hiện thao tác | — |
| `action` | VARCHAR(40) | Không |  |  | Loại thao tác | — |
| `note` | TEXT | Không |  |  | Ghi chú | PHI |
| `details` | JSONB | Không |  | tự sinh | Chi tiết (JSON) | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `coordination_messages`

Tin nhắn giữa điều phối viên và bệnh nhân trong ca.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `case_id` | UUID | Không | FK → `coordination_cases.id` |  | Ca điều phối / ca tiếp quản | — |
| `client_id` | VARCHAR(128) | Không |  |  | Mã chống gửi trùng | — |
| `sender` | VARCHAR(20) | Không |  |  | Người gửi: bệnh nhân / nhân viên / AI | — |
| `actor_id` | UUID | Có | FK → `users.id` |  | Người thực hiện thao tác | — |
| `body` | TEXT | Không |  |  | Nội dung tin nhắn | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `coordination_deposits`

Khoản đặt cọc của ca điều phối.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `case_id` | UUID | Không | FK → `coordination_cases.id` |  | Ca điều phối / ca tiếp quản | — |
| `amount` | INTEGER | Không |  |  | Số tiền cọc | — |
| `currency` | VARCHAR(3) | Không |  | VND | Đơn vị tiền (VND) | — |
| `status` | VARCHAR(24) | Không |  | requested | `requested` / `verified` / `expired` / `refund_pending` / `refunded` / `voided` | — |
| `instructions` | TEXT | Không |  |  | Hướng dẫn thanh toán tại thời điểm yêu cầu | — |
| `refund_policy` | TEXT | Không |  |  | Chính sách hoàn cọc | — |
| `transaction_reference` | VARCHAR(200) | Có |  |  | Mã giao dịch chuyển cọc | — |
| `refund_reference` | VARCHAR(200) | Có | UNIQUE |  | Mã giao dịch hoàn tiền | — |
| `evidence` | TEXT | Có |  |  | Bằng chứng đối soát | — |
| `verified_by` | UUID | Có | FK → `users.id` |  | Nhân viên xác minh | — |
| `expires_at` | TIMESTAMPTZ | Không |  |  | Thời điểm hết hạn | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |


## Hội thoại & tiếp quản

### `chat_conversations`

Lịch sử hội thoại chat của người đã đăng nhập (không có model ORM).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK |  | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `session_id` | VARCHAR(200) | Không |  |  | Mã phiên chat | — |
| `title` | VARCHAR(200) | Không |  |  | Tiêu đề (80 ký tự đầu của tin nhắn đầu) | — |
| `patient_profile_id` | UUID | Có | FK → `patient_profiles.id` |  | Hồ sơ người khám | — |
| `checkpoint` | JSONB | Không |  | '{}' | Trạng thái agent rút gọn (JSON) để khôi phục ngữ cảnh | PHI |
| `lease_token` | UUID | Có |  |  | Khóa đang xử lý lượt chat | 🔐 Bí mật |
| `busy_until` | TIMESTAMPTZ | Có |  |  | Khóa hết hạn lúc | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `chat_turns`

Từng lượt hỏi – đáp trong hội thoại chat (không có model ORM).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK |  | Khóa chính | — |
| `conversation_id` | UUID | Không | FK → `chat_conversations.id` |  | Hội thoại | — |
| `request_id` | UUID | Không |  |  | Mã lượt gửi (chống gửi trùng) | — |
| `user_text` | TEXT | Không |  |  | Tin nhắn của bệnh nhân | PHI |
| `assistant_text` | TEXT | Có |  |  | Câu trả lời của trợ lý | PHI |
| `result` | JSONB | Có |  |  | Phản hồi đầy đủ của agent (JSON) | PHI |
| `status` | VARCHAR(20) | Không |  |  | `processing` / `completed` / `failed` | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `conversations`

Hội thoại hợp nhất (web, Zalo, nhân viên).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `category` | VARCHAR(32) | Không |  | PATIENT_SUPPORT | Phân loại | — |
| `mode` | VARCHAR(32) | Không |  | AI | Chế độ hội thoại | — |
| `status` | VARCHAR(32) | Không |  | ACTIVE | Trạng thái | — |
| `patient_id` | UUID | Có | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `created_by_type` | VARCHAR(32) | Không |  | PATIENT | Loại người tạo | — |
| `created_by_id` | UUID | Có |  |  | Mã người tạo | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |
| `closed_at` | TIMESTAMPTZ | Có |  |  | Thời điểm đóng | — |

### `conversation_participants`

Người tham gia hội thoại.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `conversation_id` | UUID | Không | FK → `conversations.id` |  | Hội thoại | — |
| `participant_type` | VARCHAR(32) | Không |  |  | Loại người tham gia | — |
| `participant_id` | UUID | Có |  |  | Mã người tham gia | — |
| `role` | VARCHAR(64) | Có |  |  | Vai trò | — |
| `joined_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tham gia | — |
| `left_at` | TIMESTAMPTZ | Có |  |  | Thời điểm rời | — |

### `messages`

Tin nhắn trong hội thoại hợp nhất.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `conversation_id` | UUID | Không | FK → `conversations.id` |  | Hội thoại | — |
| `sender_type` | VARCHAR(32) | Không |  |  | Loại người gửi | — |
| `sender_id` | UUID | Có |  |  | Mã người gửi | — |
| `message_type` | VARCHAR(32) | Không |  | TEXT | Loại tin nhắn | — |
| `content` | TEXT | Có |  |  | Nội dung tin nhắn | PHI |
| `metadata` | JSONB | Có |  |  | Dữ liệu bổ sung (JSON) | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `handoffs`

Chuyển giao hội thoại từ AI sang người thật.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `conversation_id` | UUID | Không | FK → `conversations.id` |  | Hội thoại | — |
| `from_actor_type` | VARCHAR(32) | Không |  | AGENT | Chuyển từ (AI…) | — |
| `to_actor_type` | VARCHAR(32) | Không |  | STAFF | Chuyển sang (nhân viên…) | — |
| `reason` | VARCHAR(64) | Không |  | MANUAL_REVIEW | Lý do khám / lý do | PHI |
| `agent_confidence` | NUMERIC | Có |  |  | Độ tin cậy của AI khi chuyển | — |
| `requested_by_type` | VARCHAR(32) | Không |  | AGENT | Loại người yêu cầu chuyển | — |
| `requested_by_id` | UUID | Có |  |  | Mã người yêu cầu chuyển | — |
| `assigned_staff_id` | UUID | Có | FK → `users.id` |  | Nhân viên được giao | — |
| `status` | VARCHAR(32) | Không |  | REQUESTED | Trạng thái | — |
| `requested_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm yêu cầu | — |
| `accepted_at` | TIMESTAMPTZ | Có |  |  | Thời điểm nhận | — |
| `resolved_at` | TIMESTAMPTZ | Có |  |  | Thời điểm đóng | — |

### `staff_agent_context`

Ngữ cảnh của trợ lý AI dành cho nhân viên.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `conversation_id` | UUID | Không | PK, FK → `conversations.id` |  | Hội thoại | — |
| `staff_id` | UUID | Không | FK → `users.id` |  | Nhân viên | — |
| `context_patient_id` | UUID | Có | FK → `users.id` |  | Bệnh nhân đang xem | — |
| `context_booking_id` | UUID | Có |  |  | Lịch hẹn đang xem | — |
| `context_department_id` | UUID | Có |  |  | Khoa đang xem | — |
| `task_type` | VARCHAR(64) | Có |  |  | Loại tác vụ | — |
| `context_data` | JSONB | Có |  |  | Ngữ cảnh (JSON) | PHI |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `chat_takeover_cases`

Ca tiếp quản chat (cơ chế cũ).

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `patient_user_id` | UUID | Không | FK → `users.id` |  | Tài khoản bệnh nhân | — |
| `session_id` | VARCHAR(128) | Không |  |  | Mã phiên chat | — |
| `status` | VARCHAR(32) | Không |  | queued | Trạng thái | — |
| `priority` | VARCHAR(16) | Không |  | normal | Mức ưu tiên | — |
| `workflow_status` | VARCHAR(64) | Không |  | HUMAN_HELP_REQUESTED | Trạng thái agent lúc chuyển | — |
| `summary` | JSONB | Có |  |  | Tóm tắt (JSON) | PHI |
| `assigned_staff_id` | UUID | Có | FK → `users.id` |  | Nhân viên được giao | — |
| `claimed_at` | TIMESTAMPTZ | Có |  |  | Thời điểm nhận | — |
| `resolved_at` | TIMESTAMPTZ | Có |  |  | Thời điểm đóng | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `chat_takeover_messages`

Tin nhắn trong ca tiếp quản.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `case_id` | UUID | Không | FK → `chat_takeover_cases.id` |  | Ca điều phối / ca tiếp quản | — |
| `author_type` | VARCHAR(16) | Không |  |  | Loại người viết | — |
| `author_user_id` | UUID | Có | FK → `users.id` |  | Người viết | — |
| `content` | TEXT | Không |  |  | Nội dung tin nhắn | PHI |
| `client_message_id` | VARCHAR(128) | Có |  |  | Mã chống gửi trùng | — |
| `metadata` | JSONB | Có |  |  | Dữ liệu bổ sung (JSON) | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |

### `chat_takeover_audit_events`

Nhật ký ca tiếp quản.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `case_id` | UUID | Không | FK → `chat_takeover_cases.id` |  | Ca điều phối / ca tiếp quản | — |
| `actor_user_id` | UUID | Có | FK → `users.id` |  | Người thực hiện thao tác | — |
| `event_type` | VARCHAR(32) | Không |  |  | Loại sự kiện | — |
| `metadata` | JSONB | Có |  |  | Dữ liệu bổ sung (JSON) | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |


## Thông báo & kênh ngoài

### `notifications`

Thông báo gửi tới người dùng.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `user_id` | UUID | Không | FK → `users.id` |  | Tài khoản sở hữu | — |
| `booking_id` | UUID | Có | FK → `bookings.id` |  | Lịch hẹn liên quan | — |
| `kind` | VARCHAR(32) | Không |  |  | Loại: `booking_confirmed`, `booking_rejected`, `appointment_reminder`… | — |
| `status` | VARCHAR(16) | Không |  | pending | Trạng thái | — |
| `title` | VARCHAR(200) | Không |  |  | Tiêu đề / chức danh | — |
| `message` | TEXT | Không |  |  | Nội dung thông báo | — |
| `dedupe_key` | VARCHAR(160) | Không |  |  | Khóa chống tạo trùng thông báo | — |
| `available_at` | TIMESTAMPTZ | Không |  |  | Hiển thị từ lúc | — |
| `delivered_at` | TIMESTAMPTZ | Có |  |  | Đã gửi lúc | — |
| `read_at` | TIMESTAMPTZ | Có |  |  | Đã đọc lúc | — |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

### `zalo_user_mappings`

Liên kết tài khoản Zalo với người dùng.

| Cột | Kiểu | Trống được | Khóa / ràng buộc | Mặc định | Ý nghĩa | Phân loại |
|---|---|---|---|---|---|---|
| `id` | UUID | Không | PK | tự sinh | Khóa chính | — |
| `zalo_chat_id` | VARCHAR(128) | Không | UNIQUE |  | Mã chat Zalo của người dùng | PII |
| `zalo_display_name` | VARCHAR(200) | Có |  |  | Tên hiển thị trên Zalo | PII |
| `user_id` | UUID | Có | FK → `users.id` |  | Tài khoản sở hữu | — |
| `phone` | VARCHAR(32) | Có |  |  | SĐT đã liên kết (qua lệnh `/link`) | PII |
| `created_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm tạo | — |
| `updated_at` | TIMESTAMPTZ | Không |  | `now()` | Thời điểm cập nhật gần nhất | — |

