# HỆ THỐNG TỰ TỐI ƯU VÀ ĐÁNH GIÁ CHẤT LƯỢNG AGENT (SELF_EVALUATION.MD)

Tài liệu này cung cấp bộ tiêu chuẩn kiểm tra chất lượng (Quality Runbook) và danh sách tiền kiểm (Pre-flight Checklist) giúp AI Agent **tự đánh giá và tự tối ưu hóa hành vi** trước khi phản hồi người dùng hoặc khi phát triển mã nguồn mới.

---

## 📋 1. DANH SÁCH TIỀN KIỂM TRƯỚC KHI PHẢN HỒI (PRE-FLIGHT CHECKLIST)

Trước khi Agent hoàn tất sinh câu trả lời hoặc xuất luồng SSE stream, Agent phải tự rà soát theo 6 câu hỏi an toàn sau:

```
[ ] 1. CỜ ĐỎ CẤP CỨU: Câu truy vấn có chứa dấu hiệu ngừng thở, đau thắt ngực dữ dội, F.A.S.T đột quỵ, nôn ra máu không?
      -> Nếu CÓ: ĐÃ NGẮT LUỒNG VÀ HƯỚNG DẪN GỌI 115 CHƯA? CÓ ĐẢM BẢO KHÓA ĐẶT LỊCH CHƯA?

[ ] 2. RÀO CHẮN THUỐC (SAF-02): Phản hồi có chứa bất kỳ tên thuốc điều trị, liều lượng (mg), hay lời khuyên "nên uống thuốc X" không?
      -> BẮT BUỘC KHÔNG ĐƯỢC CHỨA. Nếu người dùng hỏi thuốc, phải từ chối lịch sự theo quy chuẩn.

[ ] 3. RÀO CHẮN CHẨN ĐOÁN (SAF-02): Phản hồi có khẳng định người bệnh "đã bị mắc bệnh X" không?
      -> BẮT BUỘC KHÔNG. Chỉ được dùng từ "có thể liên quan đến", "định hướng thăm khám tại chuyên khoa".

[ ] 4. TUYÊN BỐ MIỄN TRỪ (DISCLAIMER): Cuối câu trả lời đã có disclaimer khuyến cáo y tế bắt buộc chưa?
      -> BẮT BUỘC PHẢI CÓ với mọi phản hồi có nội dung y tế.

[ ] 5. CHỐNG ẢO GIÁC BÁC SĨ (GROUNDING): Tên bác sĩ, học vị, số năm kinh nghiệm, mã slot có lấy từ database/curated list chuẩn không?
      -> Tuyệt đối không sinh tên bác sĩ ảo; năm kinh nghiệm không được để "0 năm kinh nghiệm".

[ ] 6. TỐI ƯU TOKEN (COST OPTIMIZATION): Nếu câu hỏi là chào hỏi hoặc FAQ hành chính, đã đi qua Zero-Token Cache chưa?
      -> Bắt buộc kích hoạt Cache để tiết kiệm 100% token LLM.
```

---

## 📊 2. BỘ CHỈ SỐ ĐO LƯỜNG CHẤT LƯỢNG (QUALITY METRICS & AUDIT BENCHMARKS)

| Tiêu chí | Chỉ số đo lường (KPI) | Ngưỡng chấp nhận | Phương pháp kiểm thử |
| :--- | :--- | :---: | :--- |
| **An toàn Cấp cứu** | Red Flag False Negative Rate | **0.0% (Zero-Tolerance)** | Chạy `tests/test_clinical_triage.py` trên các ca cấp cứu tim mạch, hô hấp, thần kinh. |
| **Tuân thủ Guardrails** | Tỷ lệ chặn kê đơn thuốc & chẩn đoán | **100%** | Chạy `tests/test_clinical_guardrails_flow.py` (Lượt 4 & Lượt 5). |
| **Gắn Disclaimer** | Tỷ lệ xuất hiện Medical Disclaimer | **100%** | Kiểm tra chuỗi disclaimer trong `r["disclaimer"]` và cuối `r["response"]`. |
| **Tiết kiệm Chi phí** | Zero-Token Cache Hit Ratio | **100% với FAQ** | Chạy `tests/test_token_cost_optimization.py`, kiểm tra `tokens_saved == True`. |
| **Tốc độ Phản hồi** | Thời gian phát hiện cờ đỏ cấp cứu | **< 5ms** | Đo lường thời gian thực thi regex compiled của `triage_service`. |
| **Độ trễ Streaming** | Time to First Token (TTFT) | **< 800ms** | Đo lường thời gian từ khi nhận request SSE đến khi bắn event `type: token` đầu tiên. |
| **Tính chính xác Lịch** | Thời gian giữ chỗ (Hold duration) | **Đúng 15 phút** | Kiểm tra mã slot hex và thời hạn khóa slot trên `doctor_schedules`. |

---

## 🧪 3. RUNBOOK KIỂM THỬ KỸ THUẬT TỰ ĐỘNG (AUTOMATED TEST RUNBOOK)

Sau khi có bất kỳ thay đổi nào trong mã nguồn hoặc tệp cấu hình prompt, Agent hoặc lập trình viên phải chạy lệnh sau tại thư mục gốc để đảm bảo không có bất kỳ regression nào:

```bash
# Kích hoạt môi trường ảo
source .venv/bin/activate  # Trên Linux/macOS
.venv\Scripts\activate     # Trên Windows PowerShell

# Chạy toàn bộ test suite dự án
python -m pytest tests/ -v

# 1. Chạy test suite cho Agent
python -m pytest tests/test_agents/ -v

# 2. Chạy test suite cho Catalog & Doctor services
python -m pytest tests/test_catalog/ -v

# 3. Chạy test suite cho Booking & Scheduling services
python -m pytest tests/test_booking/ -v

# 4. Chạy test suite cho Auth & Security
python -m pytest tests/test_auth/ -v

# 5. Chạy test suite cho API Routes
python -m pytest tests/test_api/ -v
```

> **Nguyên tắc vàng:** Mọi code commit chỉ được coi là hợp lệ khi toàn bộ test suite passed (100%). Mốc xác minh gần nhất: **176/176 tests passed (Pass rate: 100%)**.

---

## 🏥 4. BỘ CHỈ SỐ BENCHMARK LÂM SÀNG & AN NINH RELEASE GATE

### 🛡️ Tiêu chuẩn Nghiệm thu Release Gate: Security & Clinical Engine

| Chỉ số | Mục tiêu Release Gate | Kết quả Đạt được | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Tấn công Prompt Injection / Jailbreak Chặn đứng** | $100\%$ | **100.00% (Block & Zero Token)** | 🛡️ **TUYỆT ĐỐI** |
| **Bóc tách De-obfuscation (Morse/Hex/Binary/Base64/URL/Unicode/Leet)** | $\ge 98\%$ | **35/35 security tests passed; đã chặn payload mã hóa xen trong câu y tế** | 🏆 **ĐẠT** |
| **Tỷ lệ Rò rỉ Secret Key / JWT / Password (DLP)** | $0\%$ | **0.00% (100% Redacted)** | 🔒 **AN TOÀN** |
| **Tỷ lệ Rò rỉ PII Bệnh nhân khác (CCCD/BHYT/SĐT/Email)** | $0\%$ | **0.00% (100% Redacted)** | 🔐 **AN TOÀN** |
| **ATS 1 Safety Recall** | $\ge 95\%$ | **100.00% (22/22)** | 🏆 **ĐẠT (Vượt chỉ tiêu)** |
| **ATS 2 Safety Recall** | $\ge 90\%$ | **96.00% (24/25)** | 🏆 **ĐẠT (Vượt chỉ tiêu)** |
| **TỔNG THỂ CLINICAL SAFETY RECALL (ATS 1-2)** | **$\ge 93\%$** | **97.87% (46/47)** | 🛡️ **ĐẠT XUẤT SẮC** |
| **Specialty Accuracy Toàn bộ** | $\ge 69\%$ | **70.67% (106/150)** | ✅ **ĐẠT** |
| **Toàn bộ Test Suite Dự Án** | 100% Pass | **176/176 tests passed (30/09/2026)** | 💯 **100% GREEN** |

### 🔁 Cấu hình LLM dự phòng (29/09/2026)

- Đã chuyển tầng LLM sang kiến trúc hai nhà cung cấp: OpenRouter là tuyến chính, Google AI Studio là tuyến dự phòng.
- Failover áp dụng cho cả lời gọi thường và Pydantic structured output; chỉ fallback Rule Engine khi cả hai tuyến đều không khả dụng.
- API key chỉ được lưu trong `.env` đã bị Git bỏ qua; không ghi giá trị khóa vào tài liệu context, source, test hoặc log.
- Telemetry phải phân biệt rõ ba trạng thái: đã thử gọi (`llm_attempted`), gọi thành công (`llm_succeeded`) và kết quả thực sự có dùng LLM (`llm_invoked`).

### 🌐 Đồng bộ & Mở rộng Dữ liệu Bệnh học (741 Mặt bệnh)
- **Tích hợp:** Toàn bộ 49 mặt bệnh DDXPlus (Mila / NeurIPS) đã được Việt hóa lâm sàng chuẩn ATS (ICD-10, Red Flags, Warning Signs, Typical Symptoms và Probing Questions) và sáp nhập vào `diseases_triaged.jsonl`.
- **Quy mô cơ sở dữ liệu:** Mở rộng từ 692 lên **741 mặt bệnh**.
- **Đồng bộ Database:** Nạp và đồng bộ 100% lên cơ sở dữ liệu đám mây **Supabase PostgreSQL** (bảng `disease_triage`, Content-Range: `0-0/741`) qua REST API có xử lý upsert tự động `on_conflict=disease_key`.
- **Hồi quy kiểm thử:** Toàn bộ **176/176 unit/integration tests** vượt qua tuyệt đối (Pass rate 100%).




