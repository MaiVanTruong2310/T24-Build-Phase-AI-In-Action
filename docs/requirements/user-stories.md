# User Stories — VCare+ (VMEC-01 / P-124)

> **Phạm vi:** chỉ gồm các tính năng **đã có trong code** nhánh `develop` (commit `42c909e`, 10/10/2026).
> Mỗi story ghi kèm vị trí code chính để đối chiếu. Trạng thái hoàn thành chi tiết của từng story được đánh giá riêng.
>
> **Định dạng:** _Là [tác nhân], tôi muốn [hành động], để [giá trị]._ Tiêu chí chấp nhận viết theo Given / When / Then.

## Tác nhân

| Mã | Tác nhân | Điều kiện trong hệ thống |
|---|---|---|
| BN-K | Bệnh nhân khách | Chưa đăng nhập, khai họ tên + số điện thoại để chat |
| BN | Bệnh nhân đã đăng nhập | `users.role = "patient"` |
| GH | Người giám hộ / người nhà | Bệnh nhân đăng nhập, đặt lịch cho hồ sơ người thân |
| DPV | Điều phối viên / lễ tân | `users.role = "staff"`, là `CoordinatorMember` (có thể giới hạn theo cơ sở) |
| QT | Quản trị điều phối | Staff có `is_admin = true` và không giới hạn cơ sở |
| ZL | Bệnh nhân qua Zalo | Nhắn tin cho Zalo Bot của hệ thống |

Bác sĩ **không** phải tác nhân: hệ thống chỉ lưu hồ sơ và lịch làm việc của bác sĩ, bác sĩ không đăng nhập.

## Danh sách story

| Nhóm | Story |
|---|---|
| E1. Trò chuyện & sàng lọc an toàn | US-01 → US-07 |
| E2. Định hướng chuyên khoa & tra cứu | US-08 → US-10 |
| E3. Đặt lịch & theo dõi (bệnh nhân) | US-11 → US-17 |
| E4. Tài khoản & hồ sơ | US-18 → US-20 |
| E5. Điều phối (điều phối viên) | US-21 → US-28 |
| E6. Quản trị | US-29 → US-32 |
| E7. Kênh Zalo | US-33 → US-34 |

---

## E1. Trò chuyện & sàng lọc an toàn

### US-01 — Chat không cần tài khoản
**Là** bệnh nhân khách, **tôi muốn** trò chuyện với trợ lý mà không phải đăng ký, **để** được hướng dẫn nhanh khi đang lo lắng về sức khỏe.

- **Given** tôi chưa đăng nhập và mở khung chat
  **When** tôi chọn chế độ khách, nhập họ tên (2–120 ký tự) và số điện thoại
  **Then** tôi gửi được tin nhắn và nhận phản hồi từ trợ lý.
- **Given** tôi không nhập họ tên hoặc số điện thoại
  **When** tôi bấm bắt đầu
  **Then** form không cho gửi.

_Code:_ `frontend/src/features/chat/ChatAccessGate.tsx`, `optional_chat_user` trong `src/medical_assistant/api/routes.py`

### US-02 — Nhận phản hồi dạng streaming
**Là** bệnh nhân, **tôi muốn** thấy câu trả lời hiện dần từng phần, **để** không phải chờ màn hình trống.

- **Given** tôi gửi một tin nhắn
  **When** hệ thống xử lý qua `POST /api/v1/chat/stream`
  **Then** tôi nhận lần lượt các sự kiện: khởi tạo phiên → nội dung từng phần → metadata (chuyên khoa, mức ATS, gợi ý trả lời nhanh) → kết thúc.

_Code:_ `src/medical_assistant/api/routes.py` (`/chat/stream`)

### US-03 — Cảnh báo cấp cứu thay vì đặt lịch
**Là** bệnh nhân, **tôi muốn** được cảnh báo ngay khi triệu chứng có dấu hiệu nguy hiểm, **để** đi cấp cứu kịp thời thay vì chờ lịch hẹn.

- **Given** tin nhắn của tôi có dấu hiệu cấp cứu (ví dụ "tức ngực, khó thở, vã mồ hôi")
  **When** hệ thống phân tích
  **Then** câu trả lời là cảnh báo cấp cứu, hướng dẫn gọi **115** hoặc đến phòng cấp cứu gần nhất, kèm mức ATS; hệ thống **không** đề xuất lịch khám.
- **Given** phiên chat đã được đánh dấu cấp cứu
  **When** tôi gửi yêu cầu đặt lịch thường cho phiên đó
  **Then** yêu cầu bị từ chối (HTTP 409).
- **Given** ca cấp cứu
  **When** hệ thống xử lý
  **Then** luật cấp cứu chạy **trước** khi gọi LLM (không tốn token LLM).

_Code:_ `src/medical_assistant/domain/triage_service.py`, `disease_triage.py`; kiểm tra 409 trong `routes.py` (`/booking-requests`)

### US-04 — Không chẩn đoán, không kê đơn
**Là** bệnh nhân, **tôi muốn** được giải thích rõ khi tôi hỏi "tôi bị bệnh gì" hoặc xin đơn thuốc, **để** hiểu vì sao cần gặp bác sĩ.

- **Given** tôi hỏi chẩn đoán ("Tôi bị bệnh gì?") hoặc xin kê thuốc
  **When** trợ lý trả lời
  **Then** trợ lý từ chối chẩn đoán/kê đơn, giải thích lý do và vẫn gợi ý chuyên khoa phù hợp để khám.

_Code:_ `src/medical_assistant/domain/guardrail_service.py`

### US-05 — Luôn có khuyến cáo y tế
**Là** bệnh nhân, **tôi muốn** mọi câu trả lời đều nhắc rằng thông tin chỉ mang tính tham khảo, **để** không nhầm trợ lý với bác sĩ.

- **Given** bất kỳ câu trả lời tư vấn nào
  **When** hiển thị cho tôi
  **Then** câu trả lời kèm khuyến cáo y tế (tiếng Việt hoặc tiếng Anh theo ngôn ngữ của tôi).

_Code:_ `src/medical_assistant/domain/language_service.py` (`get_medical_disclaimer`)

### US-06 — Được hỏi rõ triệu chứng, không bị hỏi lặp
**Là** bệnh nhân, **tôi muốn** trợ lý hỏi thêm từng câu một về triệu chứng và không hỏi lại điều tôi đã nói, **để** cuộc trò chuyện ngắn và tự nhiên.

- **Given** tôi mô tả triệu chứng còn thiếu thông tin (vị trí, thời gian, mức độ…)
  **When** trợ lý cần làm rõ
  **Then** trợ lý hỏi **một** câu tập trung.
- **Given** tôi đã nói "không sốt"
  **When** trợ lý hỏi tiếp
  **Then** trợ lý không hỏi lại về sốt và không coi sốt là triệu chứng của tôi.

_Code:_ `probing_service.py`, `clinical_fact_service.py`, `clinical_negation_service.py`

### US-07 — Chặn nội dung tấn công
**Là** người vận hành hệ thống (thông qua bệnh nhân), **tôi muốn** các câu lệnh tấn công (jailbreak, yêu cầu in system prompt) bị chặn, **để** trợ lý không bị lợi dụng.

- **Given** tin nhắn chứa lệnh kiểu "Ignore previous instructions…"
  **When** hệ thống kiểm tra đầu vào
  **Then** tin nhắn bị chặn, trợ lý trả lời an toàn và không gọi LLM.

_Code:_ `src/medical_assistant/domain/security/`

---

## E2. Định hướng chuyên khoa & tra cứu

### US-08 — Gợi ý chuyên khoa từ triệu chứng
**Là** bệnh nhân, **tôi muốn** biết nên khám chuyên khoa nào từ triệu chứng mô tả bằng lời thường, **để** không đặt nhầm khoa.

- **Given** tôi đã mô tả đủ triệu chứng
  **When** trợ lý kết thúc phần hỏi
  **Then** trợ lý nêu chuyên khoa phù hợp (có trong danh mục của hệ thống) và đề nghị tìm lịch khám.

_Code:_ `specialty_router.py`, `triage_service.py`

### US-09 — Gợi ý cơ sở theo khu vực
**Là** bệnh nhân, **tôi muốn** được gợi ý cơ sở gần nơi tôi ở, **để** đi khám thuận tiện.

- **Given** tôi nhắc tới khu vực (ví dụ "gần Long Biên")
  **When** trợ lý gợi ý
  **Then** trợ lý đề xuất cơ sở phù hợp trong danh mục cơ sở của hệ thống.

_Code:_ `src/medical_assistant/domain/facility_service.py`

### US-10 — Tra cứu bác sĩ
**Là** bệnh nhân, **tôi muốn** xem danh sách và hồ sơ bác sĩ theo chuyên khoa, cơ sở, **để** chọn bác sĩ phù hợp.

- **Given** tôi mở trang Bác sĩ
  **When** tôi lọc theo chuyên khoa / cơ sở
  **Then** danh sách chỉ gồm bác sĩ thỏa bộ lọc; bấm vào một bác sĩ thì xem được hồ sơ chi tiết.

_Code:_ `GET /doctors`, `/doctors/facets`, `/doctors/{id}`; `frontend/src/pages/DoctorDirectory.tsx`, `DoctorProfile.tsx`

---

## E3. Đặt lịch & theo dõi (bệnh nhân)

### US-11 — Gửi yêu cầu đặt lịch ngay trong chat
**Là** bệnh nhân (khách hoặc đã đăng nhập), **tôi muốn** gửi yêu cầu đặt lịch ngay sau khi được tư vấn, **để** không phải nhập lại thông tin ở chỗ khác.

- **Given** trợ lý đã gợi ý chuyên khoa và phiên không phải cấp cứu
  **When** tôi điền họ tên, số điện thoại Việt Nam hợp lệ, ngày sinh, ngày khám mong muốn và **đồng ý cho điều phối viên liên hệ**
  **Then** hệ thống tạo **ca điều phối** trong hàng đợi của điều phối viên và trả về mã yêu cầu; thông báo rõ đây **chưa phải** lịch đã xác nhận.
- **Given** tôi không tick đồng ý liên hệ
  **Then** yêu cầu bị từ chối (422).
- **Given** ngày khám mong muốn ở quá khứ hoặc xa hơn **90 ngày** tới
  **Then** yêu cầu bị từ chối (422) kèm thông báo lý do.

_Code:_ `POST /booking-requests` (`routes.py`) → `intake()` trong `src/services/workbench.py`

### US-12 — Đặt lịch hộ người dưới 18 tuổi
**Là** người giám hộ, **tôi muốn** đặt lịch cho con/em dưới 18 tuổi, **để** con được khám đúng quy định.

- **Given** ngày sinh của người khám cho thấy dưới 18 tuổi
  **When** tôi gửi yêu cầu đặt lịch
  **Then** hệ thống bắt buộc có họ tên và số điện thoại hợp lệ của người giám hộ; thiếu thì từ chối.

_Code:_ `_is_minor`, kiểm tra người giám hộ trong `booking_request_service.py` / `workbench.intake`

### US-13 — Đặt lịch trực tiếp theo khung giờ trống
**Là** bệnh nhân đã đăng nhập, **tôi muốn** chọn chuyên khoa, bác sĩ, khung giờ còn trống và đặt lịch, **để** chủ động thời gian khám.

- **Given** tôi chọn một khung giờ còn trống
  **When** hệ thống giữ chỗ tạm (`POST /bookings/hold`) rồi tôi xác nhận đặt (`POST /bookings`)
  **Then** lịch được tạo với trạng thái `pending_approval` (chờ điều phối viên duyệt).
- **Given** khung giờ đã hết chỗ
  **Then** tôi không đặt được và được báo lỗi.
- **Given** tôi giữ chỗ nhưng không hoàn tất
  **Then** chỗ giữ tự hết hạn và được trả lại.

_Code:_ `src/api/endpoints/booking.py`, `src/services/booking.py`, `frontend/src/pages/AppointmentBooking.tsx`

### US-14 — Theo dõi tiến trình lịch hẹn
**Là** bệnh nhân, **tôi muốn** xem lịch hẹn của mình đang ở bước nào (chờ duyệt, đã xác nhận, bị từ chối, hết hạn), **để** biết khi nào cần làm gì tiếp.

- **Given** tôi đã có lịch hẹn hoặc yêu cầu đặt lịch
  **When** tôi mở trang Tiến trình / Lịch sử
  **Then** tôi thấy từng lịch với trạng thái hiện tại và chi tiết khi bấm vào.

_Code:_ `GET /bookings`, `/bookings/{id}`, `/coordination/live/mine`; `AppointmentProgress.tsx`, `AppointmentHistory.tsx`, `AppointmentDetail.tsx`

### US-15 — Hủy hoặc đổi lịch
**Là** bệnh nhân, **tôi muốn** hủy hoặc đổi lịch hẹn, **để** nhường chỗ cho người khác khi tôi bận.

- **Given** lịch của tôi chưa bị hủy và chưa bị từ chối
  **When** tôi hủy
  **Then** lịch chuyển sang `cancelled` (không bị xóa, giữ lại để đối soát).
- **Given** lịch đã hủy hoặc bị từ chối
  **When** tôi hủy hoặc đổi lịch
  **Then** hệ thống từ chối (409).
- **Given** lịch đặt theo "thời gian mong muốn" (không gắn khung giờ cụ thể)
  **When** tôi đổi lịch
  **Then** hệ thống chưa hỗ trợ và báo lỗi (409).

_Code:_ `POST /bookings/{id}/cancel`, `/bookings/{id}/reschedule`

### US-16 — Nhận thông báo về lịch hẹn
**Là** bệnh nhân, **tôi muốn** được thông báo khi lịch chờ duyệt, được xác nhận, bị từ chối, hết hạn, cần đặt cọc, và được nhắc trước ngày khám, **để** không bỏ lỡ lịch.

- **Given** trạng thái lịch của tôi thay đổi
  **When** sự kiện xảy ra
  **Then** tôi có thông báo tương ứng trong chuông thông báo (`booking_pending_approval`, `booking_confirmed`, `booking_rejected`, `booking_expired`, `deposit_requested`, `appointment_reminder`).
- **Given** có thông báo chưa đọc
  **When** tôi bấm "đọc" hoặc "đọc tất cả"
  **Then** thông báo được đánh dấu đã đọc.

_Code:_ `src/services/notification.py`, `GET /notifications`, `/notifications/{id}/read`, `/notifications/read-all`; nhắc lịch do tác vụ nền trong `src/main.py`

### US-17 — Yêu cầu gặp người thật
**Là** bệnh nhân, **tôi muốn** yêu cầu được nói chuyện với nhân viên khi trợ lý không giải quyết được, **để** được hỗ trợ trực tiếp.

- **Given** tôi đang có phiên chat chưa đóng
  **When** tôi yêu cầu gặp người thật
  **Then** ca của tôi được đưa vào hàng đợi để điều phối viên nhận xử lý.

_Code:_ `POST /coordination/live/{session_id}/request-human` (`src/api/endpoints/workbench.py`)

---

## E4. Tài khoản & hồ sơ

### US-18 — Đăng ký, đăng nhập, quên mật khẩu
**Là** bệnh nhân, **tôi muốn** tạo tài khoản và đăng nhập an toàn, **để** hệ thống nhớ lịch hẹn và lịch sử của tôi.

- **Given** tôi đăng ký và xác minh OTP
  **When** tôi đăng nhập đúng thông tin
  **Then** tôi vào được trang bệnh nhân; phiên đăng nhập được giữ khi tải lại trang.
- **Given** tôi quên mật khẩu
  **When** tôi xin OTP và đặt lại mật khẩu
  **Then** tôi đăng nhập được bằng mật khẩu mới.
- **Given** tôi đăng xuất
  **Then** phiên đăng nhập bị hủy.

_Code:_ `src/api/endpoints/auth.py` (`/auth/register`, `/otp/*`, `/login`, `/refresh-token`, `/logout`, `/forgot-password`, `/reset-password`)

### US-19 — Hồ sơ sức khỏe & hồ sơ người thân
**Là** bệnh nhân, **tôi muốn** lưu hồ sơ sức khỏe của mình và tạo hồ sơ cho người thân, **để** đặt lịch nhanh và trợ lý tư vấn sát hơn.

- **Given** tôi đã đăng nhập
  **When** tôi cập nhật hồ sơ (thông tin cá nhân, tiền sử, ảnh đại diện) hoặc thêm/sửa/xóa hồ sơ người thân
  **Then** thông tin được lưu và dùng được khi đặt lịch.

_Code:_ `/users/me`, `/users/me/portrait`, `/patient-profiles`; `PatientProfile`, `FamilyProfiles`

### US-20 — Lịch sử hội thoại
**Là** bệnh nhân đã đăng nhập, **tôi muốn** xem lại và xóa các cuộc trò chuyện cũ, **để** tiếp tục tư vấn mà không phải kể lại từ đầu.

- **Given** tôi đã đăng nhập và có hội thoại trước đó
  **When** tôi mở lịch sử
  **Then** tôi thấy danh sách hội thoại, mở lại được từng hội thoại và trợ lý nhớ ngữ cảnh cũ.
- **When** tôi xóa một hội thoại
  **Then** hội thoại đó không còn trong danh sách.

_Code:_ `GET/DELETE /chat/conversations/{session_id}`, `src/services/chat_history.py`

---

## E5. Điều phối (điều phối viên)

### US-21 — Hàng đợi ca điều phối
**Là** điều phối viên, **tôi muốn** thấy tất cả ca cần xử lý (yêu cầu đặt lịch từ chat, yêu cầu gặp người thật, ca cấp cứu), **để** không bỏ sót bệnh nhân nào.

- **Given** tôi là điều phối viên được giới hạn ở một số cơ sở
  **When** tôi mở hàng đợi
  **Then** tôi chỉ thấy ca thuộc cơ sở của mình (hoặc ca chưa gắn cơ sở).
- **Given** có ca cấp cứu
  **Then** ca đó được ưu tiên cao nhất.

_Code:_ `GET /staff/workbench/cases`, `scope()` trong `src/services/workbench.py`; trang `/staff/queue`, `/staff/emergency`

### US-22 — Nhận ca và phân công
**Là** điều phối viên, **tôi muốn** nhận một ca để xử lý, **để** hai người không cùng gọi một bệnh nhân.

- **Given** ca chưa có người phụ trách và chưa đóng
  **When** tôi bấm nhận ca (claim)
  **Then** ca được gán cho tôi, chuyển sang `contacting` (hoặc `emergency_active` nếu là ca cấp cứu) và tôi được ghi nhận đang trực.
- **Given** ca đã có người khác nhận
  **When** tôi bấm nhận
  **Then** hệ thống báo "Ca đã có người phụ trách" (409).
- **Given** hai người sửa cùng một ca
  **Then** hệ thống dùng `version` để chặn ghi đè lên nhau.

_Code:_ `POST /staff/workbench/cases/{id}/actions` (`claim`, `decline`, `handover`, `takeover`, `resume`, `contact`, `follow_up`, `complete`, `cancel`, `reopen`), `bulk-actions`

### US-23 — Xem bối cảnh AI của ca
**Là** điều phối viên, **tôi muốn** xem tóm tắt cuộc trò chuyện, triệu chứng, chuyên khoa AI gợi ý và mức ưu tiên, **để** liên hệ bệnh nhân mà không phải hỏi lại từ đầu.

- **Given** tôi mở chi tiết một ca
  **Then** tôi thấy thông tin bệnh nhân, ảnh chụp kết quả AI (`ai_snapshot`) và lịch sử sự kiện của ca.

_Code:_ `GET /staff/workbench/cases/{id}`, `detail()`, `snapshot()`

### US-24 — Tiếp quản cuộc trò chuyện
**Là** điều phối viên, **tôi muốn** tiếp quản phiên chat đang do AI xử lý và nhắn trực tiếp với bệnh nhân, **để** xử lý ca phức tạp.

- **Given** tôi phụ trách ca
  **When** tôi tiếp quản (takeover)
  **Then** tin nhắn của bệnh nhân đến tôi thay vì AI; tôi gửi tin nhắn cho bệnh nhân được.
- **When** tôi trả quyền lại (resume)
  **Then** AI tiếp tục xử lý phiên.

_Code:_ action `takeover` / `resume`, `POST /staff/workbench/cases/{id}/messages`, `/staff/chat-takeover/*`

### US-25 — Lên phương án khám
**Là** điều phối viên, **tôi muốn** chọn chuyên khoa, dịch vụ, khung giờ cụ thể cho ca và ghi nhận bệnh nhân đã đồng ý, **để** chuẩn bị chốt lịch.

- **Given** tôi phụ trách ca
  **When** tôi lưu phương án (plan) với khung giờ hợp lệ thuộc phạm vi cơ sở của tôi
  **Then** ca chuyển sang trạng thái đã lên phương án; khung giờ không hợp lệ hoặc ngoài cơ sở thì bị từ chối.

_Code:_ `PUT /staff/workbench/cases/{id}/plan`, `validate_plan()`, `set_plan()`

### US-26 — Yêu cầu và xác minh đặt cọc
**Là** điều phối viên, **tôi muốn** yêu cầu bệnh nhân đặt cọc và xác minh khi đã nhận, **để** giảm tình trạng đặt rồi không đến.

- **Given** ca đã có phương án và bệnh nhân đã đồng ý, quản trị đã cấu hình điều khoản cọc
  **When** tôi tạo yêu cầu cọc
  **Then** bệnh nhân nhận thông báo `deposit_requested` kèm hướng dẫn thanh toán.
- **Given** chưa cấu hình điều khoản cọc
  **Then** hệ thống báo cần quản trị cấu hình trước (409).
- **When** tôi xác minh đã nhận cọc
  **Then** cọc chuyển sang `verified`; cọc quá hạn tự hết hiệu lực.

_Code:_ `POST /staff/workbench/cases/{id}/deposits`, `/verify-deposit`; `request_deposit()`, `verify_deposit()`, `expire_deposits()`

### US-27 — Chốt lịch (HITL)
**Là** điều phối viên, **tôi muốn** chốt lịch chính thức sau khi mọi điều kiện đã đủ, **để** đảm bảo **không có lịch nào được xác nhận mà không qua người thật**.

- **Given** ca đã có cọc được xác minh và khung giờ vẫn hợp lệ
  **When** tôi bấm chốt lịch
  **Then** lịch hẹn được tạo/xác nhận và bệnh nhân được thông báo.
- **Given** chưa có cọc được xác minh
  **Then** hệ thống từ chối: "Cần xác minh cọc trước khi chốt lịch" (409).

_Code:_ `POST /staff/workbench/cases/{id}/confirm`, `confirm()`

### US-28 — Duyệt lịch đặt trực tiếp
**Là** điều phối viên, **tôi muốn** duyệt hoặc từ chối các lịch bệnh nhân tự đặt trên web, **để** kiểm soát lịch trước khi xác nhận.

- **Given** lịch ở trạng thái `pending_approval`
  **When** tôi chọn xác nhận hoặc từ chối (kèm ghi chú)
  **Then** lịch chuyển sang `confirmed` hoặc `rejected` và bệnh nhân nhận thông báo.
- **Given** lịch quá hạn duyệt
  **Then** tác vụ nền tự chuyển sang `expired`.

_Code:_ `GET /staff/bookings`, `PATCH /staff/bookings/{id}/status`; trang `/staff/booking-approvals`

### US-28b — Ca trực và bàn giao
**Là** điều phối viên, **tôi muốn** bắt đầu ca trực, kết thúc và bàn giao ca cho người khác, **để** hàng đợi luôn có người phụ trách.

- **When** tôi bắt đầu hoặc kết thúc ca trực
  **Then** trạng thái trực của tôi được cập nhật.
- **Given** tôi đang giữ các ca chưa đóng
  **When** tôi bàn giao cho một đồng nghiệp khác, kèm ghi chú bàn giao
  **Then** toàn bộ ca chưa đóng (`completed`/`cancelled` không tính) của tôi được chuyển cho người nhận.
- **Given** tôi bàn giao cho chính mình hoặc để trống ghi chú
  **Then** hệ thống từ chối.

_Code:_ `POST /staff/workbench/duty/start`, `/duty/end`, `/duty/handover`

---

## E6. Quản trị

### US-29 — Quản lý danh mục
**Là** quản trị, **tôi muốn** thêm/sửa chuyên khoa, dịch vụ, cơ sở, bác sĩ và bật/tắt nhận lịch của bác sĩ, **để** trợ lý chỉ gợi ý dữ liệu đúng và có thật.

- **Given** tôi là quản trị
  **When** tôi tạo hoặc sửa một mục danh mục
  **Then** thay đổi được lưu và ghi nhật ký kiểm toán.
- **Given** tôi là điều phối viên thường (không phải quản trị)
  **When** tôi mở trang quản lý bác sĩ / dịch vụ
  **Then** tôi bị chuyển về hàng đợi.

_Code:_ `/staff/doctors`, `/staff/services`, `/staff/specialties`, `/staff/facilities`; `StaffAdminGate.tsx`

### US-30 — Quản lý lịch làm việc bác sĩ
**Là** điều phối viên/quản trị, **tôi muốn** tạo, sửa, hủy, nhập hàng loạt lịch làm việc của bác sĩ, **để** bệnh nhân thấy đúng khung giờ trống.

- **When** tôi tạo lịch trùng giờ với lịch đã có của cùng bác sĩ
  **Then** hệ thống chặn.
- **When** tôi nhập file lịch hàng loạt
  **Then** hệ thống báo kết quả từng dòng (thành công / lỗi).

_Code:_ `/staff/schedules`, `/staff/schedules/import`, `/staff/schedule-activity`; trang `/staff/doctor-schedule`

### US-31 — Cấu hình chính sách điều phối & thành viên
**Là** quản trị, **tôi muốn** cấu hình thời gian giữ chỗ, thời gian phản hồi, hướng dẫn thanh toán, chính sách hoàn cọc và phân quyền thành viên theo cơ sở, **để** quy trình điều phối thống nhất.

- **Given** tôi là quản trị
  **When** tôi cập nhật chính sách (`hold_minutes`, `response_minutes`, `emergency_response_minutes`, hướng dẫn thanh toán, chính sách hoàn tiền) hoặc danh sách thành viên
  **Then** cấu hình mới được áp dụng cho các ca sau đó.

_Code:_ `PUT /staff/workbench/policy`, `PUT /staff/workbench/members`; trang `/staff/settings`

### US-32 — Theo dõi tổng quan
**Là** quản trị/điều phối viên, **tôi muốn** xem số liệu tổng quan (ca theo trạng thái, lịch hẹn, bệnh nhân), **để** nắm tình hình vận hành.

- **When** tôi mở trang tổng quan
  **Then** tôi thấy số liệu lấy từ dữ liệu thật của hệ thống.

_Code:_ `/staff/dashboard/summary`, `/staff/workbench/dashboard`, `/staff/patients`; trang `/staff/overview`, `/staff/patients`

---

## E7. Kênh Zalo

### US-33 — Tư vấn qua Zalo
**Là** bệnh nhân dùng Zalo, **tôi muốn** nhắn tin triệu chứng cho Zalo Bot, **để** được tư vấn mà không cần mở web.

- **Given** Zalo Bot đã được cấu hình
  **When** tôi nhắn tin
  **Then** tin nhắn được xử lý bởi cùng trợ lý AI như trên web; câu trả lời dài được tự chia thành nhiều tin, mỗi tin tối đa 1800 ký tự (dưới giới hạn 2000 ký tự của Zalo), ưu tiên cắt ở cuối câu hoặc xuống dòng.

_Code:_ `src/zalo/service.py` (`_handle_agent_chat_turn`), `split_message_chunks` trong `src/zalo/client.py`, `POST /zalo/webhook`

### US-34 — Tra cứu lịch hẹn qua Zalo
**Là** bệnh nhân dùng Zalo, **tôi muốn** hỏi bot về lịch hẹn của mình, **để** biết lịch đã được xác nhận hay chưa.

- **Given** tài khoản Zalo của tôi liên kết được với tài khoản web (qua số điện thoại)
  **When** tôi hỏi lịch hẹn của mình
  **Then** bot trả về các lịch hẹn và ca điều phối gần nhất của tôi.

_Code:_ `_handle_my_bookings` trong `src/zalo/service.py`

---

## Ngoài phạm vi (chưa có trong code)

Các mục dưới đây **không** viết thành story vì code chưa thực hiện:

- Thông báo đẩy qua Zalo khi lịch được duyệt (hàm `send_zalo_notification_to_user` có nhưng chưa được gọi).
- Tự động điều xe/gửi dữ liệu cho cấp cứu 115 (trang `EmergencyCoordinator` chỉ là giao diện mẫu, không có đường dẫn và không có backend).
- Bác sĩ đăng nhập và tự quản lý lịch.
- Thanh toán cọc trực tuyến (hiện điều phối viên xác minh cọc thủ công).
