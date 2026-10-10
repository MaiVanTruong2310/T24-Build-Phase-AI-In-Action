-- =========================================================================
-- MIGRATION: DỌN DẸP & TỐI ƯU HÓA DATABASE SUPABASE (VGREENAI / P-124)
-- =========================================================================

-- PHẦN 1: XÓA CÁC INDEX & CONSTRAINT TRÙNG LẶP (DUPLICATE INDEXES)
-- Lý do: Giảm dung lượng RAM đệm, tăng tốc độ ghi dữ liệu (INSERT/UPDATE)

-- 1.1. Xóa các Index trùng lặp tạo bởi lệnh CREATE INDEX
DROP INDEX IF EXISTS public.ix_doctors_code;
DROP INDEX IF EXISTS public.ix_facilities_code;
DROP INDEX IF EXISTS public.ix_services_code;
DROP INDEX IF EXISTS public.ix_specialties_code;
DROP INDEX IF EXISTS public.ix_users_phone;

-- 1.2. Xóa Constraint trùng lặp trên bảng doctor_specialties (Dùng DROP CONSTRAINT thay vì DROP INDEX)
-- (Giữ lại constraint: doctor_specialties_doctor_id_specialty_id_key)
ALTER TABLE public.doctor_specialties DROP CONSTRAINT IF EXISTS uq_doctor_specialty;


-- PHẦN 2: TỐI ƯU HIỆU NĂNG CHO RLS POLICIES CỦA PACKAGE & ZALO
-- Lý do: Tránh re-evaluate hàm auth.uid() cho từng dòng bằng cú pháp (select auth.uid())
DROP POLICY IF EXISTS package_requests_authenticated_select ON public.package_requests;
CREATE POLICY package_requests_authenticated_select 
ON public.package_requests 
FOR SELECT 
TO authenticated 
USING ((SELECT auth.uid()) = requested_by_user_id OR (SELECT auth.uid()) = patient_id);

DROP POLICY IF EXISTS zalo_user_mappings_authenticated_select ON public.zalo_user_mappings;
CREATE POLICY zalo_user_mappings_authenticated_select 
ON public.zalo_user_mappings 
FOR SELECT 
TO authenticated 
USING ((SELECT auth.uid()) = user_id);

-- Tối ưu Multiple Permissive Policies trên disease_triage
DROP POLICY IF EXISTS "Allow write access for authenticated and anon" ON public.disease_triage;


-- PHẦN 3: GỠ BỎ CÁC BẢNG DƯ THỪA / KHÔNG SỬ DỤNG (TOÀN BỘ 0 ROWS)
-- Lưu ý: Hệ thống chính thức đang dùng doctor_schedules, booking_holds, bookings.
-- 5 bảng consultation_* và weekly_shifts là mô hình ca khám cũ bị bỏ quên (toàn bộ 0 dòng).
-- Bảng doctor_services và patient_open_loops cũng có 0 dòng và không có luồng sử dụng.
DROP TABLE IF EXISTS public.consultation_request_events CASCADE;
DROP TABLE IF EXISTS public.consultation_requests CASCADE;
DROP TABLE IF EXISTS public.consultation_slots CASCADE;
DROP TABLE IF EXISTS public.consultation_sessions CASCADE;
DROP TABLE IF EXISTS public.weekly_shifts CASCADE;
DROP TABLE IF EXISTS public.doctor_services CASCADE;
