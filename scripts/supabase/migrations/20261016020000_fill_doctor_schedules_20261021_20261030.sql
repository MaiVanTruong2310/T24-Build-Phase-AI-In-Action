-- Bổ sung lịch trống 10 ngày (21/10–30/10/2026) cho mọi bác sĩ đang nhận lịch.
-- Lịch cũ chỉ đến 20/10. Giữ đúng mẫu sẵn có: mỗi ngày 2 ca (sáng 08:30–11:30, chiều 14:00–16:30 giờ VN),
-- capacity 1, cùng cơ sở bác sĩ đang có lịch, external_schedule_id GEN_{doctor}_{YYYYMMDD}_{AM|PM}.
-- Chỉ chèn thêm, không sửa/xoá dòng cũ (không cần bản sao lưu). Chạy lại an toàn (ON CONFLICT DO NOTHING).
-- Rollback: 20261016020000_fill_doctor_schedules_20261021_20261030_rollback.sql

insert into public.doctor_schedules (doctor_id, facility_id, starts_at, ends_at, capacity, status, source_system, external_schedule_id)
select
  d.id,
  f.facility_id,
  -- day::date + time = timestamp (giờ VN) → AT TIME ZONE ra timestamptz. Không bỏ ::date: generate_series trả
  -- timestamptz, khi đó AT TIME ZONE đổi ngược chiều và lệch 14 giờ (đã gặp, sửa bằng migration *_timezone).
  (day::date + s.start_time) at time zone 'Asia/Ho_Chi_Minh',
  (day::date + s.end_time) at time zone 'Asia/Ho_Chi_Minh',
  1,
  'available',
  'vinmec_booking_api',
  'GEN_' || d.id || '_' || to_char(day, 'YYYYMMDD') || '_' || s.period
from public.doctors d
-- Cơ sở của ca gần nhất (mỗi bác sĩ hiện có đúng 1 cơ sở trong lịch).
join lateral (
  select ds.facility_id
  from public.doctor_schedules ds
  where ds.doctor_id = d.id and ds.source_system = 'vinmec_booking_api'
  order by ds.starts_at desc
  limit 1
) f on true
cross join generate_series(date '2026-10-21', date '2026-10-30', interval '1 day') as day
cross join (values ('AM', time '08:30', time '11:30'), ('PM', time '14:00', time '16:30')) as s(period, start_time, end_time)
where d.status = 'active' and d.review_status = 'approved' and d.booking_enabled
on conflict (source_system, external_schedule_id) do nothing;
