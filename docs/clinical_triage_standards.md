# HỆ THỐNG PHÂN LOẠI TRIỆU CHỨNG Y KHOA CHUẨN QUỐC TẾ (CLINICAL TRIAGE STANDARDS FOR HEALTHCARE AI AGENT)

**Dự án:** P-124 - AI Agent Trợ Lý Đặt Lịch Khám & Điều Hướng Chuyên Khoa
**Chuẩn tham chiếu:**
- **ESI (Emergency Severity Index - Hoa Kỳ)** do *Agency for Healthcare Research and Quality (AHRQ)* & *Emergency Nurses Association (ENA)* ban hành.
- **MTS (Manchester Triage System - Châu Âu/Anh Quốc)**.
- **Quyết định 3959/QĐ-BYT** của Bộ Y tế Việt Nam về Tiêu chí phân loại cấp cứu tại khoa Cấp cứu bệnh viện.

---

## 1. TỔNG QUAN 5 CẤP ĐỘ TRIỆU CHỨNG (ESI 5-LEVEL MODEL)

Trong y khoa thế giới, hệ thống **ESI (Emergency Severity Index)** là chuẩn phổ biến và khoa học nhất để phân luồng người bệnh theo 5 mức độ từ khẩn cấp đến thông thường:

```
[Level 1: Tối khẩn cấp] ---> [Level 2: Khẩn cấp / Đe dọa tính mạng]
   ===> CHẶN ĐẶT LỊCH NGAY - KÍCH HOẠT MÀN HÌNH 115 / CẤP CỨU
-----------------------------------------------------------------------
[Level 3: Bán khẩn]     ---> [Level 4: Tiêu chuẩn] ---> [Level 5: Không khẩn]
   ===> CHO PHÉP ĐIỀU HƯỚNG CHUYÊN KHOA & ĐẶT LỊCH HẸN
```

---

## 2. MA TRẬN PHÂN LOẠI CHI TIẾT & HÀNH VI CỦA AI AGENT

| Cấp độ (ESI Level) | Tên gọi chuẩn Y khoa | Mô tả lâm sàng & Dấu hiệu nhận diện | Triệu chứng thực tế điển hình | Hành vi của AI Agent (Action & Guardrails) |
| :---: | :---: | :--- | :--- | :--- |
| **CẤP ĐỘ 1 (Level 1)** | **Resuscitation (Hồi sinh cấp cứu)** | Ngừng tuần hoàn, ngừng thở, đe dọa tử vong trong vài giây/phút, cần can thiệp hồi sức tức thì. | - Ngưng tim, ngưng thở, bất tỉnh sâu.<br/>- Đang co giật liên tục không tỉnh.<br/>- Tím tái toàn thân, sốc phản vệ mất mạch. | **BLOCK LUỒNG ĐẶT LỊCH LẬP TỨC.**<br/>Hiển thị pop-up cảnh báo đỏ toàn màn hình:<br/>*"TÌNH TRẠNG NGUY KỊCH! Vui lòng gọi 115 hoặc đưa người bệnh đến khoa Cấp cứu gần nhất ngay bây giờ."* Kèm nút bấm trực tiếp gọi `tel:115`. |
| **CẤP ĐỘ 2 (Level 2)** | **Emergent / High Risk (Khẩn cấp nguy cơ cao)** | Nguy cơ đe dọa tính mạng hoặc tàn phế cao, đau đớn dữ dội, lú lẫn/rối loạn tri giác, không thể chờ đợi. | - Đau ngực dữ dội, bóp nghẹt lan ra tay/cằm (nghi nhồi máu cơ tim).<br/>- Dấu hiệu đột quỵ não FAST (méo miệng, liệt nửa người, khó nói).<br/>- Khó thở cấp, thở rít.<br/>- Nôn ra máu đỏ tươi, đi cầu phân đen như bã cà phê.<br/>- Đau đầu dữ dội đột ngột chưa từng có (Thunderclap headache).<br/>- Bụng gồng cứng như gỗ, đau dữ dội.<br/>- Thai ngoài tử cung (trễ kinh + đau bụng dữ dội + ra máu).<br/>- Sốt cao co giật ở trẻ em, li bì khó đánh thức.<br/>- Uống thuốc trừ sâu/thuốc độc, uống quá liều thuốc ngủ. | **BLOCK LUỒNG ĐẶT LỊCH.**<br/>Agent từ chối đặt lịch ngày hôm sau:<br/>*"Triệu chứng của bạn thuộc nhóm nguy hiểm cần được xử trí y tế ngay lập tức tại phòng Cấp cứu (Emergency Room), không nên chờ đợi lịch khám hẹn trước."*<br/>Cung cấp địa chỉ & hotline cấp cứu của cơ sở bệnh viện gần nhất. |
| **CẤP ĐỘ 3 (Level 3)** | **Urgent (Bán khẩn cấp)** | Người bệnh tỉnh táo, huyết động ổn định nhưng có triệu chứng cấp tính cần được khám và làm nhiều xét nghiệm/chẩn đoán hình ảnh trong ngày. | - Đau bụng âm ỉ tăng dần vùng hố chậu phải (nghi viêm ruột thừa giai đoạn sớm).<br/>- Sốt cao 39-40 độ C liên tục 2 ngày nghi sốt xuất huyết nhưng còn tỉnh táo.<br/>- Chấn thương gãy xương kín, bong gân sưng to, đau nhiều nhưng chi còn hồng ấm.<br/>- Đau quặn thận từng cơn kèm tiểu buốt/tiểu máu. | **CHO PHÉP ĐẶT LỊCH ƯU TIÊN (SAME-DAY BOOKING).**<br/>Agent định hướng chuyên khoa phù hợp (Nội tiêu hóa, Ngoại tổng quát, Cơ xương khớp). Ưu tiên gợi ý các khung giờ khám trống sớm nhất trong ngày hôm nay hoặc sáng sớm mai. |
| **CẤP ĐỘ 4 (Level 4)** | **Semi-urgent / Standard (Tiêu chuẩn)** | Bệnh mạn tính ổn định, triệu chứng nhẹ diễn tiến vài tuần/tháng, chỉ cần 1 xét nghiệm hoặc khám đơn thuần. | - Đau nửa đầu mạn tính tái phát.<br/>- Đau lưng, đau mỏi vai gáy khi ngồi văn phòng.<br/>- Viêm họng nhẹ, ho khan vài ngày không sốt.<br/>- Đau dạ dày âm ỉ sau ăn nhiều tuần.<br/>- Rối loạn kinh nguyệt, mụn trứng cá. | **ĐIỀU HƯỚNG CHUYÊN KHOA BÌNH THƯỜNG.**<br/>Agent tiến hành Triage hỏi thêm 2-3 câu làm rõ, tra cứu RAG đối soát triệu chứng $\rightarrow$ Gợi ý bác sĩ và các slot khám phù hợp trong tuần. |
| **CẤP ĐỘ 5 (Level 5)** | **Non-urgent (Không khẩn cấp)** | Khám sức khỏe định kỳ, tư vấn tiêm chủng, tái khám theo hẹn, đổi đơn thuốc, không có triệu chứng khó chịu. | - Khám sức khỏe tổng quát định kỳ.<br/>- Khám tiền hôn nhân, tầm soát ung thư.<br/>- Đăng ký gói tiêm vắc-xin cho trẻ.<br/>- Xin cấp lại giấy khám sức khỏe lái xe. | **HỖ TRỢ ĐẶT LỊCH & TƯ VẤN GÓI DỊCH VỤ.**<br/>Gợi ý các Gói khám sức khỏe (Check-up Packages) trong bảng `services` và hướng dẫn chuẩn bị giấy tờ/nhịn ăn theo `service_policy`. |

---

## 3. LINK TÀI LIỆU CHÍNH THỨC & THAM KHẢO NGHIÊN CỨU

1. **Emergency Severity Index (ESI) - AHRQ & ENA:**
   - Trang chủ nghiên cứu & ESI Handbook (Bản hướng dẫn chuẩn):
     👉 [AHRQ Emergency Severity Index (ESI) Implementation Handbook](https://www.ahrq.gov/patient-safety/settings/emergency-dept/esi.html)
     👉 [Emergency Nurses Association (ENA) ESI Course & Criteria](https://www.ena.org/education/esi)
   - Nghiên cứu tổng quan trên Thư viện Y khoa Quốc gia Hoa Kỳ (PubMed / NIH):
     👉 [Emergency Severity Index Triage: A Systematic Review - NIH PubMed](https://www.ncbi.nlm.nih.gov/books/NBK557583/)

2. **Manchester Triage System (MTS):**
   - Tiêu chuẩn phân luồng dựa trên lưu đồ cờ đỏ (Red Flags):
     👉 [Manchester Triage Group Reference](https://www.triagenet.net/)

3. **Bộ Y tế Việt Nam:**
   - Quyết định số **3959/QĐ-BYT** về Tiêu chí đánh giá mức độ khẩn cấp tại Khoa Cấp cứu:
     - Đỏ (Hồi sinh cấp cứu) $\approx$ ESI Level 1
     - Cam (Khẩn cấp) $\approx$ ESI Level 2
     - Vàng (Bán khẩn) $\approx$ ESI Level 3
     - Xanh lá cây (Tiêu chuẩn) $\approx$ ESI Level 4
     - Xanh da trời (Không khẩn cấp) $\approx$ ESI Level 5

---

## 4. CÁCH ĐƯA VÀO CODE VÀ DATABASE CỦA BẠN

Để hệ thống hóa trong mã nguồn dự án, bạn có thể tạo một Enum phân cấp trong Python (`src/medical_assistant/domain/triage.py`):

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

class TriageSeverityLevel(str, Enum):
    LEVEL_1_RESUSCITATION = "LEVEL_1"  # Cấp cứu tối khẩn -> 115
    LEVEL_2_EMERGENT      = "LEVEL_2"  # Khẩn cấp nguy hiểm -> Đến ER ngay
    LEVEL_3_URGENT        = "LEVEL_3"  # Bán khẩn -> Khám trong ngày
    LEVEL_4_STANDARD      = "LEVEL_4"  # Tiêu chuẩn -> Đặt lịch chuyên khoa
    LEVEL_5_NON_URGENT    = "LEVEL_5"  # Không khẩn -> Gói khám / Tái khám

class TriageAnalysisResult(BaseModel):
    severity_level: TriageSeverityLevel
    is_emergency: bool  # True nếu Level 1 hoặc Level 2
    matched_red_flags: List[str]
    suggested_specialty_codes: List[str]
    triage_reasoning: str
    user_advice: str
```

File này đã được lưu vào workspace tại: [`docs/clinical_triage_standards.md`](docs/clinical_triage_standards.md).
