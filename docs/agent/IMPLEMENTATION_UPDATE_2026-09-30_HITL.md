# CẬP NHẬT HITL & DỮ LIỆU BÁC SĨ — 30/09/2026

## Kết luận kiểm toán trước sửa

- Luồng cũ dùng danh sách bác sĩ hardcode, tự sinh slot hex và chỉ khóa bằng bộ nhớ tiến trình.
- Thông báo “giữ chỗ thành công” không tương ứng với một bản ghi bền vững trong database.
- Supabase hiện kết nối được bằng vai trò `anon`, nhưng các bảng bác sĩ/lịch trả về 0 dòng khả kiến và bảng `booking_requests` chưa tồn tại trên project đang cấu hình.
- `DATABASE_URL` hiện là giá trị mẫu localhost; project ref của MCP và REST không trùng nhau. Vì vậy migration mới **chưa được xác nhận đã deploy lên Supabase từ xa**.

## Kiến trúc sau sửa

1. `DoctorScheduleService` ưu tiên Supabase và chỉ coi slot là thật khi có UUID từ `doctor_schedules` với `status = available`.
2. Nếu chưa có lịch, hệ thống chỉ hiển thị hồ sơ có nguồn từ tập crawl 992 bác sĩ Vinmec; không gắn giờ trống giả.
3. Khách chưa đăng nhập được mở form HITL. Form thu thập họ tên, điện thoại, ngày sinh, giới tính, email, lựa chọn bác sĩ/ngày/buổi/cơ sở, thời gian liên hệ, ghi chú và consent.
4. Người dưới 18 tuổi bắt buộc có họ tên và điện thoại người giám hộ.
5. Backend ghi bảng `booking_requests` bằng `SUPABASE_SERVICE_ROLE_KEY` chỉ tồn tại phía server. `anon` không có quyền ghi PII trực tiếp.
6. Chỉ sau khi insert thành công mới trả `saved = true`, mã `YC-XXXXXXXX` và `PENDING_CONTACT`.
7. `PENDING_CONTACT` chỉ là hàng đợi điều phối viên; không phải lịch đã chốt. Lỗi ghi DB trả HTTP 503 và không xác nhận giả.

## Tăng cường trí thông minh ngữ cảnh

- Thêm lớp phân định chủ thể `self / other` và cô lập episode lâm sàng.
- Câu xã hội như bày tỏ thích/ghét không còn bị nhập vào triệu chứng hoặc kích hoạt lại ATS.
- Câu hỏi sức khỏe về người thứ ba không ghi đè hồ sơ của người dùng; hệ thống chỉ hướng dẫn chung và tôn trọng quyền đồng ý của người cần khám.
- Câu quay lại “tôi nên khám ở đâu” tiếp tục đúng episode trước đó.
- Tra cứu bác sĩ, lịch và form HITL không còn chiếm chỗ trong sliding window triệu chứng.

## Thành phần triển khai

- Migration: `scripts/supabase/migrations/20260930023321_guest_booking_requests.sql`
- Persistence: `src/medical_assistant/domain/booking_request_service.py`
- API: `POST /api/v1/booking-requests`
- UI form: `src/medical_assistant/web/static/app.js`
- Doctor grounding: `src/medical_assistant/domain/doctor_schedule_service.py`

## Việc bắt buộc trước khi chạy production

1. Chốt đúng Supabase project ref giữa REST, CLI và MCP.
2. Cấu hình `DATABASE_URL` thật hoặc đăng nhập lại Supabase CLI/MCP.
3. Apply migration lên đúng project.
4. Đặt `SUPABASE_SERVICE_ROLE_KEY` trong secret manager/.env phía server; không đưa vào frontend, Git hoặc `context_agent`.
5. Nạp dữ liệu thật vào `specialties`, `doctors`, `doctor_specialties`, `doctor_schedules` và kiểm thử RLS bằng vai trò anon/staff/service role.

