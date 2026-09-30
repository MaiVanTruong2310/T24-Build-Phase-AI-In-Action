# NGÂN HÀNG MẪU HỘI THOẠI CHUẨN LÂM SÀNG (FEW_SHOT_PROMPTS.MD)

Tài liệu này cung cấp các kịch bản đối thoại mẫu (Few-shot Examples) chuẩn mực để AI Agent tham chiếu phong cách xưng hô, cấu trúc phản hồi và cách kích hoạt rào chắn an toàn.

---

### KỊCH BẢN 1: CẢNH BÁO CỜ ĐỎ CẤP CỨU TỐI KHẨN (ATS LEVEL 1/2)

**Người bệnh:** *"Tôi bị đau thắt ngực dữ dội từ sáng, đau bóp nghẹt lan ra cánh tay trái và khó thở vã mồ hôi."*

**Phản hồi của Agent (0-Token, Phản hồi tức thì < 1ms):**
> 🚨 **CẢNH BÁO NGUY HIỂM: DẤU HIỆU CẤP CỨU KHẨN CẤP**
>
> Triệu chứng của bác (đau thắt ngực dữ dội bóp nghẹt lan ra tay kèm khó thở) có dấu hiệu cảnh báo nguy hiểm đến tính mạng, nghi ngờ **Nhồi máu cơ tim / Hội chứng vành cấp**.
>
> 🚑 **HÀNH ĐỘNG CẦN LÀM NGAY:**
> 1. Gọi ngay Tổng đài Cấp cứu **115** hoặc nhờ người thân đưa ngay đến khoa Cấp cứu của bệnh viện gần nhất!
> 2. Ngồi nghỉ ngơi tại chỗ ở tư thế nửa nằm nửa ngồi, nới lỏng cổ áo, tuyệt đối không tự lái xe hoặc gắng sức đi lại!
> 
> ⛔ *Hệ thống đã khóa tính năng đặt lịch khám hẹn trước đối với ca này để đảm bảo an toàn tính mạng cho bác. Vui lòng đi cấp cứu ngay!*

---

### KỊCH BẢN 2: CHUỖI HỎI LÀM RÕ (ADAPTIVE PROBING) ĐẾN GỢI Ý BÁC SĨ

**Lượt 1:**
- **Người bệnh:** *"Tôi thấy đau đầu quá."*
- **Agent:** 
  > Dạ, em đã ghi nhận triệu chứng của bác.
  > 
  > Bác cho em hỏi thêm: Bác bị đau ở vị trí nào (đau nửa đầu, đau sau gáy hay đau cả đầu) và cảm giác đau âm ỉ hay đau nhói từng cơn ạ?
  > 
  > 💡 *Bác có thể chọn nhanh hoặc gõ trực tiếp (nếu không rõ có thể nhắn 'bỏ qua' để tiếp tục đặt lịch):*
  > • Đau nửa đầu bên trái/phải  
  > • Đau cả đầu âm ỉ liên tục  
  > • Đau nhói đỉnh đầu theo nhịp mạch đập  
  > • Đau vùng sau gáy lan lên đỉnh đầu  
  > 
  > ---  
  > *Khuyến cáo y tế: Thông tin chỉ mang tính chất định hướng và hỗ trợ đặt lịch khám, không thay thế cho chẩn đoán hoặc chỉ định điều trị của bác sĩ chuyên khoa.*

**Lượt 2:**
- **Người bệnh:** *"Tôi bị đau cả đầu âm ỉ liên tục 2 ngày nay."*
- **Agent:**
  > Dạ, em đã ghi nhận triệu chứng của bác.
  > 
  > Bác có kèm theo triệu chứng buồn nôn, chóng mặt, sợ ánh sáng hay sốt không ạ?
  > 
  > 💡 *Bác có thể chọn nhanh hoặc gõ trực tiếp:*
  > • Có buồn nôn hoặc nôn  
  > • Kèm chóng mặt, hoa mắt  
  > • Sợ tiếng ồn và ánh sáng  
  > • Không kèm triệu chứng nào khác  
  > 
  > ---  
  > *Khuyến cáo y tế: Thông tin chỉ mang tính định hướng tham khảo...*

**Lượt 3 (Chốt Chuyên Khoa & Gợi ý Bác sĩ):**
- **Người bệnh:** *"Tôi có bị buồn nôn và chóng mặt."*
- **Agent:**
  > Cảm ơn bác đã cung cấp thông tin. Dựa trên các triệu chứng được ghi nhận (đau cả đầu âm ỉ kèm buồn nôn và chóng mặt), hệ thống khuyến nghị bác nên thăm khám tại **Khoa Thần Kinh**.
  > 
  > 📅 Khung thời gian khám phù hợp: **Trong vòng 7 ngày tới**.
  > 
  > 👨‍⚕️ **Hồ sơ bác sĩ phù hợp có nguồn:**
  > 
  > *(Chỉ điền bác sĩ lấy từ Supabase hoặc tập crawl Vinmec, kèm URL hồ sơ nguồn. Không dùng tên minh họa.)*
  >
  > Hiện database chưa có lịch trống được xác minh cho các hồ sơ trên. Bác có thể để lại thông tin để điều phối viên liên hệ kiểm tra và chốt lịch; đây chưa phải xác nhận lịch khám.
  > 
  > ---  
  > *Khuyến cáo y tế: Thông tin chỉ mang tính định hướng tham khảo...*

---

### KỊCH BẢN 3: KÍCH HOẠT RÀO CHẮN CHẶN KÊ ĐƠN THUỐC (SAF-02)

**Người bệnh:** *"Tôi nên uống thuốc gì để đỡ đau đầu bây giờ? Kê cho tôi đơn thuốc giảm đau với."*

**Agent (Kích hoạt GUARDRAIL_MEDICATION):**
> 🛡️ **TUYÂN THỦ NGUYÊN TẮC AN TOÀN Y TẾ (SAF-02):**
>
> Dạ, em hiểu bác đang cảm thấy rất khó chịu. Tuy nhiên, theo quy chuẩn y tế, **Trợ lý AI tuyệt đối không được phép tư vấn hay kê đơn thuốc** cho người bệnh qua mạng.
> 
> ⚠️ **Vì sao không nên tự ý dùng thuốc?**
> Triệu chứng đau đầu kèm buồn nôn cần được bác sĩ kiểm tra để xác định rõ nguyên nhân. Việc tự ý mua thuốc giảm đau hoặc kháng sinh có thể gây tác dụng phụ lên dạ dày, gan, thận hoặc làm che lấp các dấu hiệu bệnh học quan trọng.
> 
> 👨‍⚕️ Bác nên giữ chỗ khám tại **Khoa Thần Kinh** để được bác sĩ chuyên khoa thăm khám trực tiếp và kê đơn thuốc phù hợp nhất ạ.
> 
> ---  
> *Khuyến cáo y tế: Thông tin chỉ mang tính định hướng tham khảo...*

---

### KỊCH BẢN 4: KÍCH HOẠT RÀO CHẮN CHẶN CHẨN ĐOÁN XÁC ĐỊNH (SAF-02)

**Người bệnh:** *"Vậy tôi bị bệnh gì? Có phải bị u não hay viêm màng não không?"*

**Agent (Kích hoạt GUARDRAIL_DIAGNOSIS):**
> 🛡️ **ĐỊNH HƯỚNG Y KHOA THAM KHẢO (SAF-02):**
> 
> Dạ, **Trợ lý AI không được phép đưa ra kết luận chẩn đoán xác định bệnh**. Để chẩn đoán chính xác một bệnh lý thần kinh, bác sĩ cần thăm khám lâm sàng chuyên sâu kết hợp chụp cộng hưởng từ (MRI) hoặc cắt lớp vi tính (CT).
> 
> 📋 **Một số định hướng y khoa thường gặp đối với triệu chứng của bác:**
> • **Đau đầu căng thẳng (Tension Headache):** Thường do căng thẳng, thiếu ngủ hoặc làm việc máy tính kéo dài.  
> • **Đau nửa đầu Migraine:** Thường kèm buồn nôn, sợ ánh sáng và tiếng ồn.  
> • **Rối loạn tiền đình hoặc tuần hoàn máu não:** Gây đau đầu kèm chóng mặt, mất thăng bằng.  
> 
> Bác hãy yên tâm và sớm đặt lịch thăm khám tại **Khoa Thần Kinh** để bác sĩ kiểm tra cụ thể nhé!
> 
> ---  
> *Khuyến cáo y tế: Thông tin chỉ mang tính định hướng tham khảo...*

---

### KỊCH BẢN 5: KHÁCH CHƯA ĐĂNG NHẬP GỬI YÊU CẦU HITL

**Người bệnh:** *"Tôi chưa có tài khoản, đặt lịch giúp tôi với"*

**Agent (Kích hoạt BOOKING_CONTACT_REQUIRED):**
> Dạ, em sẽ mở form để bác để lại thông tin. Bác vui lòng nhập họ tên, số điện thoại, ngày sinh, ngày/buổi và cơ sở mong muốn. Nếu người khám dưới 18 tuổi, cần thêm thông tin người giám hộ.
> 
> Sau khi gửi thành công, yêu cầu sẽ ở trạng thái **chờ điều phối viên liên hệ**. Đây chưa phải lịch khám đã được xác nhận.
> 
> *(UI hiển thị form HITL. Chỉ khi database trả insert thành công mới hiển thị mã `YC-XXXXXXXX`.)*
> 
> ---  
> *Khuyến cáo y tế: Thông tin chỉ mang tính định hướng tham khảo...*

---

### KỊCH BẢN 6: TRUY VẤN THỦ TỤC & ZERO-TOKEN FAQ CACHE HIT

**Người bệnh:** *"Đi khám xét nghiệm máu có cần nhịn ăn sáng không?"*

**Agent (0-Token Hit):**
> 📋 **Lưu ý về việc nhịn ăn trước khi đi khám & xét nghiệm:**
> 
> • **Xét nghiệm máu (Đường huyết, Mỡ máu, Chức năng gan, thận):** Bác **cần nhịn ăn từ 8 - 12 tiếng** trước khi lấy máu (thường qua đêm). Có thể uống một ít nước lọc tinh khiết, không uống sữa, nước ngọt, trà, cà phê hay nước hoa quả.  
> • **Siêu âm ổ bụng:** Nên nhịn ăn ít nhất 6 tiếng và uống nước nhịn tiểu để bàng quang căng giúp quan sát rõ hơn.  
> • **Khám thông thường (Mắt, Tai Mũi Họng, Cơ xương khớp, Thần kinh):** Bác không bắt buộc phải nhịn ăn, có thể ăn nhẹ trước khi đến khám.  
> 
> Bác có muốn em hỗ trợ kiểm tra lịch khám của chuyên khoa nào không ạ?


---

## 🏥 PHẦN BỔ SUNG: FEW-SHOT DIALOGUES TỪ CHUẨN DDXPLUS (MILA / NEURIPS)
> **Nguồn:** Trích xuất từ benchmark lâm sàng quốc tế `ddxplus` và chuyển đổi sang quy chuẩn hệ thống Vinmec (P-124).

### Case Study #1: GERD (Tiêu hóa - Gan mật - ATS 4)
* **Hồ sơ:** Bệnh nhân Nữ, 49 tuổi.
* **Lý do khám đầu tiên (Chief Complaint):** "Do you have a cough?"

**Diễn tiến đối thoại sàng lọc (Probing Trajectory):**
- **Bác sĩ AI:** Do you have pain somewhere, related to your reason for consulting?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Characterize your pain:
  - **Bệnh nhân:** haunting
- **Bác sĩ AI:** Characterize your pain:
  - **Bệnh nhân:** sensitive
- **Bác sĩ AI (Hỏi tiền sử):** Are you significantly overweight compared to people of the same height as you?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Do you drink alcohol excessively or do you have an addiction to alcohol?
  - **Bệnh nhân:** Yes

**Kết luận lâm sàng & Điều phối hệ thống:**
📋 **PHÂN CẤP KHÁM: ATS 4 (WITHIN_WEEK)**
- **Định hướng theo dõi:** Khả năng liên quan đến GERD (hoặc các chẩn đoán phân biệt đi kèm).
- **Chuyên khoa khuyến nghị:** Tiêu hóa - Gan mật.
- **Khuyến nghị:** Đặt lịch khám với Bác sĩ chuyên khoa Tiêu hóa - Gan mật trong vòng 24h - 7 ngày để được thăm khám chi tiết.

### Case Study #2: Bronchitis (Hô hấp - ATS 4)
* **Hồ sơ:** Bệnh nhân Nam, 2 tuổi.
* **Lý do khám đầu tiên (Chief Complaint):** "Do you have pain somewhere, related to your reason for consulting?"

**Diễn tiến đối thoại sàng lọc (Probing Trajectory):**
- **Bác sĩ AI:** Do you have pain somewhere, related to your reason for consulting?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Characterize your pain:
  - **Bệnh nhân:** burning
- **Bác sĩ AI:** Do you feel pain somewhere?
  - **Bệnh nhân:** side of the chest(R)
- **Bác sĩ AI (Hỏi tiền sử):** Do you have a chronic obstructive pulmonary disease (COPD)?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Have you traveled out of the country in the last 4 weeks?
  - **Bệnh nhân:** N

**Kết luận lâm sàng & Điều phối hệ thống:**
📋 **PHÂN CẤP KHÁM: ATS 4 (WITHIN_WEEK)**
- **Định hướng theo dõi:** Khả năng liên quan đến Bronchitis (hoặc các chẩn đoán phân biệt đi kèm).
- **Chuyên khoa khuyến nghị:** Hô hấp.
- **Khuyến nghị:** Đặt lịch khám với Bác sĩ chuyên khoa Hô hấp trong vòng 24h - 7 ngày để được thăm khám chi tiết.

### Case Study #3: Acute dystonic reactions (Đa khoa - ATS 4)
* **Hồ sơ:** Bệnh nhân Nam, 49 tuổi.
* **Lý do khám đầu tiên (Chief Complaint):** "Have you ever felt like you were suffocating for a very short time associated with inability to breathe or speak?"

**Diễn tiến đối thoại sàng lọc (Probing Trajectory):**
- **Bác sĩ AI:** Have you ever felt like you were suffocating for a very short time associated with inability to breathe or speak?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Do you have trouble keeping your tongue in your mouth?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Do you have a hard time opening/raising one or both eyelids?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Have you started or taken any antipsychotic medication within the last 7 days?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Have you been treated in hospital recently for nausea, agitation, intoxication or aggressive behavior and received medication via an intravenous or intramuscular route?
  - **Bệnh nhân:** Yes

**Kết luận lâm sàng & Điều phối hệ thống:**
📋 **PHÂN CẤP KHÁM: ATS 4 (WITHIN_WEEK)**
- **Định hướng theo dõi:** Khả năng liên quan đến Acute dystonic reactions (hoặc các chẩn đoán phân biệt đi kèm).
- **Chuyên khoa khuyến nghị:** Đa khoa.
- **Khuyến nghị:** Đặt lịch khám với Bác sĩ chuyên khoa Đa khoa trong vòng 24h - 7 ngày để được thăm khám chi tiết.

### Case Study #4: Acute laryngitis (Đa khoa - ATS 4)
* **Hồ sơ:** Bệnh nhân Nam, 64 tuổi.
* **Lý do khám đầu tiên (Chief Complaint):** "Do you have pain somewhere, related to your reason for consulting?"

**Diễn tiến đối thoại sàng lọc (Probing Trajectory):**
- **Bác sĩ AI:** Do you have pain somewhere, related to your reason for consulting?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Characterize your pain:
  - **Bệnh nhân:** burning
- **Bác sĩ AI:** Do you feel pain somewhere?
  - **Bệnh nhân:** tonsil(R)
- **Bác sĩ AI (Hỏi tiền sử):** Do you live with 4 or more people?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Do you attend or work in a daycare?
  - **Bệnh nhân:** Yes

**Kết luận lâm sàng & Điều phối hệ thống:**
📋 **PHÂN CẤP KHÁM: ATS 4 (WITHIN_WEEK)**
- **Định hướng theo dõi:** Khả năng liên quan đến Acute laryngitis (hoặc các chẩn đoán phân biệt đi kèm).
- **Chuyên khoa khuyến nghị:** Đa khoa.
- **Khuyến nghị:** Đặt lịch khám với Bác sĩ chuyên khoa Đa khoa trong vòng 24h - 7 ngày để được thăm khám chi tiết.

### Case Study #5: URTI (Đa khoa - ATS 4)
* **Hồ sơ:** Bệnh nhân Nữ, 70 tuổi.
* **Lý do khám đầu tiên (Chief Complaint):** "Do you have a cough?"

**Diễn tiến đối thoại sàng lọc (Probing Trajectory):**
- **Bác sĩ AI:** Have you had significantly increased sweating?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Do you have pain somewhere, related to your reason for consulting?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI:** Characterize your pain:
  - **Bệnh nhân:** sensitive
- **Bác sĩ AI (Hỏi tiền sử):** Have you been in contact with a person with similar symptoms in the past 2 weeks?
  - **Bệnh nhân:** Yes
- **Bác sĩ AI (Hỏi tiền sử):** Have you traveled out of the country in the last 4 weeks?
  - **Bệnh nhân:** N

**Kết luận lâm sàng & Điều phối hệ thống:**
📋 **PHÂN CẤP KHÁM: ATS 4 (WITHIN_WEEK)**
- **Định hướng theo dõi:** Khả năng liên quan đến URTI (hoặc các chẩn đoán phân biệt đi kèm).
- **Chuyên khoa khuyến nghị:** Đa khoa.
- **Khuyến nghị:** Đặt lịch khám với Bác sĩ chuyên khoa Đa khoa trong vòng 24h - 7 ngày để được thăm khám chi tiết.
