# Migration cơ sở dữ liệu — VCare+ (P-124)

> Thứ tự migration Alembic, cách chạy, và cách xử lý database đã chạy **chuỗi migration cũ**.
> Căn cứ: `develop` commit `69e5833` (12/10/2026); chuỗi cũ lấy từ commit `300ec0f` (05/10/2026, trước PR #33). Head được kiểm tra bằng `alembic heads`.
> Xem kèm: [schema-overview.md](schema-overview.md).

## 1. Thứ tự migration hiện tại

27 revision, **1 head: `0024_schedule_service_and_busy_reason`**.

| # | Revision | Làm gì |
|---|---|---|
| 1 | `0001_auth_foundation` | Bảng `users`, `otp_challenges`, `refresh_sessions` |
| 2 | `0002_user_personal_information` | Thông tin cá nhân của người dùng |
| 3 | `0003_medical_catalog` | Danh mục: chuyên khoa, dịch vụ, cơ sở, bác sĩ, bảng liên kết |
| 4 | `0004_staff_role_alignment` | Chuẩn hóa vai trò staff |
| 5 | `3c5a170017bb` | Thêm `avatar_url` cho bác sĩ |
| 6 | `44837e30b196` | Bổ sung cột cho dịch vụ |
| 7 | `0005_schedule_management` | Bảng `doctor_schedules` |
| 8 | `0006_schedule_overlap_guard` | Chặn lịch trùng giờ |
| 9 | `0007_booking_core` | Bảng `bookings` |
| 10 | `0008_booking_approval_workflow` | Luồng duyệt lịch |
| 11 | `0009_booking_requested_time` | Đặt lịch theo thời gian mong muốn |
| 12 | `0010_booking_holds_idempotency` | Bảng `booking_holds`, khóa chống tạo trùng |
| 13 | `0011_booking_notifications` | Bảng `notifications` |
| 14 | `0012_consultation_coordination` | Bảng `weekly_shifts`, `consultation_sessions`, `consultation_slots`, `consultation_requests`, `consultation_request_events` |
| 15 | `0013_doctor_discovery` | Cột tra cứu bác sĩ: kinh nghiệm, chức vụ, cơ sở chính |
| 16 | `0014_doctor_role_backfill` | Cột `professional_role` cho bác sĩ |
| 17 | `0015_coordinator_workbench` | Các bảng bàn điều phối (`coordination_*`, `coordinator_members`) |
| 18 | `0016_add_auth_user_id_to_users` | Liên kết người dùng với Supabase Auth |
| 19 | `0017_add_patient_details_to_users` | Cột hồ sơ sức khỏe `patient_details` |
| 20 | `0018_chat_takeover` | Bảng `chat_takeover_*` |
| 21 | `0019_booking_expiry_status` | Trạng thái `expired` cho lịch hẹn |
| 22 | `0020_reconcile_model_schema` | Bổ sung cột còn thiếu ở `bookings`, `doctors`, `doctor_facilities` cho database bị lệch |
| 23a | `0021_chat_history_tables` | Bảng `chat_conversations`, `chat_turns` |
| 24a | `0022_booking_expired_at` | Cột `expired_at` cho lịch hẹn |
| 23b | `0021_workbench_takeover_compatibility` | Tương thích dữ liệu tiếp quản cũ với bàn điều phối |
| 25 | `0023_merge_workbench_booking_heads` | **Gộp 2 nhánh** `0022` và `0021_workbench…` |
| 26 | `0024_schedule_service_and_busy_reason` | Dịch vụ và lý do bận cho khung giờ bác sĩ |

```text
0001 → … → 0020_reconcile_model_schema
              ├─ 0021_chat_history_tables → 0022_booking_expired_at ──┐
              └─ 0021_workbench_takeover_compatibility ───────────────┴─ 0023_merge → 0024 (head)
```

## 2. Cách chạy

Chạy ở thư mục gốc repo, với `DATABASE_URL` trỏ tới database cần cập nhật (đặt trong `.env`):

```bash
alembic current            # database đang ở revision nào
alembic heads              # revision mới nhất trong code (phải ra đúng 1 dòng: 0024…)
alembic history --verbose  # xem toàn bộ chuỗi
alembic upgrade head       # chạy tất cả migration còn thiếu
```

**Trước khi chạy trên database có dữ liệu thật: luôn sao lưu.**

```bash
pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%Y%m%d_%H%M).dump
```

Viết migration mới:

```bash
alembic revision -m "mo_ta_ngan"                  # viết tay
alembic revision --autogenerate -m "mo_ta_ngan"   # sinh từ model, bắt buộc rà lại trước khi commit
```

Đặt tên theo số thứ tự tiếp theo (`0025_…`). Nếu hai người cùng tạo migration song song (như hai file `0021`), phải tạo thêm một migration gộp (`alembic merge heads -m "merge_…"`) để chỉ còn **1 head**.

## 3. ⚠️ Hiện trạng: migration chưa được chạy tự động

| Nơi | Thực tế |
|---|---|
| Docker Compose | **Không có** service chạy `alembic upgrade head` (service `db-migrate` cũ đã bị bỏ) |
| CI/CD (`.github/workflows/ci_cd.yml`) | Không có bước chạy migration. `DATABASE_AUTO_CREATE=false` chỉ được đặt cho bước **test** |
| Ứng dụng khi khởi động | `DATABASE_AUTO_CREATE` mặc định là **`True`** (`src/config.py`): chạy `Base.metadata.create_all` để **tạo bảng còn thiếu** |

**Hệ quả:**
- Database production hiện được giữ đúng cấu trúc chủ yếu nhờ `create_all`, **không phải nhờ Alembic**.
- `create_all` chỉ **tạo bảng mới**. Nó **không** thêm cột, sửa kiểu, thêm ràng buộc cho bảng đã có, và **không** cập nhật bảng `alembic_version`.
- 11 bảng có model nhưng không có migration (xem [schema-overview.md](schema-overview.md)) chỉ tồn tại nhờ cơ chế này.
- ⚠️ **Dựng database mới chỉ bằng `alembic upgrade head` nhiều khả năng lỗi ở `0020`.** Migration này tạo khóa ngoại `bookings.patient_profile_id → patient_profiles(id)` mà **không kiểm tra bảng có tồn tại không**, trong khi `patient_profiles` không được migration nào trước đó tạo ra (chỉ có trong `scripts/supabase/migrations/20261005000000_patient_family_profiles.sql`). Kết luận này rút ra từ việc đọc code, **chưa chạy thử trên PostgreSQL thật**. Cần kiểm chứng bằng cách chạy `alembic upgrade head` trên một database trống.

**Đề xuất:**
1. Thêm migration tạo `patient_profiles`, `patient_relationships` **trước** `0020` (hoặc cho `0020` kiểm tra bảng tồn tại), và migration `0025` tạo các bảng còn lại.
2. Thêm bước `alembic upgrade head` vào quy trình deploy, chạy **trước** khi khởi động container mới.
3. Đặt `DATABASE_AUTO_CREATE=false` trên production.

## 4. Database đã chạy chuỗi migration cũ 0012–0018

### 4.1. Chuyện gì đã xảy ra

Trước ngày 05/10/2026, `develop` có một chuỗi migration khác cho các số `0012`–`0015`. PR #33 và #34 đã thay bằng chuỗi hiện tại. **Mã revision `0016`, `0017`, `0018` giống nhau ở cả hai chuỗi**, còn `0012`–`0015` khác hoàn toàn:

| Số | Chuỗi cũ (`300ec0f`) | Chuỗi hiện tại |
|---|---|---|
| 0012 | `0012_delivery_metadata`: thêm cột gửi thông báo (`channel`, `provider`, `attempt_count`, `error`, `dead_letter`) vào `notifications` | `0012_consultation_coordination`: tạo 5 bảng lịch tư vấn |
| 0013 | `0013_booking_notification_kafka`: thêm `bookings.hold`, `bookings.expired_at` | `0013_doctor_discovery`: cột tra cứu bác sĩ |
| 0014 | `0014_remove_booking_holds`: **xóa bảng `booking_holds`**, cột `bookings.hold_id` và khóa ngoại liên quan | `0014_doctor_role_backfill`: cột `professional_role` |
| 0015 | `0015_schedule_types_and_notes`: thêm cột loại lịch, ghi chú cho `doctor_schedules` | `0015_coordinator_workbench`: tạo các bảng bàn điều phối |
| 0016–0018 | Cùng mã revision | Cùng mã revision |

### 4.2. Vì sao nguy hiểm

Database cũ có bảng `alembic_version` ghi `0018_chat_takeover`. Alembic thấy mã này **có trong chuỗi mới**, nên coi database đã chạy xong `0001`–`0018` của chuỗi mới, và `alembic upgrade head` **chỉ chạy `0019`–`0024`**. Kết quả:

- **Không bao giờ tạo** các bảng của `0012`–`0015` mới (lịch tư vấn, bàn điều phối), trừ khi `DATABASE_AUTO_CREATE=true` tạo hộ.
- Chuỗi cũ `0014_remove_booking_holds` **xóa cả bảng `booking_holds`** lẫn cột `bookings.hold_id`. `0020_reconcile_model_schema` thêm lại cột và khóa ngoại tới `booking_holds`, nhưng **không tạo lại bảng**. Nếu bảng chưa được `create_all` tạo lại, `0020` sẽ **lỗi** "relation booking_holds does not exist".
- Các cột thừa của chuỗi cũ (`notifications.dead_letter`, `bookings.hold`…) vẫn còn, gây lệch cấu trúc nhưng không làm lỗi ứng dụng.

Lệnh `alembic upgrade head` **không báo lỗi gì**, nên rất dễ không phát hiện ra.

### 4.3. Nhận biết database theo chuỗi cũ

```sql
-- 1. Revision hiện tại
SELECT version_num FROM alembic_version;

-- 2. Dấu vết chuỗi cũ: có kết quả = database đã chạy 0012/0013 CŨ
SELECT table_name, column_name FROM information_schema.columns
WHERE (table_name = 'notifications' AND column_name = 'dead_letter')
   OR (table_name = 'bookings'      AND column_name = 'hold');

-- 3. Dấu vết chuỗi mới: không có kết quả = THIẾU bảng của 0012/0015 MỚI
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('weekly_shifts', 'consultation_requests', 'coordination_cases');
```

| Kết quả | Kết luận |
|---|---|
| Câu 2 có dòng **và** câu 3 thiếu bảng | Database theo chuỗi cũ, **chưa** được sửa → xử lý theo 4.4 |
| Câu 2 có dòng, câu 3 đủ bảng | Database theo chuỗi cũ nhưng đã được `create_all` bù bảng → vẫn nên làm 4.4 (cách B) để khớp cấu trúc |
| Câu 2 không có dòng | Database theo chuỗi mới → chỉ cần `alembic upgrade head` |

### 4.4. Cách xử lý

**Cách A: Reset (dữ liệu dev / demo, không cần giữ).** Đơn giản và sạch nhất.

```bash
pg_dump "$DATABASE_URL" -Fc -f backup_truoc_reset.dump   # vẫn nên sao lưu
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
# Sau đó nạp lại dữ liệu mẫu (danh mục, bác sĩ, lịch) bằng script seed của nhóm
```

Trên Supabase: không xóa schema `public` nếu đang dùng chung cho Supabase Auth hoặc các bảng khác. Chỉ xóa các bảng của ứng dụng, hoặc tạo một project Supabase mới cho môi trường dev.

**Cách B: Giữ dữ liệu, sửa cấu trúc (staging / production).**

1. Sao lưu: `pg_dump … -Fc`.
2. Hạ mốc về **trước chỗ rẽ nhánh**, chỉ đổi mốc chứ **không chạy SQL**:
   ```bash
   alembic stamp 0011_booking_notifications
   ```
3. Chạy lại phần chuỗi mới. Các migration `0012`–`0015` mới hầu hết dùng `CREATE TABLE`, `ADD COLUMN`, nên có thể báo lỗi "đã tồn tại" nếu `create_all` đã tạo bảng trước. Khi đó, kiểm tra bảng đã đúng cấu trúc rồi `alembic stamp <revision đó>` để bỏ qua, và tiếp tục:
   ```bash
   alembic upgrade 0015_coordinator_workbench
   alembic stamp 0018_chat_takeover     # 0016–0018 giống nhau ở hai chuỗi, đã chạy rồi
   alembic upgrade head                 # 0019 → 0024
   ```
4. Nếu bảng `booking_holds` không còn (chuỗi cũ `0014` đã xóa), tạo lại bảng **trước** khi chạy tới `0020`. Cách nhanh: khởi động ứng dụng một lần với `DATABASE_AUTO_CREATE=true` để `create_all` tạo bảng còn thiếu, hoặc chạy lại phần `upgrade()` của `0010_booking_holds_and_idempotency`.
5. (Không bắt buộc) xóa các cột thừa của chuỗi cũ sau khi chắc chắn không code nào dùng: `notifications.channel`, `provider`, `attempt_count`, `error`, `dead_letter`; `bookings.hold`.
6. Chạy lại 3 câu SQL ở mục 4.3 và `pytest tests/ -m "not integration"` để xác nhận.

`alembic stamp` **chỉ ghi mốc** vào bảng `alembic_version`, không thay đổi cấu trúc. Dùng sai sẽ khiến Alembic bỏ qua migration thật. Luôn kiểm tra cấu trúc trước khi stamp.

### 4.5. Phòng tránh lặp lại

- **Không sửa hoặc thay migration đã được chạy ở môi trường khác.** Muốn thay đổi thì viết migration mới.
- Khi merge code từ nhánh khác có migration trùng số, đổi mã revision của nhánh mới về số tiếp theo, không dùng lại số cũ.
- Đưa `alembic upgrade head` vào quy trình deploy để phát hiện xung đột sớm.

## 5. Đối chiếu model với migration

> Thực hiện ngày 12/10/2026 trên `develop` `69e5833`.
>
> **Cách làm:** phân tích tĩnh, chưa chạy trên PostgreSQL thật. Một script đọc lần lượt 27 migration theo đúng thứ tự Alembic và dựng lại danh sách bảng / cột mà chuỗi migration tạo ra (gồm `op.create_table`, `op.add_column`, các câu SQL `CREATE TABLE` / `ALTER TABLE … ADD COLUMN` / `DROP COLUMN`), rồi so với cột của model SQLAlchemy. Mọi khác biệt đều được **kiểm tra tay** trong file migration; một khác biệt báo nhầm (các cột mảng của `doctors`, thực ra được thêm trong vòng lặp của `0020`) đã bị loại.

### 5.1. Mức bảng

| Loại | Bảng | Ghi chú |
|---|---|---|
| **Có model, không có migration** (11) | `patient_profiles`, `patient_relationships`, `package_requests`, `conversations`, `conversation_participants`, `messages`, `handoffs`, `patient_chat_context`, `staff_agent_context`, `patient_memory_items`, `patient_open_loops` | Chỉ được tạo bởi `create_all` (`DATABASE_AUTO_CREATE=true`) hoặc script ngoài Alembic. Xem mục 3 |
| **Có migration, không có model** (2) | `chat_conversations`, `chat_turns` | **Có chủ đích**: tạo ở `0021_chat_history_tables`, truy cập bằng SQL thuần trong `src/services/chat_history.py` |

### 5.2. Mức cột: model có, migration Alembic không tạo

| Bảng | Cột thiếu | Nguồn duy nhất tạo ra | Ảnh hưởng |
|---|---|---|---|
| `booking_holds` | `patient_profile_id`, `requested_by_user_id` | `scripts/supabase/migrations/20261005000000_patient_family_profiles.sql` | Database dựng chỉ bằng Alembic sẽ **lỗi khi giữ chỗ** (model đọc/ghi cột không tồn tại) |
| `consultation_requests` | `patient_profile_id`, `requested_by_user_id` | như trên | Lỗi khi tạo / xem yêu cầu tư vấn |
| `coordination_cases` | `patient_profile_id`, `requested_by_user_id` | như trên | Lỗi trên **bàn điều phối** |

Script Supabase thêm 2 cột này cho 5 bảng (`bookings`, `booking_holds`, `consultation_requests`, `package_requests`, `coordination_cases`). Alembic chỉ bổ sung lại cho `bookings` (trong `0020`). `create_all` **không** thêm cột vào bảng đã có, nên không bù được 3 bảng trên.

### 5.3. Mức cột: migration tạo, model không còn dùng

| Bảng | Cột thừa | Tạo ở | Ảnh hưởng |
|---|---|---|---|
| `users` | `password_hash`, `verified_at` | `0001_auth_foundation` | Không ảnh hưởng (cho phép NULL). Còn sót từ thời tự quản lý mật khẩu, trước khi chuyển sang Supabase Auth |
| `doctors` | `license_number` (UNIQUE), `email`, `phone`, `date_of_birth`, `gender` | `0003_medical_catalog` | Không ảnh hưởng (cho phép NULL). Thông tin cá nhân của bác sĩ không còn được dùng |

Các cột thừa của chuỗi migration cũ (`notifications.dead_letter`…, `bookings.hold`) chỉ có ở database đã chạy chuỗi cũ: xem mục 4.

### 5.4. Migration phụ thuộc Supabase

`0012_consultation_coordination` và `0015_coordinator_workbench` chạy `ENABLE ROW LEVEL SECURITY` và `REVOKE ALL … FROM anon, authenticated` cho các bảng chúng tạo. `anon`, `authenticated` là **vai trò riêng của Supabase**, không có trên PostgreSQL thường. Vì vậy chuỗi migration hiện **chỉ chạy được trên Supabase**; chạy trên container `pgvector/pgvector:pg17` trong `docker-compose.yml` sẽ lỗi ngay ở `0012` với "role \"anon\" does not exist", trừ khi tạo trước 2 role này.

### 5.5. Tóm tắt và đề xuất

| Mức | Vấn đề | Đề xuất |
|---|---|---|
| 🔴 | 11 bảng và 6 cột (5.2) chỉ có ngoài Alembic. Database dựng bằng Alembic sẽ thiếu và lỗi | Viết migration `0025` tạo 11 bảng; thêm `patient_profile_id`, `requested_by_user_id` cho 3 bảng ở 5.2; đặt bước tạo `patient_profiles` **trước** `0020` (xem mục 3) |
| 🟠 | Migration chỉ chạy được trên Supabase (5.4) | Bọc lệnh `REVOKE` trong khối kiểm tra role tồn tại (`DO $$ … IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') …`), hoặc ghi rõ môi trường dev phải dùng Supabase |
| 🟡 | 7 cột thừa (5.3) | Xóa bằng một migration riêng khi đã chắc không còn code nào dùng |

**Cần kiểm chứng:** toàn bộ mục 5 là kết quả đọc code. Nên chạy `alembic upgrade head` trên một database Supabase trống, rồi dùng `alembic check` để Alembic tự so cấu trúc thật với model.
