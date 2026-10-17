-- Rollback 20261016020000_fill_doctor_schedules_20261021_20261030.sql
-- Xoá các ca đã sinh cho 21/10–30/10/2026, BỎ QUA ca đã có lịch hẹn / giữ chỗ / phiếu điều phối tham chiếu
-- (FK ON DELETE RESTRICT) để không làm mất lịch hẹn của bệnh nhân.

delete from public.doctor_schedules ds
where ds.source_system = 'vinmec_booking_api'
  and ds.external_schedule_id ~ '^GEN_[0-9a-f-]{36}_202610(2[1-9]|30)_(AM|PM)$'
  and not exists (select 1 from public.bookings b where b.schedule_id = ds.id or b.appointment_schedule_id = ds.id)
  and not exists (select 1 from public.booking_holds h where h.schedule_id = ds.id)
  and not exists (select 1 from public.consultation_slots c where c.schedule_id = ds.id);
