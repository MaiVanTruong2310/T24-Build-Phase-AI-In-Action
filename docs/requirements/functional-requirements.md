# Yêu cầu chức năng (Functional Requirements) — VCare+ (P-124)

> Mô tả **hệ thống phải làm gì**, viết theo dạng "Hệ thống phải…". Căn cứ: đề bài VMEC-01 và code nhánh `develop` (commit `42c909e`, 10/10/2026).
>
> - **Ưu tiên:** `Bắt buộc` = đề bài yêu cầu hoặc ràng buộc an toàn; `Nên có` = yêu cầu nâng cao của đề; `Bổ sung` = nhóm tự thêm.
> - **Trạng thái:** lấy từ [story-status.md](story-status.md): ✅ Xong · 🟡 Một phần.
> - **Story:** liên kết tới [user-stories.md](user-stories.md).
> - Một story thường gồm nhiều FR. Vì vậy một FR có thể ✅ trong khi story của nó 🟡, vì story bị 🟡 do một FR khác. Ví dụ FR-14 (RAG) ✅ nhưng US-08 🟡 do FR-12 (thứ tự chuyên khoa).

## Danh sách module

| Module | Mã | Số yêu cầu |
|---|---|---|
| 1. Xác thực & phân quyền | FR-01 → FR-07 | 7 |
| 2. Chat AI | FR-08 → FR-16 | 9 |
| 3. Cấp cứu & an toàn lâm sàng | FR-17 → FR-22 | 6 |
| 4. Đặt lịch | FR-23 → FR-31 | 9 |
| 5. Điều phối (HITL) | FR-32 → FR-41 | 10 |
| 6. Thông báo | FR-42 → FR-45 | 4 |
| 7. Zalo | FR-46 → FR-48 | 3 |
| 8. Danh mục, lịch bác sĩ & quản trị | FR-49 → FR-54 | 6 |

---

## 1. Xác thực & phân quyền

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-01 | Hệ thống phải cho phép bệnh nhân đăng ký tài khoản bằng email và kích hoạt bằng mã xác nhận gửi qua email (Supabase Auth). | Bắt buộc | US-18 | ✅ |
| FR-02 | Hệ thống phải cho phép đăng nhập, cấp access token + refresh token, giữ phiên khi tải lại trang (qua cookie hoặc header `Bearer`). | Bắt buộc | US-18 | ✅ |
| FR-03 | Hệ thống phải cho phép đặt lại mật khẩu qua OTP và đổi mật khẩu khi đã đăng nhập. | Bắt buộc | US-18 | ✅ |
| FR-04 | Hệ thống phải phân biệt tối thiểu 2 vai trò: **bệnh nhân** (`patient`) và **nhân viên điều phối** (`staff`). Mọi API `/staff/*` phải từ chối người không phải staff. | Bắt buộc | US-21, US-29 | ✅ |
| FR-05 | Hệ thống phải giới hạn điều phối viên chỉ thấy và xử lý ca thuộc các cơ sở được phân công (`facility_ids`). | Nên có | US-21 | ✅ |
| FR-06 | Hệ thống phải dành riêng các chức năng cấu hình (chính sách điều phối, thành viên, danh mục, gói khám) cho **quản trị điều phối** (staff có `is_admin`, không giới hạn cơ sở). | Nên có | US-29, US-31 | ✅ |
| FR-07 | Hệ thống phải chặn các request ghi dữ liệu dùng cookie nếu `Origin` không nằm trong danh sách cho phép. | Bổ sung | — | ✅ |

## 2. Chat AI

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-08 | Hệ thống phải cho phép trò chuyện với trợ lý bằng ngôn ngữ tự nhiên, cả khi **chưa đăng nhập** (khai họ tên + số điện thoại). | Bắt buộc | US-01 | ✅ |
| FR-09 | Hệ thống phải trả lời dạng streaming (SSE) với các sự kiện: khởi tạo → nội dung → metadata (chuyên khoa, mức ATS, gợi ý trả lời nhanh) → kết thúc. | Nên có | US-02 | ✅ |
| FR-10 | Hệ thống phải hỏi làm rõ nhu cầu/triệu chứng **từng câu một** trước khi gợi ý chuyên khoa và không hỏi lại thông tin đã có. | Bắt buộc | US-06 | ✅ |
| FR-11 | Hệ thống phải hiểu câu phủ định (ví dụ "không sốt") và không coi đó là triệu chứng. | Bắt buộc | US-06 | ✅ |
| FR-12 | Hệ thống phải gợi ý chuyên khoa phù hợp, **chỉ dùng chuyên khoa có trong danh mục** của hệ thống (không bịa tên khoa/bác sĩ). | Bắt buộc | US-08 | 🟡 Thứ tự khoa chính khi đa triệu chứng chưa ổn định |
| FR-13 | Hệ thống phải gợi ý cơ sở khám theo khu vực bệnh nhân nêu. | Nên có | US-09 | ✅ |
| FR-14 | Hệ thống phải truy xuất tri thức về khoa/dịch vụ (RAG: ChromaDB + SQLite FTS) và trích nguồn khi trả lời thông tin danh mục. | Bắt buộc | US-08 | ✅ |
| FR-15 | Hệ thống phải hỗ trợ tiếng Việt và tiếng Anh, tự trả lời theo ngôn ngữ của bệnh nhân. | Bổ sung | US-05 | ✅ |
| FR-16 | Hệ thống phải lưu lịch sử hội thoại của bệnh nhân đã đăng nhập, cho phép xem lại, xóa, và khôi phục ngữ cảnh khi tiếp tục (kể cả sau khi server khởi động lại). | Nên có | US-20 | ✅ |

## 3. Cấp cứu & an toàn lâm sàng

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-17 | Hệ thống phải phát hiện dấu hiệu cấp cứu (đau ngực dữ dội, khó thở, dấu hiệu đột quỵ, co giật, ý định tự tử…) bằng luật, **trước khi gọi LLM**. | Bắt buộc | US-03 | ✅ |
| FR-18 | Khi phát hiện cấp cứu, hệ thống phải hướng dẫn gọi **115** hoặc đến cơ sở cấp cứu gần nhất, và **không** đề xuất đặt lịch thường. Yêu cầu đặt lịch cho phiên cấp cứu phải bị từ chối. | Bắt buộc | US-03 | 🟡 Nhãn bệnh hiển thị còn sai ở một số ca |
| FR-19 | Hệ thống phải phân mức khẩn cấp theo thang ATS (1–5) và dùng mức này để giới hạn thời gian đặt lịch. | Nên có | US-03 | ✅ |
| FR-20 | Hệ thống **không được** chẩn đoán bệnh hay kê đơn thuốc; khi bị yêu cầu phải từ chối, giải thích và hướng tới chuyên khoa phù hợp. | Bắt buộc | US-04 | ✅ |
| FR-21 | Mọi câu trả lời phải kèm khuyến cáo "thông tin chỉ mang tính tham khảo, vui lòng gặp bác sĩ để được tư vấn chính xác". | Bắt buộc | US-05 | 🟡 Chỉ gắn khi có ngữ cảnh lâm sàng (xem RB-03) |
| FR-22 | Hệ thống phải chặn nội dung tấn công (prompt injection, jailbreak, yêu cầu lộ system prompt) và che thông tin cá nhân (PII/PHI) của người khác trong câu trả lời. | Bắt buộc | US-07 | 🟡 Chỉ che ở câu trả lời đầu ra; tin nhắn bệnh nhân vẫn gửi nguyên văn cho LLM |

## 4. Đặt lịch

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-23 | Hệ thống phải cho phép gửi yêu cầu đặt lịch ngay trong chat, gồm họ tên, số điện thoại Việt Nam, ngày sinh, ngày khám mong muốn và **đồng ý cho điều phối viên liên hệ**. | Bắt buộc | US-11 | ✅ |
| FR-24 | Yêu cầu đặt lịch từ chat phải tạo **ca điều phối** trong hàng đợi của điều phối viên và thông báo rõ đây **chưa phải** lịch đã xác nhận. | Bắt buộc | US-11 | ✅ |
| FR-25 | Ngày khám mong muốn phải nằm trong khoảng từ hôm nay đến 90 ngày tới (giờ Việt Nam). | Bổ sung | US-11 | ✅ |
| FR-26 | Với người khám dưới 18 tuổi, hệ thống phải bắt buộc có họ tên và số điện thoại người giám hộ. | Bổ sung | US-12 | ✅ |
| FR-27 | Hệ thống phải cho bệnh nhân đã đăng nhập tra lịch trống của bác sĩ và **giữ chỗ tạm** trước khi xác nhận đặt; chỗ giữ phải tự hết hạn nếu không hoàn tất. | Bắt buộc | US-13 | ✅ |
| FR-28 | Lịch đặt trực tiếp phải ở trạng thái `pending_approval` cho tới khi nhân viên duyệt; chuyển sang `expired` nếu quá hạn duyệt. | Bắt buộc | US-13, US-28 | ✅ |
| FR-29 | Hệ thống phải ngăn đặt quá sức chứa của khung giờ và xử lý an toàn khi nhiều người đặt cùng lúc. | Nên có | US-13 | ✅ |
| FR-30 | Hệ thống phải cho bệnh nhân hủy lịch (lưu trạng thái `cancelled`, không xóa dữ liệu) và đổi sang khung giờ khác. | Nên có | US-15 | 🟡 Chưa đổi được lịch loại "thời gian mong muốn" |
| FR-31 | Hệ thống phải cho bệnh nhân xem danh sách và tiến trình các lịch hẹn, yêu cầu của mình. | Bắt buộc | US-14 | ✅ |

## 5. Điều phối (Human-in-the-loop)

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-32 | Hệ thống phải hiển thị hàng đợi ca điều phối (yêu cầu đặt lịch, yêu cầu gặp người thật, ca cấp cứu), trong đó ca cấp cứu được ưu tiên cao nhất. | Bắt buộc | US-21 | ✅ |
| FR-33 | Hệ thống phải cho bệnh nhân yêu cầu chuyển sang người thật trong phiên chat. | Nên có | US-17 | ✅ |
| FR-34 | Hệ thống phải cho điều phối viên nhận ca; mỗi ca chỉ có một người phụ trách; dùng `version` để chặn hai người ghi đè lên nhau. | Bắt buộc | US-22 | ✅ |
| FR-35 | Hệ thống phải hỗ trợ các thao tác trên ca: nhận, từ chối, bàn giao, tiếp quản, trả lại AI, liên hệ, hẹn theo dõi, hoàn tất, hủy, mở lại (kể cả thao tác hàng loạt nhận/từ chối). | Nên có | US-22 | ✅ |
| FR-36 | Hệ thống phải hiển thị cho điều phối viên bối cảnh AI của ca: tóm tắt hội thoại, triệu chứng, chuyên khoa gợi ý, mức ưu tiên, lịch sử sự kiện. | Bắt buộc | US-23 | ✅ |
| FR-37 | Hệ thống phải cho điều phối viên tiếp quản phiên chat và nhắn trực tiếp với bệnh nhân, sau đó trả quyền lại cho AI. | Nên có | US-24 | ✅ |
| FR-38 | Hệ thống phải cho điều phối viên lập phương án khám (chuyên khoa, dịch vụ, khung giờ) và kiểm tra khung giờ còn hợp lệ, thuộc phạm vi cơ sở. | Bắt buộc | US-25 | ✅ |
| FR-39 | Hệ thống phải hỗ trợ yêu cầu đặt cọc theo chính sách do quản trị cấu hình, xác minh cọc và tự hết hạn cọc quá thời gian. | Bổ sung | US-26 | ✅ |
| FR-40 | **Không có lịch nào được xác nhận mà không qua người thật**: điều phối viên phải duyệt lịch đặt trực tiếp, và chỉ chốt được lịch từ ca điều phối khi đã có cọc được xác minh. | Bắt buộc | US-27, US-28 | ✅ |
| FR-41 | Hệ thống phải cho điều phối viên bắt đầu/kết thúc ca trực và bàn giao toàn bộ ca chưa đóng cho đồng nghiệp (bắt buộc có ghi chú). | Nên có | US-28b | ✅ |

## 6. Thông báo

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-42 | Hệ thống phải tạo thông báo trong ứng dụng khi lịch chờ duyệt, được xác nhận, bị từ chối, hết hạn, và khi cần đặt cọc. | Nên có | US-16 | ✅ |
| FR-43 | Hệ thống phải tự động nhắc lịch trước ngày khám (tác vụ nền định kỳ). | Nên có | US-16 | ✅ |
| FR-44 | Hệ thống phải cho bệnh nhân xem danh sách thông báo, đánh dấu đã đọc từng cái hoặc tất cả. | Nên có | US-16 | ✅ |
| FR-45 | Hệ thống phải đẩy thông báo thời gian thực cho điều phối viên khi có ca chat cần tiếp quản (WebSocket). | Bổ sung | US-24 | ✅ |

## 7. Zalo

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-46 | Hệ thống phải nhận tin nhắn từ Zalo Bot (webhook hoặc polling) và trả lời bằng cùng trợ lý AI như trên web. | Bổ sung | US-33 | ✅ |
| FR-47 | Hệ thống phải chia câu trả lời dài thành nhiều tin, mỗi tin tối đa 1800 ký tự (dưới giới hạn 2000 của Zalo). | Bổ sung | US-33 | ✅ |
| FR-48 | Hệ thống phải liên kết người dùng Zalo với tài khoản web theo số điện thoại và cho tra cứu lịch hẹn của mình. | Bổ sung | US-34 | ✅ |

## 8. Danh mục, lịch bác sĩ & quản trị

| Mã | Yêu cầu | Ưu tiên | Story | Trạng thái |
|---|---|---|---|---|
| FR-49 | Hệ thống phải cho tra cứu bác sĩ theo chuyên khoa, cơ sở và xem hồ sơ chi tiết. | Nên có | US-10 | ✅ |
| FR-50 | Hệ thống phải cho quản trị thêm/sửa chuyên khoa, dịch vụ, cơ sở, bác sĩ, bật/tắt nhận lịch của bác sĩ, và ghi nhật ký thay đổi. | Bắt buộc | US-29 | ✅ |
| FR-51 | Hệ thống phải cho nhân viên tạo, sửa, hủy, nhập hàng loạt lịch làm việc bác sĩ, và chặn lịch trùng giờ. | Bắt buộc | US-30 | ✅ |
| FR-52 | Hệ thống phải cho quản trị cấu hình chính sách điều phối: thời gian giữ chỗ, thời gian phản hồi (thường/cấp cứu), hướng dẫn thanh toán, chính sách hoàn cọc. | Nên có | US-31 | ✅ |
| FR-53 | Hệ thống phải cho bệnh nhân quản lý hồ sơ sức khỏe của mình và hồ sơ người thân để đặt lịch hộ. | Nên có | US-19 | ✅ |
| FR-54 | Hệ thống phải hiển thị số liệu tổng quan vận hành và danh sách bệnh nhân cho nhân viên. | Nên có | US-32 | ✅ |

---

## Đối chiếu với yêu cầu đề bài VMEC-01

| Yêu cầu đề bài | Đáp ứng bởi |
|---|---|
| Đăng nhập ≥ 2 vai trò (bệnh nhân, lễ tân/điều phối) | FR-01 → FR-06 |
| Agent gợi ý chuyên khoa, tra lịch trống, đặt lịch có bệnh nhân xác nhận | FR-08 → FR-12, FR-23, FR-27 |
| HITL bắt buộc: lễ tân/điều phối duyệt trước khi chốt | FR-28, FR-32 → FR-40 |
| Phát hiện cấp cứu → 115 thay vì đặt lịch | FR-17, FR-18 |
| Không chẩn đoán, luôn có khuyến cáo | FR-20, FR-21 |
| RAG có trích nguồn danh mục khoa, không bịa tên | FR-12, FR-14 |
| Bảo mật PII/PHI, phân quyền theo vai trò | FR-04 → FR-07, FR-22 |
| *(Nâng cao)* Memory hồ sơ, cá nhân hóa | FR-16, FR-53 |
| *(Nâng cao)* Xử lý xung đột lịch, khung giờ thay thế | FR-29, FR-38 |
| *(Nâng cao)* Nhắc lịch tự động | FR-42, FR-43 |
| *(Nâng cao)* Dashboard điều phối | FR-32, FR-54 |
| *(Nâng cao)* Chuyển người thật khi AI không đủ tự tin | FR-33, FR-37 |

**Tổng: 54 yêu cầu, 49 ✅, 5 🟡** (FR-12, FR-18, FR-21, FR-22, FR-30).

---

## Ràng buộc bắt buộc

Đề bài VMEC-01 đặt ra 6 ràng buộc bắt buộc. Bảng dưới chỉ ra **dòng code đang thực thi** từng ràng buộc và mức đáp ứng hiện tại (develop `42c909e`).

### RB-01. Human-in-the-loop: không lịch nào được chốt mà không qua người thật

> _Đề:_ "HITL BẮT BUỘC… mọi đặt lịch phải có bệnh nhân xác nhận và/hoặc lễ tân/điều phối duyệt trước khi chốt."

| Điểm kiểm soát | Code thực thi |
|---|---|
| Yêu cầu đặt lịch từ chat bắt buộc bệnh nhân **đồng ý cho điều phối viên liên hệ**, thiếu thì trả 422 | `src/medical_assistant/api/routes.py:360-361` |
| Yêu cầu từ chat chỉ tạo **ca điều phối**, không tạo lịch hẹn | `intake()` trong `src/services/workbench.py:253` |
| Phương án khám chỉ được lưu khi ghi nhận **bệnh nhân đã đồng ý** (`patient_agreed`) | `src/services/workbench.py:891` |
| Chỉ yêu cầu cọc khi phương án đã được bệnh nhân thống nhất | `src/services/workbench.py:931-932` |
| Chỉ **chốt lịch** khi có cọc đã được nhân viên xác minh | `confirm()`, `src/services/workbench.py:1105-1114` |
| Lịch bệnh nhân tự đặt luôn bắt đầu ở `pending_approval` | `src/services/booking.py:384` |
| Chỉ nhân viên (`require_staff`) mới chuyển `pending_approval` → `confirmed`/`rejected` | `src/api/endpoints/booking.py:409`; `review()` `src/services/booking.py:690-707` |

**Mức đáp ứng: ✅ Đạt.**

### RB-02. Không chẩn đoán, không kê đơn

> _Đề:_ "agent chỉ gợi ý chuyên khoa/định hướng, KHÔNG chẩn đoán bệnh."

| Lớp | Code thực thi |
|---|---|
| Lớp 1 (đầu vào): nhận diện câu hỏi đòi kê đơn / đòi chẩn đoán | `check_intent()`, `src/medical_assistant/domain/guardrail_service.py:782-815` |
| Chuyển sang trạng thái guardrail | `src/medical_assistant/agent/nodes/analyze_node.py:1060-1062` |
| Trả lời từ chối + hướng chuyên khoa | `src/medical_assistant/agent/nodes/respond_node.py:400-403` |
| Lớp 2 (đầu ra): lọc mọi câu trả lời có nội dung kê đơn hoặc khẳng định chẩn đoán | `MedicalSafetyValidators` (`src/medical_assistant/domain/security/guardrail_validators.py:24`), gọi tại `respond_node.py:1105-1106` |

**Mức đáp ứng: ✅ Đạt**, nhưng có một điểm cần lưu ý: cảnh báo cấp cứu đang **nêu tên bệnh cụ thể** ("Nghi ngờ Nhồi máu cơ tim cấp", "Dấu hiệu FAST nghi ngờ Đột quỵ") và có nhãn sai ("Hội chứng Sheehan" cho trẻ sốt co giật). Nên đổi sang mô tả nhóm dấu hiệu thay vì tên bệnh.

### RB-03. Luôn hiển thị khuyến cáo y tế

> _Đề:_ "Luôn hiển thị khuyến cáo 'thông tin chỉ mang tính tham khảo, vui lòng gặp bác sĩ để được tư vấn chính xác'."

| Điểm kiểm soát | Code thực thi |
|---|---|
| Nội dung khuyến cáo (Việt/Anh) | `get_medical_disclaimer()`, `src/medical_assistant/domain/language_service.py:345` |
| Gắn khuyến cáo vào câu trả lời | `src/medical_assistant/agent/nodes/respond_node.py:1101` |

**Mức đáp ứng: 🟡 Một phần.** Khuyến cáo chỉ được gắn khi `has_clinical_context` đúng (`respond_node.py:1078`), tức là khi đã có triệu chứng, chuyên khoa, mức ATS hoặc trạng thái lâm sàng. Câu trả lời không lâm sàng (chào hỏi, ngoài phạm vi…) **không có khuyến cáo**, và giao diện chat cũng không có dòng khuyến cáo cố định. Cách sửa đơn giản: thêm một dòng khuyến cáo cố định dưới khung chat, hoặc luôn gắn khuyến cáo ở backend.

### RB-04. Grounded: không bịa tên bác sĩ, khoa, lịch trống

> _Đề:_ "Grounded trên danh mục chuyên khoa/dịch vụ… không bịa tên bác sĩ/khoa không tồn tại."

| Điểm kiểm soát | Code thực thi |
|---|---|
| Danh sách bác sĩ lấy từ dữ liệu hệ thống, kèm link hồ sơ gốc | `src/medical_assistant/agent/nodes/respond_node.py:173`, `:757-776` |
| Chỉ coi là "lịch trống" những khung giờ đã được database xác minh (`verified`); nếu không có thì nói rõ là chưa có lịch xác minh | `respond_node.py:739-777` |
| Tra cứu tri thức qua RAG có trích nguồn | `src/medical_assistant/rag/` |
| Kết quả đo | Hallucination 0% trên 32 thực thể (bác sĩ, cơ sở, SĐT, giá, kinh nghiệm, địa chỉ); grounded 100% (`reports/eval_info.md` §2–3) |

**Mức đáp ứng: ✅ Đạt** (mẫu đo nhỏ, 10 câu).

### RB-05. Cấp cứu → 115, không đặt lịch

> _Đề:_ "Phát hiện dấu hiệu cấp cứu… phải cảnh báo gọi 115/đến cơ sở y tế gần nhất thay vì đặt lịch."

| Điểm kiểm soát | Code thực thi |
|---|---|
| Kiểm tra cấp cứu bằng luật **trước khi gọi LLM** | `src/medical_assistant/agent/nodes/analyze_node.py:72-92`; `evaluate_symptoms()` `triage_service.py:1134` |
| Ca cấp cứu đi thẳng tới bước trả lời, **bỏ qua bước tìm bác sĩ/lịch** | `should_continue()`, `src/medical_assistant/agent/graph.py:58` |
| Nội dung cảnh báo có hướng dẫn gọi 115 | `src/medical_assistant/domain/language_service.py:365-384` |
| Từ chối yêu cầu đặt lịch thường cho phiên cấp cứu (409) | `src/medical_assistant/api/routes.py:378` |
| Nút gọi 115 trên giao diện chat | `frontend/src/layouts/ChatbotWidget.tsx:946` (`tel:115`) |

**Mức đáp ứng: ✅ Đạt**, cụ thể là bắt đúng 6/6 ca thử. Còn 2 vấn đề cần cải thiện:
- Thời gian trả lời cảnh báo là 7,9–14,8 s (NFR-11).
- Nhãn bệnh hiển thị sai ở 2 ca (NFR-07).

### RB-06. Bảo mật PII/PHI: mã hóa, phân quyền theo vai trò

> _Đề:_ "Bảo mật PII/PHI (mã hóa, phân quyền theo vai trò)."

| Điểm kiểm soát | Code thực thi |
|---|---|
| Phân quyền theo vai trò: staff / quản trị | `require_staff` `src/api/dependencies.py:30`; `require_coordination_admin` `:60` |
| Giới hạn điều phối viên theo cơ sở | `scope()` trong `src/services/workbench.py` |
| Mật khẩu băm `scrypt` có salt | `src/core/security.py:24-38` |
| Cookie phiên `HttpOnly`, `Secure` trên production, chống CSRF theo Origin | `src/services/cookie_session.py:29-34`; `CookieOriginMiddleware` |
| Che PII/PHI trong câu trả lời (Presidio + DLP) | `src/medical_assistant/agent/nodes/respond_node.py:1109-1126` |

**Mức đáp ứng: 🟡 Một phần.** Còn thiếu 2 phần:
- **Tin nhắn bệnh nhân được gửi nguyên văn cho nhà cung cấp LLM bên ngoài.** Bước che PII chỉ chạy trên câu trả lời đầu ra, không chạy trên đầu vào.
- **Chưa mã hóa dữ liệu nhạy cảm khi lưu.** Tiền sử bệnh và hồ sơ sức khỏe được lưu dạng thường trong PostgreSQL. Code chưa có mã hóa ở mức cột.

### Tổng hợp ràng buộc

| Ràng buộc | Mức đáp ứng |
|---|---|
| RB-01 Human-in-the-loop | ✅ |
| RB-02 Không chẩn đoán | ✅ (lưu ý tên bệnh trong cảnh báo cấp cứu) |
| RB-03 Luôn có khuyến cáo | 🟡 |
| RB-04 Grounded | ✅ |
| RB-05 Cấp cứu → 115 | ✅ (lưu ý tốc độ và nhãn) |
| RB-06 Bảo mật PII/PHI | 🟡 |
