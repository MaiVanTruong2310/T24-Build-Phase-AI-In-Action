# AI AGENT CONTEXT & SELF-OPTIMIZATION HUB (P-124)

Thư mục `context_agent/` là trung tâm tri thức (Context & Knowledge Hub) được thiết kế theo tiêu chuẩn kỹ thuật cao, giúp AI Agent (Antigravity, Cursor, Claude, LLM Core) hiểu sâu sắc toàn bộ nghiệp vụ, tôn trọng các giới hạn an toàn y tế và **tự tối ưu hóa hiệu năng phản hồi** trong dự án **P-124: Trợ Lý Y Tế Đặt Lịch & Điều Hướng Chuyên Khoa Thông Minh**.

---

## 🗺️ BẢN ĐỒ TRI THỨC AGENT (KNOWLEDGE ARCHITECTURE)

| File | Tên tài liệu | Mục đích & Chức năng |
| :--- | :--- | :--- |
| [PRODUCT_SPECIFICATION_REPORT.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/PRODUCT_SPECIFICATION_REPORT.md) | **Đặc tả Sản phẩm & Kiến trúc (BA/PO Report)** | Bản báo cáo toàn diện v1.1.0 về bối cảnh, PRD, sơ đồ kiến trúc 2 giai đoạn, data schema, finite state machine và KPI sản phẩm. |
| [AGENT.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/AGENT.md) | **Định danh & Vai trò Cốt lõi (Identity & Spec)** | Xác lập chân dung AI Trợ lý tiếp đón y tế, tôn chỉ giao tiếp, phong cách xưng hô và phạm vi trách nhiệm. |
| [RULES.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/RULES.md) | **Hệ thống Quy tắc Vàng & Rào chắn (Golden Rules)** | Bộ quy tắc bắt buộc: Cờ đỏ cấp cứu SAF-01, Chặn kê đơn & chẩn đoán SAF-02, Concurrency slot locking, bảo mật PII/DLP, và Phân tầng quyền hạn kiến trúc Hybrid (Rule Engine nắm quyền an toàn tối cao). |
| [SKILLS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/SKILLS.md) | **Bộ Kỹ năng Chuyên sâu (Agent Skills)** | Hướng dẫn thực thi 12 kỹ năng nghiệp vụ: Safety Engine v3 (3 tầng ATS 1-5), Adaptive Probing, Grounded Search (992 bác sĩ), Slot Locking 15 phút, Zero-Token Caching, Typo Tolerance, Tích hợp Supabase MCP, Specialty Router v2.0, Bilingual Engine (EN-VI), Tường lửa Bảo mật Đa tầng & De-obfuscation Guardrail (Anti-Jailbreak & DLP), Phân loại phủ định lâm sàng (`ClinicalNegationService`), và Trích xuất dữ kiện Hybrid kết hợp LLM (`LLMClinicalExtractor`). |
| [WORKFLOWS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/WORKFLOWS.md) | **Quy trình & Sơ đồ Quyết định (State Workflows)** | Luồng xử lý phân tầng qua StateGraph LangGraph (Analyze với 6 cổng an toàn -> Find Doctors -> Respond) kèm logic rẽ nhánh short-circuit. |
| [FEW_SHOT_PROMPTS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/FEW_SHOT_PROMPTS.md) | **Ngân hàng Mẫu Hội thoại Chuẩn (Few-shot Bank)** | Tuyển tập các ca đàm thoại mẫu chuẩn mực: Cấp cứu, hỏi đơn thuốc, hỏi bệnh, giữ chỗ, hỏi thông tin khoa và câu hỏi thủ tục. |
| [SELF_EVALUATION.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/SELF_EVALUATION.md) | **Cơ chế Tự Tối Ưu & Đánh giá (Self-Optimization)** | Check-list tiền kiểm, tiêu chí đo lường chất lượng, Runbook kiểm thử kỹ thuật (176/176 tests passed 100%) và KPI Release Gate lâm sàng. |
| [DDXPLUS_BENCHMARK_ANALYSIS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/DDXPLUS_BENCHMARK_ANALYSIS.md) | **Báo cáo Benchmark DDXPlus Toàn diện (Mila / NeurIPS)** | Quy trình trích xuất streaming, giải mã triệu chứng, chuẩn hóa Strict Blind v3.0, phân tích chi tiết Safety Engine v3 đạt 97.87% Safety Recall và tích hợp song ngữ EN-VI. |
| [IMPLEMENTATION_UPDATE_2026-09-29.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/IMPLEMENTATION_UPDATE_2026-09-29.md) | **Biên bản nâng cấp Hybrid/RAG 29-09-2026** | Trạng thái source sau khi nối RAG vào agent chính, bổ sung LLM fallback, fact-aware probing, action validation, lịch/slot an toàn và kết quả regression 168/168. |
| [IMPLEMENTATION_UPDATE_2026-09-30_HITL.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/IMPLEMENTATION_UPDATE_2026-09-30_HITL.md) | **Biên bản HITL & dữ liệu bác sĩ 30-09-2026** | Loại bỏ bác sĩ/slot giả, thêm form khách vãng lai, hàng đợi `PENDING_CONTACT`, quy tắc xác nhận sau khi ghi DB và trạng thái triển khai Supabase thực tế. |

---

## ⚡ HƯỚNG DẪN KÍCH HOẠT NHANH CHO AI AGENT (AGENT ONBOARDING)

Khi bắt đầu một phiên làm việc hoặc giải quyết tác vụ trong repo P-124, AI Agent phải thực hiện theo thứ tự ưu tiên sau:

1. **Bước 1 (Đọc Quy tắc an toàn):** Đọc kỹ [RULES.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/RULES.md) để đảm bảo không vi phạm an toàn y tế và không làm hỏng dữ liệu hệ thống.
2. **Bước 2 (Tra cứu Kỹ năng):** Sử dụng [SKILLS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/SKILLS.md) để nắm rõ logic vận hành của các dịch vụ nghiệp vụ (`triage_service`, `guardrail_service`, `probing_service`, `doctor_schedule_service`, `cache_service`).
3. **Bước 3 (Tham chiếu Mẫu chuẩn):** Tra cứu [FEW_SHOT_PROMPTS.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/FEW_SHOT_PROMPTS.md) trước khi sinh câu trả lời cho người dùng nhằm giữ đúng văn phong y khoa ấm áp, chuẩn mực.
4. **Bước 4 (Tiền kiểm tra):** Trước khi hoàn tất câu trả lời hoặc code commit, chạy checklist trong [SELF_EVALUATION.md](file:///d:/AI%20in%20Action/LogAgent/P-124/context_agent/SELF_EVALUATION.md).
