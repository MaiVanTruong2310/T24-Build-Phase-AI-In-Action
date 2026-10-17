-- Sửa giờ các ca sinh bởi 20261016020000 (bản đầu lệch 14 giờ do AT TIME ZONE áp lên timestamptz).
-- Tính lại từ ngày + ca trong external_schedule_id. Lúc áp: 19.840 ca, chưa có lịch hẹn/giữ chỗ nào tham chiếu.
-- Chạy lại an toàn (kết quả giống nhau). Rollback chung: 20261016020000_..._rollback.sql

update public.doctor_schedules ds
set starts_at = (to_date(m[1], 'YYYYMMDD') + case m[2] when 'AM' then time '08:30' else time '14:00' end) at time zone 'Asia/Ho_Chi_Minh',
    ends_at   = (to_date(m[1], 'YYYYMMDD') + case m[2] when 'AM' then time '11:30' else time '16:30' end) at time zone 'Asia/Ho_Chi_Minh',
    updated_at = now()
from (
  select id, regexp_match(external_schedule_id, '_(\d{8})_(AM|PM)$') m
  from public.doctor_schedules
  where source_system = 'vinmec_booking_api'
    and external_schedule_id ~ '^GEN_[0-9a-f-]{36}_202610(2[1-9]|30)_(AM|PM)$'
) x
where ds.id = x.id;
