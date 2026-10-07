# BỘ CẨM NANG KỸ NĂNG NGHIỆP VỤ AGENT (SKILLS.MD)

Tài liệu này hướng dẫn cách Agent gọi và kết hợp 6 kỹ năng nghiệp vụ chuyên biệt được đóng gói trong các Domain Services tại `src/medical_assistant/domain/`.

---

## 🩺 KỸ NĂNG 1: ĐỘNG CƠ AN TOÀN LÂM SÀNG 3 TẦNG CHUẨN ATS (SAFETY ENGINE v3)

- **Module thực thi:** `triage_service.py` -> `get_triage_service()`
- **Dữ liệu nền tảng:** 741 mặt bệnh phân tầng ATS (gồm 692 bệnh Datalake + 49 bệnh lâm sàng chuẩn quốc tế DDXPlus) từ `data/datalake/normalized/diseases_triaged.jsonl` và Supabase `disease_triage`.
- **Cơ chế hoạt động 3 Tầng Phân Cấp (Hierarchical 3-Tier Architecture):**
  1. **Tầng 1 (Hard Red Flags - Tối Khẩn ATS 1/2):**
     Quét biểu thức chính quy (compiled regex) đa ngữ (Anh - Việt) tức thì trong `< 1ms` cho 9 nhóm cờ đỏ đe dọa mạng sống: Ngừng tuần hoàn/hôn mê, STEMI/Nhồi máu cơ tim tối cấp, F.A.S.T Đột quỵ não, Suy hô hấp cấp/ngưng thở, Xuất huyết tiêu hóa ồ ạt kèm tụt huyết áp, Bụng ngoại khoa cứng như gỗ, Trạng thái động kinh liên tục, Ngộ độc cấp nặng, Thai ngoài tử cung vỡ.
     -> Nếu khớp: Gán `ats_level = 1` hoặc `2`, `urgency_tier = EMERGENCY_BLOCK`, `max_booking_days = 0`, `is_emergency = True`, ghi nhận `triggered_rule_ids`. Ngắt quy trình đặt hẹn thường, hướng dẫn gọi 115 hoặc Hotline Cấp cứu Vinmec.
  2. **Tầng 2 (Syndrome Combination Rules - Hội Chứng Lâm Sàng Phối Hợp):**
     Đánh giá các hội chứng cấp cứu nguy hiểm dựa trên tập triệu chứng bắt buộc (`required_groups`) kết hợp các yếu tố phủ định loại trừ (`negative_factors`) để tránh báo động giả:
     - `ANAPHYLAXIS_ACUTE`: Phù mặt/môi/mày đay + khó thở/thở rít/tụt huyết áp (loại trừ nếu có sốt/ho khạc đờm mủ).
     - `PNEUMOTHORAX_ACUTE`: Đau ngực đột ngột dữ dội/nhói như dao đâm + khó thở (loại trừ trào ngược dạ dày, ho từng cơn gãy sườn).
     - `EPIGLOTTITIS_ACUTE` & `LARYNGOSPASM_ACUTE`: Thở rít thanh quản (stridor/high-pitched), nuốt đau dữ dội, co thắt thanh môn.
     - `PSVT_ARRHYTHMIA_ACUTE`: Tim đập nhanh kịch phát dồn dập + choáng váng/ngất xỉu (loại trừ hoảng loạn tâm lý).
     - `ACUTE_PULMONARY_EDEMA`: Khó thở dữ dội + vã mồ hôi lạnh + phù chân/đau ngực.
     - `COPD_ASTHMA_EXACERBATION`: Tam chứng Anthonisen (khó thở tăng vọt + ho tăng + đờm mủ đục) (loại trừ viêm phế quản kèm chảy mũi).
     - `BOERHAAVE_ACUTE`: Đau ngực/thượng vị dữ dội đột ngột sau nôn ói nhiều lần liên tục.
     - `SCOMBROID_POISONING_ACUTE`: Đỏ bừng mặt + buồn nôn/tiêu chảy cấp sau ăn hải sản.
  3. **Tầng 3 (Warning Signs Bán Khẩn - ATS 3 & Subacute Tuning):**
     Kiểm tra các hội chứng cần khám trong ngày: Đau quặn thận ra máu, sốt cao nghi sốt xuất huyết, viêm ruột thừa cấp nghi ngờ, đi ngoài phân đen bán cấp (không kèm sốc/chóng mặt).
     -> Gán `ats_level = 3`, `urgency_tier = SAME_DAY`, `max_booking_days = 1`.
  4. **Tầng 4 (So khớp Bệnh học 741 Bệnh - ATS 4/5):**
     Tính điểm so khớp (matching score) dựa trên: tên bệnh (25đ), bigram cờ đỏ (5đ), warning signs (3đ), triệu chứng thông thường (2đ).
     -> Không cho phép candidate matching tạo cờ đỏ ATS 1/2 giả nếu không vượt qua Tầng 1/2.
  5. **Tầng 5 (Fallback Triệu chứng chung):**
     Nếu không khớp bệnh rõ ràng: Gợi ý khoa **"Sức khỏe tổng quát"** (`TONG_QUAT`), `max_booking_days = 7`, yêu cầu hỏi thêm triệu chứng.

---

## 💬 KỸ NĂNG 2: HỎI LÀM RÕ THÍCH ỨNG (ADAPTIVE PROBING SKILL)

- **Module thực thi:** `probing_service.py` -> `get_probing_service()`
- **Cơ chế hoạt động:**
  1. Nhận diện nhóm triệu chứng chính (Category): Thần kinh, Tiêu hóa, Xương khớp, Hô hấp, Sức khỏe tổng quát.
  2. Theo dõi biến đếm lượt hỏi: `probing_turn` (khởi đầu từ `0`, tối đa là `2`).
  3. **Lượt 1 (Turn 0 -> 1):** Hỏi về thời gian khởi phát và tính chất đau (đau âm ỉ, đau buốt, đau quặn).
     - Trả về câu hỏi làm rõ (`next_question`).
     - Trả về danh sách chip trả lời nhanh (`quick_replies`), ví dụ: `["Mới bị 1-2 ngày nay", "Đã kéo dài hơn 1 tuần", "Đau từng cơn", "Đau âm ỉ liên tục"]`.
  4. **Lượt 2 (Turn 1 -> 2):** Hỏi về triệu chứng phối hợp hoặc biểu hiện toàn thân (có buồn nôn, chóng mặt, sốt hay ợ chua không).
  5. **Kết thúc Probing (Turn >= 2 hoặc khi người dùng nhắn "bỏ qua"):**
     - Đặt `needs_more_probing = False`.
     - Chuyển `workflow_status = "TRIAGED_READY_FOR_BOOKING"`.
     - Kích hoạt tìm kiếm danh sách bác sĩ chuyên khoa.
  6. **Cô lập episode và chủ thể:**
     - Chỉ ghi tin nhắn có dữ kiện lâm sàng của chính người dùng vào `collected_details`.
     - Nhánh `SOCIAL_REDIRECT` xử lý câu xã hội mà không tái triage.
     - Nhánh `THIRD_PARTY_HEALTH_GUIDANCE` xử lý thông tin người khác, giữ nguyên episode của người dùng.
     - `SELF_CARE_FOLLOWUP` quay lại ATS/chuyên khoa gần nhất của chính người dùng.

---

## 👨‍⚕️ KỸ NĂNG 3: TRA CỨU BÁC SĨ & LỊCH KHÁM KHẢ DỤNG (DOCTOR & SCHEDULE DISCOVERY)

- **Module thực thi:** `doctor_schedule_service.py` -> `get_doctor_schedule_service()`
- **Dữ liệu nền tảng:** 992 hồ sơ bác sĩ Vinmec & danh mục Chuyên khoa (`SPECIALTY_ALIAS_MAP`).
- **Cơ chế hoạt động:**
  1. Chuẩn hóa tên chuyên khoa từ kết quả Triage (loại bỏ dấu, map alias: *"thần kinh"* -> *"nội thần kinh"*, *"ngoại thần kinh"*, *"neurology"*).
  2. Truy vấn Supabase theo quan hệ `specialties -> doctor_specialties -> doctors -> doctor_schedules`:
     - Chỉ hiển thị slot có bản ghi thật, `status = 'available'` và UUID lịch từ database.
     - Tuyệt đối không tạo tên bác sĩ, mã slot hoặc giờ khám bằng dữ liệu hardcode/hash.
  3. Nếu Supabase chưa có lịch, fallback chỉ để tra cứu **hồ sơ bác sĩ có nguồn** từ tập crawl 992 hồ sơ Vinmec:
     - Hiển thị tên, chức danh, nơi công tác, mô tả chuyên môn và URL nguồn Vinmec nếu có.
     - Gắn `schedule_verified = false`, không hiển thị giờ trống và nói rõ lịch chưa được database xác minh.
  4. Định dạng thời gian theo giờ Việt Nam (**GMT+7**):
     - Hàm `format_utc_to_vn_time()` chuyển đổi thời gian UTC sang định dạng: `08:30 (Sáng) - 25/09/2026`.

---

## 📅 KỸ NĂNG 4: TIẾP NHẬN YÊU CẦU & HITL (BOOKING INTAKE STATE MACHINE)

- **Module thực thi:** `booking_request_service.py`, `routes.py`, `example_node.py`
- **Cơ chế hoạt động:**
  1. Khi khách chưa đăng nhập muốn đặt lịch, trả `workflow_status = "BOOKING_CONTACT_REQUIRED"` và render form đầy đủ: họ tên, điện thoại, ngày sinh, giới tính, email, bác sĩ mong muốn, ngày/buổi/cơ sở, thời gian liên hệ, ghi chú và đồng ý liên hệ.
  2. Người dưới 18 tuổi bắt buộc có họ tên và số điện thoại người giám hộ.
  3. Backend dùng `SUPABASE_SERVICE_ROLE_KEY` phía máy chủ để ghi bảng `booking_requests`; trình duyệt và khóa `anon` không được ghi trực tiếp PII.
  4. Chỉ sau khi database insert thành công mới trả `saved = true`, mã `YC-XXXXXXXX` và trạng thái `PENDING_CONTACT`.
  5. `PENDING_CONTACT` chỉ có nghĩa yêu cầu đã vào hàng đợi điều phối; **không phải giữ slot hay xác nhận lịch**. Nếu DB lỗi, trả HTTP 503 và không được báo thành công.

---

## ⚡ KỸ NĂNG 5: ZERO-TOKEN CACHE & ĐO LƯỜNG TIKTOKEN (COST & METRICS OPTIMIZATION)

- **Module thực thi:** `cache_service.py` & `token_counter.py`
- **Cơ chế hoạt động:**
  1. **Zero-Token Cache Hit:**
     - Kiểm tra các mẫu câu chào hỏi, bảng giá khám, hướng dẫn nhịn ăn xét nghiệm, hotline giờ làm việc, và quy định đổi/hủy lịch.
     - Nếu hit cache: Trả về câu trả lời đã biên tập chuẩn y khoa, gán `tokens_saved = True`, **không tốn bất kỳ token LLM nào**.
  2. **Đo lường Token Chi Tiết (tiktoken):**
     - Sử dụng encoding `cl100k_base` (chuẩn của GPT-4o / GPT-4o-mini).
     - Tính toán 4 chỉ số: `prompt_tokens`, `completion_tokens`, `total_tokens`, và `tokens_saved`.
     - Đính kèm vào `metadata.token_usage` của kết quả để hiển thị trực quan trên giao diện người dùng.

---

## 🔤 KỸ NĂNG 6: NHẬN DIỆN LỖI GÕ PHÍM & TỪ KHÓA CHUYÊN KHOA (TYPO TOLERANCE)

- **Module thực thi:** `guardrail_service.py`
- **Cơ chế hoạt động:**
  - Hỗ trợ phát hiện các lỗi gõ Telex phổ biến trên bàn phím tiếng Việt (ví dụ: gõ nhầm *"khia"* thay vì *"khoa"*: *"thông tin về khia sức khỏe tổng quát"*).
  - Tự động tách cụm từ tên chuyên khoa, tìm kiếm trong kho tri thức và trả lời đầy đủ chức năng, dịch vụ của chuyên khoa đó mà không bị gián đoạn hội thoại.

---

## ⚡ KỸ NĂNG 7: TÍCH HỢP SUPABASE MCP & POSTGRES AGENT SKILLS

- **Cấu hình MCP Server:** Được định nghĩa tại `.mcp.json` và `.agents/mcp_config.json` kết nối tới `https://mcp.supabase.com/mcp` với các tính năng (`features`): `docs`, `account`, `database`, `debugging`, `development`, `functions`, `branching`.
- **Cài đặt Agent Skills:**
  - `supabase`: Cung cấp bộ công cụ toàn diện quản trị Supabase Database, Auth, Realtime, Storage, Vector và Edge Functions.
  - `supabase-postgres-best-practices`: Bộ quy tắc tối ưu hóa thiết kế lược đồ quan hệ, chỉ mục HNSW/pgvector, RLS Policies, truy vấn tối ưu và chống deadlock.
- **Xác thực bảo mật:**
  - Kích hoạt qua lệnh `claude /mcp` trong terminal thông thường, đăng nhập OAuth mà không cần lưu API key nhạy cảm trong mã nguồn.
  - Khi cần truy vấn schema, kiểm tra logs hoặc chạy migration, Agent gọi công cụ MCP thông qua server `supabase` đã xác thực.

---

## 🎯 KỸ NĂNG 8: BỘ ĐIỀU PHỐI CHUYÊN KHOA 3 TẦNG (SPECIALTY ROUTER v2.0)

- **Module thực thi:** `specialty_router.py` → `get_specialty_router()`
- **Cơ chế hoạt động:**
  1. **Tầng 1 — Pathology Lookup (O(1), <1ms):**
     Tra cứu trực tiếp tên bệnh (pathology) trong bảng mapping 49 bệnh DDXPlus → Vinmec specialty code.
     → Nếu khớp: Trả kết quả ngay với `confidence = 1.0`. Dừng.
  2. **Tầng 2 — Semantic Keyword Router (<50ms):**
     Tính overlap score giữa query tokens và specialty keyword prototypes (bilingual EN-VI).
     Sử dụng unigram + bigram matching, normalized scoring.
     → Nếu score ≥ 0.15 (threshold): Trả kết quả với confidence = score. Dừng (nếu score ≥ 0.25).
  3. **Tầng 3 — LLM-based Router (~500ms):**
     Gọi GPT-4o-mini với structured JSON output để phân loại chuyên khoa.
     Prompt chứa danh sách 18 chuyên khoa hợp lệ tại Vinmec.
     → Trả kết quả với confidence từ LLM. Dùng cho production real-time routing.

- **Tích hợp vào Triage Engine:**
  - `triage_service.py` Bước 3: Khi match bệnh, dùng Router để refine specialty nếu disease DB trả generic.
  - `triage_service.py` Bước 4 (Fallback): Dùng Router thay vì luôn trả "Sức khỏe tổng quát".

- **Kết quả Benchmark:**
  - Độ chính xác điều phối tăng từ **~13% → ~80%** (+67 điểm %).
  - Safety Recall duy trì **100%** trên toàn bộ 28 ca cấp cứu.

---

## 🌐 KỸ NĂNG 9: DỊCH VỤ SONG NGỮ ANH - VIỆT VÀ CHUẨN HÓA QUỐC TẾ (BILINGUAL ENGINE)

- **Module thực thi:** `language_service.py` -> `get_language_service()`
- **Cơ chế hoạt động:**
  1. **Nhận diện Ngôn ngữ Tức thì (`detect_language`):**
     Phân tích tần suất từ khóa y khoa tiếng Anh (`chest pain`, `dyspnea`, `fever`, `doctor`, `appointment`) và tiếng Việt (`đau ngực`, `khó thở`, `sốt`, `bác sĩ`, `khám`) để xác định ngôn ngữ đầu vào (`en` hoặc `vi`).
  2. **Chuẩn hóa Mã Chuyên khoa Chính tắc (`canonicalize_specialty_code`):**
     Quy chuẩn mọi tên gọi chuyên khoa tiếng Việt hoặc tiếng Anh (kể cả alias, không dấu, tên khoa bệnh viện) về 11 mã chuẩn: `HO_HAP`, `TIM_MACH`, `TIEU_HOA`, `TAI_MUI_HONG`, `THAN_KINH`, `MIEN_DICH`, `TRUYEN_NHIEM`, `TAM_THAN`, `XUONG_KHOP`, `DA_LIEU`, `TONG_QUAT`.
  3. **Bộ Mẫu Phản hồi Y khoa Song ngữ Chuẩn mực:**
     - Hướng dẫn Cấp cứu Quốc tế (`get_emergency_guidance`): Cảnh báo tính mạng, gọi 115 hoặc Hotline Vinmec 24/7.
     - Hướng dẫn Điều phối Khám (`get_triage_guidance`): Giải thích lý do gợi ý chuyên khoa, khuyến nghị thời gian khám an toàn (`max_booking_days`).
     - Tiếp nhận Yêu cầu Đặt hẹn (get_hold_booking_response): Ghi nhận thông tin yêu cầu đặt hẹn, mã tham chiếu REQ-XXXXXX chuyển Điều phối viên y tế liên hệ xác nhận.
     - Tuyên bố Miễn trừ Y tế (`get_medical_disclaimer`): Khẳng định AI chỉ mang tính định hướng, không thay thế chẩn đoán bác sĩ.
  4. **Tích hợp Toàn diện Toàn Pipeline:**
     - `triage_service.py`: Quét cờ đỏ tiếng Anh trực tiếp mà không cần qua dịch máy.
     - `guardrail_service.py`: Chặn đơn thuốc và chẩn đoán khẳng định bằng cả tiếng Anh và tiếng Việt.
     - `cache_service.py`: Trả FAQ Zero-Token tiếng Anh (< 0.1ms) cho thủ tục nhịn ăn, bảng giá, giờ khám và hủy lịch.
     - `probing_service.py`: Câu hỏi làm rõ triệu chứng và chip chọn nhanh bằng tiếng Anh.
     - `example_node.py` (LangGraph): Tự động duy trì trạng thái ngôn ngữ hội thoại xuyên suốt lượt chat.

---

## 🛡️ KỸ NĂNG 10: TƯỜNG LỬA BẢO MẬT ĐA TẦNG & CHỐNG TẤN CÔNG HỆ THỐNG (SECURITY & DE-OBFUSCATION GUARDRAIL)

- **Module thực thi:** `src/medical_assistant/domain/security/`
  - `deobfuscator.py` -> `get_deobfuscator()`
  - `security_guardrail_service.py` -> `get_security_guardrail_service()`
  - `dlp_service.py` -> `get_dlp_service()`
- **Cơ chế hoạt động 4 Tầng Phòng Thủ (Defense-in-Depth):**
  1. **Tầng 0 — Bóc tách & Chuẩn hóa Tiền Xử lý (De-obfuscation Engine):**
     - Loại bỏ ký tự tàng hình (Zero-width spaces `\u200B`, `\u200C`, `\u200D`, `\uFEFF`, soft hyphen `\u00AD`, BiDi `\u202E`).
     - Chuẩn hóa Unicode Homoglyphs (Cyrillic `а`/`с`/`е`/`о` $\to$ Latin `a`/`c`/`e`/`o`).
     - Tự động nhận diện và giải mã các biến thể: Mã Morse (`... --- ...`), Nhị phân 8-bit (`01100001`), Hexadecimal (`\x6b\x65`, `0x...`), Base64 hợp lệ, Leetspeak (`k3_d0n`, `thu0c`) và Token-splitting (`t h u o c`).
     - Hỗ trợ giải mã đệ quy tối đa 2 lớp (ví dụ: Hex bọc trong Base64) trước khi đưa dữ liệu vào Triage lâm sàng.
  2. **Tầng 1 — Tường lửa An ninh Đầu vào (Adversarial Defense):**
     - Phát hiện Prompt Injection & Jailbreak (DAN, Developer Mode, Roleplay phá vỡ rào chắn, chỉ thị "ignore previous instructions").
     - Chặn yêu cầu trích xuất System Prompt (Prompt Exfiltration), câu lệnh thao tác cơ sở dữ liệu (`DROP TABLE`, `UNION SELECT`), và các nội dung nguy hiểm (vũ khí, tự hại).
     - Ngắt luồng hội thoại ngay lập tức (`workflow_status = "SECURITY_BLOCKED"`), không tốn token LLM (`tokens_saved = True`).
  3. **Tầng 2 — Cách ly Đa Bệnh nhân (Multi-Tenant PHI/PII Protection):**
     - Chặn đứng mọi nỗ lực dò hỏi thông tin cá nhân, số điện thoại, CCCD/CMND, BHYT hay lịch khám của bệnh nhân khác.
     - Đảm bảo AI chỉ hoạt động trong phạm vi phiên khám được xác thực của người dùng hiện tại.
  4. **Tầng 3 — Tường lửa Ngăn Chặn Rò Rỉ Dữ Liệu Đầu Ra (Output DLP Sanitization):**
     - Quét toàn bộ phản hồi trước khi gửi về client.
     - Tự động làm sạch và che giấu:
       - Secret keys & Tokens: OpenAI API Key (`sk-...`), Supabase Service Role Key (`sbp_...`), JWT Tokens (`eyJ...`), Database URLs (`postgres://...`).
       - Dữ liệu PII của người khác: Số CCCD 9-12 số, Thẻ BHYT 15 số, Số điện thoại lạ, Email lạ.
       - Thay thế bằng các nhãn an toàn: `[REDACTED_SECRET]`, `[REDACTED_PII]`, `[REDACTED_PHONE]`.

---

## 🔬 KỸ NĂNG 11: PHÂN LOẠI PHỦ ĐỊNH & PHÂN CỰC LÂM SÀNG (CLINICAL NEGATION & POLARITY SERVICE)

- **Module thực thi:** `clinical_negation_service.py` -> `get_clinical_negation_service()`
- **Cơ chế hoạt động:**
  1. **Nhận diện Từ khóa Phủ định Đa ngữ (Vietnamese & English):**
     - Tiếng Việt: `không`, `chưa`, `chẳng`, `chả`, `hết`, `đâu có`, `chưa từng`, `không còn`, `ko`, `k`.
     - Tiếng Anh: `denies`, `denied`, `negative for`, `free of`, `without`, `never`, `not`, `no`, `none`.
  2. **Xác định Phạm vi Phủ định Theo Mệnh đề (Clause-Boundary Scoping):**
     - Giới hạn phạm vi từ từ phủ định đến ranh giới câu hoặc liên từ đối lập: `[.,;!?\n]` hoặc `nhưng`, `tuy nhiên`, `song`, `còn`, `mà`, `chứ`, `but`, `however`, `although`, `yet`.
     - Sử dụng regex word boundary `\b` đối chiếu dung sai cao cả tiếng Việt có dấu và không dấu (xử lý triệt để `'đ'`/`'d'`).
  3. **Phân tách Phân cực (Polarity Partitioning):**
     - Phân định rạch ròi giữa `positive` (triệu chứng bệnh nhân thực sự có) và `negative` (triệu chứng bệnh nhân phủ định hoặc đã khỏi).
     - **Triệt tiêu Over-triage:** Ngăn chặn tuyệt đối việc kích hoạt nhầm cờ đỏ cấp cứu tim mạch khi bệnh nhân nhắn: *"Tôi bị đau bụng quặn thượng vị, không đau ngực, không khó thở"*.

---

## 🧠 KỸ NĂNG 12: BỘ TRÍCH XUẤT DỮ KIỆN KẾT HỢP HYBRID & CONFIDENCE ROUTER (HYBRID FACT EXTRACTOR)

- **Module thực thi:** `llm_clinical_extractor.py` -> `get_llm_clinical_extractor()` kết hợp `clinical_fact_service.py`
- **Cơ chế hoạt động:**
  1. **Mô hình Dữ kiện Cấu trúc Chuẩn Y khoa (`ClinicalFactModel`):**
     - Trích xuất: `chief_complaint`, `positive_facts`, `negative_facts`, `duration_days`, `bowel_interval_days`, `location`, `severity`, `qualifiers`.
  2. **Confidence Router 3 Tầng Thông Minh:**
     - *Tầng 1 (Rule Engine - 0ms, 0 Token):* Xử lý ngay lập tức các mô tả triệu chứng ngắn, rõ ràng, đơn bệnh.
     - *Tầng 2 (Small LLM - GPT-4o-mini structured output):* Tự động kích hoạt khi câu dài (> 40 ký tự), có các liên từ sắc thái phức tạp (*"tưởng là"*, *"nghĩ là"*, *"nhưng không"*, *"dữ dội"*, *"từ hôm kia"*), hoặc khi câu chứa từ than phiền mà Rule Engine chưa bao quát hết.
     - *Tầng 3 (Fallback An toàn):* Nếu LLM gặp lỗi mạng/timeout, tự động giáng cấp xuống Rule Engine, không làm gián đoạn hội thoại của người bệnh.
  3. **Fact-Aware Probing Đa Chuyên Khoa:**
     - Mở rộng cơ chế kiểm tra dữ kiện đã biết ra toàn bộ các chuyên khoa thường gặp: **Đau đầu / Thần kinh (`DAU_DAU`)**, **Đau bụng / Tiêu hóa (`DAU_BUNG`)**, **Cơ xương khớp (`CO_XUONG_KHOP`)**, và **Táo bón (`TAO_BON`)**.
     - **Chống lặp câu hỏi (Zero Duplicate Questions):** Nếu bệnh nhân đã cung cấp vị trí và thời gian đau ở lượt 1, hệ thống không hỏi lại mà chuyển thẳng sang kiểm tra các cờ đỏ báo động còn thiếu hoặc chốt chuyên khoa sẵn sàng đặt lịch.

---

## 🔁 KỸ NĂNG 13: LLM MULTI-PROVIDER FAILOVER

- **Module thực thi:** `infrastructure/llm.py` -> `get_llm()`.
- **Nhà cung cấp chính:** OpenRouter qua giao diện OpenAI-compatible.
- **Nhà cung cấp dự phòng:** Google AI Studio (Gemini) qua giao diện OpenAI-compatible.
- **Cơ chế:** Mọi lời gọi thường và structured output đều thử nhà cung cấp chính trước; khi lỗi kết nối, xác thực, timeout hoặc hết hạn mức thì tự động chuyển sang nhà cung cấp dự phòng.
- **Kiểm soát chi phí:** `max_retries=0` tại từng provider để tránh retry kép; router Hybrid vẫn chỉ gọi LLM cho câu phức tạp hoặc thiếu dữ kiện.
- **Quản lý bí mật:** API key chỉ tồn tại trong `.env` đã được `.gitignore` bảo vệ. Tài liệu context, source code, test và log không được chứa giá trị khóa.
- **Quan sát vận hành:** Phân biệt `llm_attempted`, `llm_succeeded` và `llm_invoked`; lỗi cả hai provider mới giáng cấp an toàn về Rule Engine.



