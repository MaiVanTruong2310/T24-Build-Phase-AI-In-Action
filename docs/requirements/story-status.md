# Trạng thái thực hiện User Story — VCare+ (P-124)

> Đối chiếu từng story trong [user-stories.md](user-stories.md) với code nhánh `develop` (commit `42c909e`, 10/10/2026).
>
> **Cách kiểm chứng:**
> - Chạy toàn bộ test: `pytest tests/` → **749 pass, 5 fail, 18 skip** (không có key LLM, agent chạy nhánh dự phòng bằng luật).
> - Thử trực tiếp đồ thị agent với 9 câu (cấp cứu, chẩn đoán, kê đơn, triệu chứng thường).
> - Kiểm tra từng trang frontend có gọi API thật hay dùng dữ liệu mẫu.
>
> **Ký hiệu:** ✅ Xong · 🟡 Một phần (chạy được nhưng thiếu/sai một phần) · ❌ Chưa làm

## Tổng hợp

| Trạng thái | Số story |
|---|---|
| ✅ Xong | 31 |
| 🟡 Một phần | 4 |
| ❌ Chưa làm | 0 |

Các tính năng chưa làm đã được tách sang mục "Ngoài phạm vi" của `user-stories.md` nên không xuất hiện ở đây.

## Chi tiết

### E1. Trò chuyện & sàng lọc an toàn

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-01 Chat không cần tài khoản | ✅ | `frontend/src/features/chat/ChatAccessGate.tsx`; `optional_chat_user` trong `src/medical_assistant/api/routes.py` | |
| US-02 Phản hồi streaming | ✅ | `POST /chat/stream` trong `src/medical_assistant/api/routes.py` | |
| US-03 Cảnh báo cấp cứu | 🟡 | `src/medical_assistant/domain/triage_service.py`; thử trực tiếp: **6/6 ca cấp cứu được bắt** (đau ngực, đột quỵ, khó thở, tức ngực, trẻ sốt co giật, ý định tự tử) | Phát hiện đúng, nhưng **tên bệnh hiển thị cho bệnh nhân bị sai**: trẻ sốt co giật → "Hội chứng Sheehan" (khoa Tim mạch); ý định tự tử → "Ngộ độc cấp tính". Việc nêu tên bệnh cụ thể trong cảnh báo cũng sát ranh giới "không chẩn đoán" của đề |
| US-04 Không chẩn đoán, không kê đơn | ✅ | `src/medical_assistant/domain/guardrail_service.py`; thử trực tiếp: "Tôi bị bệnh gì?" → `GUARDRAIL_DIAGNOSIS`, "kê thuốc giảm đau" → `GUARDRAIL_MEDICATION` | 1 test luồng tổng hợp đang fail: `test_clinical_guardrails_flow.py::test_full_clinical_guardrails_conversation_flow` |
| US-05 Luôn có khuyến cáo y tế | 🟡 | `get_medical_disclaimer` (`language_service.py:345`), gắn tại `respond_node.py:1101` | Chỉ gắn khi có ngữ cảnh lâm sàng (`has_clinical_context`, `respond_node.py:1078`); câu chào hỏi / ngoài phạm vi không có khuyến cáo, giao diện cũng không có dòng khuyến cáo cố định. Đề yêu cầu **luôn** hiển thị |
| US-06 Hỏi rõ, không hỏi lặp | ✅ | `probing_service.py`, `clinical_fact_service.py`, `clinical_negation_service.py`; thử "đau đầu 3 ngày" → hỏi vị trí và thời gian | 1 test fail: `test_token_cost_optimization.py::test_sliding_window_memory_compression` |
| US-07 Chặn nội dung tấn công | ✅ | `src/medical_assistant/domain/security/`; nhóm test bảo mật pass | |

### E2. Định hướng chuyên khoa & tra cứu

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-08 Gợi ý chuyên khoa | 🟡 | `specialty_router.py`; thử "đau đầu" → Thần kinh, "đau bụng phải" → Tiêu hóa – Gan mật | 1 test fail: `test_multi_specialty_extraction.py::test_primary_specialty_is_first_recommendation`, tức là khi có nhiều triệu chứng, khoa chính chưa luôn đứng đầu. Ngoài ra 1 test fail về mức khẩn cấp (`tests/test_medical_assistant/test_triage_specificity.py`, "bụng chướng, đầy hơi sau ăn" bị nâng mức) |
| US-09 Gợi ý cơ sở theo khu vực | ✅ | `src/medical_assistant/domain/facility_service.py`; `tests/test_medical_assistant/test_doctor_facility_linking.py` | |
| US-10 Tra cứu bác sĩ | ✅ | `GET /doctors`, `/doctors/facets`, `/doctors/{id}`; `DoctorDirectory.tsx`, `DoctorProfile.tsx` | |

### E3. Đặt lịch & theo dõi

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-11 Yêu cầu đặt lịch trong chat | ✅ | `POST /booking-requests` → `intake()` trong `src/services/workbench.py`; `tests/test_workbench.py` | Yêu cầu nay đi thẳng vào hàng đợi điều phối viên |
| US-12 Đặt lịch hộ người dưới 18 tuổi | ✅ | `_is_minor` + kiểm tra người giám hộ trong `intake()` | |
| US-13 Đặt lịch theo khung giờ trống | ✅ | `src/api/endpoints/booking.py`, `src/services/booking.py`; `tests/test_booking/` | |
| US-14 Theo dõi tiến trình | ✅ | `GET /bookings`, `/coordination/live/mine`; `AppointmentProgress.tsx`, `AppointmentHistory.tsx` | |
| US-15 Hủy / đổi lịch | 🟡 | `POST /bookings/{id}/cancel`, `/reschedule` | Chưa đổi được lịch loại "thời gian mong muốn" (code trả `BOOKING_NOT_RESCHEDULABLE`) |
| US-16 Thông báo lịch hẹn | ✅ | `src/services/notification.py` (6 loại thông báo); nhắc lịch chạy trong tác vụ nền `src/main.py` | Chỉ thông báo trong ứng dụng; không có email và không có thông báo Zalo |
| US-17 Yêu cầu gặp người thật | ✅ | `POST /coordination/live/{session_id}/request-human` | |

### E4. Tài khoản & hồ sơ

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-18 Đăng ký, đăng nhập, quên mật khẩu | ✅ | `src/api/endpoints/auth.py`, `src/services/supabase_auth.py`; `tests/test_auth/` | Toàn bộ qua Supabase Auth bằng email; mã xác nhận và liên kết khôi phục gửi qua email. `/auth/reset-password` đã ngừng dùng (luôn trả 400) |
| US-19 Hồ sơ sức khỏe & người thân | ✅ | `/users/me`, `/patient-profiles`; `PatientProfile`, `FamilyProfiles` | |
| US-20 Lịch sử hội thoại | ✅ | `GET/DELETE /chat/conversations/{session_id}`; `src/services/chat_history.py` | |

### E5. Điều phối

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-21 Hàng đợi ca theo cơ sở | ✅ | `GET /staff/workbench/cases`, `scope()` trong `src/services/workbench.py` | |
| US-22 Nhận ca, phân công | ✅ | `action()` (`claim`…`reopen`), kiểm tra `version`; `tests/test_coordinator_regressions.py` | |
| US-23 Xem bối cảnh AI | ✅ | `detail()`, `snapshot()` | |
| US-24 Tiếp quản chat | ✅ | action `takeover`/`resume`; `/staff/chat-takeover/*`; `tests/test_chat_takeover.py` | |
| US-25 Lên phương án khám | ✅ | `validate_plan()`, `set_plan()` | |
| US-26 Đặt cọc | ✅ | `request_deposit()`, `verify_deposit()`, `expire_deposits()` | Xác minh cọc thủ công, chưa thanh toán trực tuyến |
| US-27 Chốt lịch (HITL) | ✅ | `confirm()`: bắt buộc có cọc `verified` | |
| US-28 Duyệt lịch đặt trực tiếp | ✅ | `PATCH /staff/bookings/{id}/status`; tự hết hạn trong tác vụ nền | |
| US-28b Ca trực & bàn giao | ✅ | `/staff/workbench/duty/start`, `/end`, `/handover` | |

### E6. Quản trị

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-29 Quản lý danh mục | ✅ | `/staff/doctors`, `/staff/services`…; `StaffAdminGate.tsx`; `tests/test_catalog/` | |
| US-30 Lịch làm việc bác sĩ | ✅ | `/staff/schedules`, `/schedules/import`; `tests/test_booking`, test lịch | |
| US-31 Chính sách & thành viên | ✅ | `PUT /staff/workbench/policy`, `/members` | |
| US-32 Tổng quan | ✅ | `/staff/dashboard/summary`; `tests/test_staff_dashboard.py`; trang không dùng dữ liệu mẫu | `/staff/patients` chưa có test riêng |

### E7. Zalo

| Story | Trạng thái | Bằng chứng | Ghi chú |
|---|---|---|---|
| US-33 Tư vấn qua Zalo | ✅ | `_handle_agent_chat_turn`, `split_message_chunks` (1800 ký tự); `tests/test_zalo.py` | |
| US-34 Tra cứu lịch hẹn qua Zalo | ✅ | `_handle_my_bookings` trong `src/zalo/service.py` | Chưa có test riêng |

## Việc cần làm tiếp (theo thứ tự ưu tiên)

1. **US-03:** sửa nhãn bệnh trong cảnh báo cấp cứu (trẻ co giật, ý định tự tử). Cân nhắc chỉ ghi nhóm dấu hiệu (ví dụ "dấu hiệu thần kinh cấp") thay vì tên bệnh, để không vi phạm ràng buộc "không chẩn đoán". Với ý định tự tử, nên kèm số đường dây hỗ trợ tâm lý.
2. **US-05:** luôn hiển thị khuyến cáo (thêm dòng cố định dưới khung chat hoặc luôn gắn ở backend).
3. **US-08, US-04, US-06:** sửa 4 test đang fail (hoặc cập nhật test nếu hành vi mới là đúng).
4. **US-15:** hỗ trợ đổi lịch cho lịch loại "thời gian mong muốn".
5. Thêm test cho `/staff/patients` và tra cứu lịch hẹn qua Zalo.

## Ghi chú kỹ thuật

- Hai router cùng khai báo `POST /api/v1/chat` và `GET /api/v1/status` (`src/medical_assistant/api/routes.py` và `src/api/routes.py`). FastAPI chỉ dùng router được gắn trước, nên router kia không bao giờ chạy. Test cũng cảnh báo `Duplicate Operation ID`.
- 1 test fail về hạ tầng: `test_api_security_gaps.py::test_health_ready_returns_200`. Test này cần database thật, không ảnh hưởng chức năng.
