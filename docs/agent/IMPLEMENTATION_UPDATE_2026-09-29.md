# Biên bản nâng cấp Hybrid LLM + Rule + RAG — 29/09/2026

## Trạng thái đã triển khai

- Agent FastAPI/LangGraph tại cổng 8001 đã dùng RAG chuyên khoa trong nhánh `DEPARTMENT_INFO`; phản hồi chỉ sử dụng passage đúng tên chuyên khoa, có URL nguồn và không tự gắn nhãn “mũi nhọn/đứng đầu” khi kho dữ liệu không chứng minh.
- Câu hỏi so sánh với bệnh viện khác được nhận diện riêng. Nếu thiếu dữ liệu đối chiếu đồng nhất, agent nói rõ giới hạn rồi trình bày thông tin nội bộ đã truy xuất thay vì quảng cáo không có căn cứ.
- Hybrid Dialogue v2 được cấp `specialty_catalog`, `fact_catalog`, thời gian, probing budget và state giới hạn. Lượt triệu chứng tự nhiên vẫn gọi LLM structured output; FAQ/điều hướng/lịch/khoa có intent chắc chắn đi fast path để tiết kiệm chi phí.
- Khi LLM hoặc cả provider mất kết nối, agent dùng fallback bảo thủ, không trả HTTP 500. Telemetry phân biệt `llm_or_estimated`, `llm_fallback_rule` và `deterministic_rule`; fallback không bị báo nhầm là token LLM thực dùng.
- Rule fact extraction và LLM facts được merge; giữ thêm `location`, `severity`, `pain_severity_0_10`, `onset`, `qualifiers`, observation và correction. Cây hỏi bệnh bỏ qua vị trí/chi tiết người dùng đã nói.
- Action được backend kiểm tra trước khi thực thi. `request_safety_review`, yêu cầu người thật, đổi ngôn ngữ và out-of-scope có trạng thái/renderer riêng, không rơi mặc định sang tìm bác sĩ.
- Tên hiển thị chuyên khoa được tách khỏi mã chuẩn (`suggested_department_name` và `suggested_department_code`), tránh truyền `TIEU_HOA` trực tiếp sang UI hoặc làm lịch không khớp alias.
- Tìm lịch giữ đúng khoa của phiên, lọc buổi sáng/chiều, dùng mã slot ổn định qua lần khởi động và không tự thêm “10 năm kinh nghiệm” khi dữ liệu thiếu.
- Chỉ chấp nhận giữ slot đã được hiển thị trong phiên. Slot demo dùng khóa trong tiến trình và TTL 15 phút; đây chưa phải khóa phân tán/ACID cho nhiều worker, production vẫn cần Supabase RPC hoặc transaction có điều kiện.
- Renderer lịch đã đổi chuỗi `\\n` thành newline thật, không còn hiển thị dấu gạch chéo trong giao diện.
- DLP ghi telemetry `dlp_leakage_detected`; nhánh prompt injection, FAQ và fast path giữ số token LLM bằng 0 đúng bản chất.

## Kiểm thử xác minh

- Toàn bộ regression suite: **168/168 passed**.
- Bổ sung test cho: so sánh chuyên khoa có nguồn, yêu cầu thông tin chi tiết, alias `TIEU_HOA`, lọc lịch theo buổi, mã slot giả, LLM mất kết nối và hội thoại ba lượt triệu chứng → so sánh → thông tin khoa.
- Smoke test API thật tại `POST /api/v1/chat`: đau bụng bên trái không còn hỏi lại vị trí; hai lượt hỏi khoa Tiêu hóa trả dữ liệu RAG kèm nguồn Vinmec.

## Dọn source

Đã xóa hai module mẫu không có import, route hoặc test phụ thuộc:

- `src/medical_assistant/agent/tools/example_tool.py`
- `src/medical_assistant/domain/mock_medical_data.py`

Không xóa `web/app.py`, `web/templates/index.html`, `web/static/chat.js` vì legacy RAG Flask app và unit test vẫn tham chiếu. Không xóa `llm_clinical_extractor.py` vì test và tài liệu hiện tại vẫn dùng.

## Giới hạn còn lại

- `token_usage` ở lượt LLM thành công hiện là ước tính tokenizer, chưa phải usage do provider trả về. Không dùng chỉ số này làm hóa đơn.
- Lịch curated là dữ liệu demo. Muốn xác nhận đặt lịch thật qua nhiều process phải triển khai transaction/RPC tại database, TTL và idempotency key.
- RAG hiện dùng SQLite FTS và lọc exact-title cho thông tin khoa; chưa có reranker semantic cho các câu hỏi chéo nhiều chuyên khoa.
- Kết quả unit/regression không thay thế nghiệm thu lâm sàng hoặc benchmark blind mới.

Tài liệu này không chứa và không được bổ sung API key, token hoặc bí mật môi trường.
