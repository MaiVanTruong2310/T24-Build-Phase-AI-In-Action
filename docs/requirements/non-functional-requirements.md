# Yêu cầu phi chức năng (Non-Functional Requirements) — VCare+ (P-124)

> Mô tả **hệ thống phải tốt đến mức nào**. Mỗi yêu cầu có chỉ tiêu đo được và số liệu thực đo.
>
> **Nguồn số liệu:**
> - [`EVAL_EVIDENCES.md`](../../EVAL_EVIDENCES.md): 5 ca kiểm thử chạy trên pipeline thật (06/10/2026).
> - [`reports/eval_info.md`](../../reports/eval_info.md): benchmark 10 câu, provider DeepSeek (07/10/2026).
> - `eval/results/*.json`: benchmark 10 / 10 / 20 ca.
> - Cấu hình mặc định trong `src/config.py`, `src/medical_assistant/config.py`.
> - Kết quả `pytest tests/` trên develop `42c909e` (10/10/2026): 749 pass, 5 fail, 18 skip.
>
> **Đánh giá:** ✅ Đạt · ⚠️ Chưa đạt · 📏 Chưa đo đủ
>
> **Về chỉ tiêu:** Safety recall = 100%, Route ≥ 90%, Tool-call ≥ 85%, Grounded ≥ 85%, Hallucination = 0% lấy từ bảng chuẩn trong `reports/eval_info.md`. Các chỉ tiêu còn lại (độ trễ, chi phí, bảo mật…) là **mục tiêu nhóm đề xuất** cho bản demo; nhóm có thể điều chỉnh.
>
> ⚠️ **Giới hạn số liệu:** các bộ đánh giá hiện chỉ có 5–20 ca. Theo chính báo cáo `eval_info.md`, cỡ mẫu dưới 50 câu **chưa đủ ý nghĩa thống kê**. Các con số dưới đây là kết quả kiểm định sơ bộ, cần chạy lại với ≥ 50 câu.

---

## 1. An toàn lâm sàng

| Mã | Yêu cầu | Chỉ tiêu | Thực đo | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-01 | Không bỏ sót ca cấp cứu | Safety recall **= 100%** | 100% (2/2 câu red flag); thử trực tiếp 6/6 ca cấp cứu được bắt | `eval_info.md` §2; thử agent 10/10 | ✅ (mẫu nhỏ) |
| NFR-02 | Cảnh báo cấp cứu không phụ thuộc LLM | 0 token LLM cho ca cấp cứu | 0 token (TC-03 tiết kiệm 398 token) | `EVAL_EVIDENCES.md` TC-03 | ✅ |
| NFR-03 | Không bịa thông tin (tên bác sĩ, cơ sở, SĐT, giá, địa chỉ) | Hallucination rate **= 0%** | 0% trên 32 thực thể của 6 loại | `eval_info.md` §3 | ✅ |
| NFR-04 | Câu trả lời có căn cứ dữ liệu | Grounded rate ≥ 85% | 100% | `eval_info.md` §2 | ✅ |
| NFR-05 | Định tuyến đúng chuyên khoa | Route accuracy ≥ 90% | 100% (10 câu); 20/20 ca benchmark đa chuyên khoa | `eval_info.md` §2; `multi_specialty_pipeline_benchmark_20_cases.json` | ✅ |
| NFR-06 | Agent gọi đúng công cụ tra cứu | Tool-call accuracy ≥ 85% | **80%** (2 ca tra cứu chuyên khoa / kiến thức bệnh không gọi tool) | `eval_info.md` §2, §6 | ⚠️ |
| NFR-07 | Thông tin hiển thị trong cảnh báo cấp cứu phải chính xác | 0 nhãn bệnh sai | 2 nhãn sai: trẻ sốt co giật → "Hội chứng Sheehan"; ý định tự tử → "Ngộ độc cấp" | Thử agent trên develop `42c909e` | ⚠️ |

## 2. Hiệu năng (độ trễ)

| Mã | Yêu cầu | Chỉ tiêu | Thực đo | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-08 | Độ trễ trung bình một lượt chat | ≤ 8 s | 4,6 s / 6,8 s / 7,5 s (3 bộ benchmark) | `eval/results/*.json` (`avg_latency_ms`) | ✅ |
| NFR-09 | Độ trễ p50 | ≤ 8 s | **9,3 s** | `eval_info.md` §2 | ⚠️ |
| NFR-10 | Độ trễ p95 | ≤ 20 s | **26,4 s** | `eval_info.md` §2 | ⚠️ |
| NFR-11 | Cảnh báo cấp cứu phải hiển thị gần như tức thì | ≤ 2 s | **7,9 s** (TC-03); 14,8 s (nhóm `emergency_red_flag`) | `EVAL_EVIDENCES.md` TC-03; `eval_info.md` §4 | ⚠️ |
| NFR-12 | Chặn nội dung tấn công nhanh | ≤ 2 s | 1,75 s (TC-02) | `EVAL_EVIDENCES.md` TC-02 | ✅ |
| NFR-13 | Người dùng không thấy màn hình trống khi chờ | Gửi tín hiệu duy trì kết nối SSE | Gửi `keep-alive` mỗi 5 s khi agent đang xử lý | `src/medical_assistant/api/routes.py` | ✅ |
| NFR-14 | Giới hạn thời gian gọi LLM | Mỗi request ≤ 20 s, tổng ≤ 25 s | Cấu hình `llm_request_timeout_seconds=20`, `llm_total_timeout_seconds=25` | `src/medical_assistant/config.py` | ✅ |

## 3. Chi phí LLM

| Mã | Yêu cầu | Chỉ tiêu | Thực đo | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-15 | Chi phí LLM mỗi lượt tư vấn | ≤ 10 VNĐ/lượt | 7,09 – 8,23 VNĐ/lượt (536 – 754 token) | `EVAL_EVIDENCES.md` TC-01, TC-04, TC-05 | ✅ |
| NFR-16 | Chi phí trung bình theo benchmark | ≤ 0,001 USD/ca | 0,00024 USD/ca (0,004771 USD / 20 ca); 0,00008 – 0,00006 USD/ca ở 2 bộ 10 ca | `eval/results/*.json` (`total_cost_usd`) | ✅ |
| NFR-17 | Không tốn token cho câu hỏi có thể trả lời bằng luật | 0 token cho ca cấp cứu, tấn công, câu hỏi thường gặp | 0 token (TC-02, TC-03); có cache FAQ | `EVAL_EVIDENCES.md`; `cache_service.py` | ✅ |

## 4. Bảo mật & dữ liệu cá nhân (PII/PHI)

| Mã | Yêu cầu | Chỉ tiêu | Thực tế trong hệ thống | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-18 | Mật khẩu không lưu dạng đọc được | Băm có salt bằng thuật toán chậm | `scrypt` có salt | `src/core/security.py` | ✅ |
| NFR-19 | Token đăng nhập có thời hạn ngắn | Access token ≤ 1 giờ | Access token theo `expires_in` của Supabase Auth (mặc định 3600 s); refresh 30 ngày, xoay vòng mỗi lần làm mới | `src/services/cookie_session.py`, Supabase Auth | ✅ |
| NFR-20 | Cookie phiên không bị JavaScript đọc trộm | `HttpOnly`; `Secure` trên production | `httponly=True`, `secure` bật khi `APP_ENV=production`; từ chối cấu hình `SameSite=None` mà không `Secure` | `src/services/cookie_session.py` | ✅ |
| NFR-21 | Chống giả mạo request (CSRF) cho cookie | Request ghi dữ liệu phải có `Origin` hợp lệ | `CookieOriginMiddleware` trả 403 nếu Origin lạ | `src/services/cookie_session.py`, `src/main.py` | ✅ |
| NFR-22 | Phân quyền theo vai trò | 100% API `/staff/*` yêu cầu quyền staff | Mọi route `/staff/*` dùng `require_staff` hoặc `require_coordination_admin`; có test 401/403 | `src/api/endpoints/*.py`, `tests/test_api/` | ✅ |
| NFR-23 | Che thông tin cá nhân trước khi gửi LLM | SĐT, CCCD… được che trước khi gửi nhà cung cấp LLM | **Chưa có**: Presidio + DLP chỉ chạy trên câu trả lời đầu ra (`respond_node.py:1109-1126`); tin nhắn bệnh nhân gửi nguyên văn cho LLM | `src/medical_assistant/agent/nodes/respond_node.py` | ⚠️ |
| NFR-24 | Chặn tấn công vào agent | 100% câu tấn công trong bộ test bị chặn | TC-02 (jailbreak + đòi ma túy) bị chặn; nhóm test bảo mật pass | `EVAL_EVIDENCES.md` TC-02; `tests/test_medical_assistant/test_security_*` | ✅ (mẫu nhỏ) |
| NFR-25 | Không lưu bí mật trong mã nguồn | 0 API key / mật khẩu trong repo | `.env` bị git bỏ qua; `.env.example` chỉ có giá trị trống | `.gitignore`, `.env.example` | ✅ |
| NFR-26 | OTP xác minh phải gửi thật | Mã xác nhận gửi qua kênh thật, không trả mã trong response | Mã xác nhận gửi qua email bởi Supabase Auth; API không bao giờ trả mã OTP (`otp: null`). Biến `MOCK_OTP_CODE` còn trong `ci_cd.yml` nhưng code không dùng | `src/api/endpoints/auth.py`, `src/services/supabase_auth.py` | ✅ |

## 5. Khả dụng & độ tin cậy

| Mã | Yêu cầu | Chỉ tiêu | Thực tế trong hệ thống | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-27 | Không gián đoạn khi một nhà cung cấp LLM lỗi | Tự chuyển sang nhà cung cấp dự phòng | Chuỗi dự phòng OpenRouter → Gemini → OpenAI/DeepSeek; tạm ngắt provider lỗi 30 s | `src/medical_assistant/infrastructure/llm.py`; `llm_failure_cooldown_seconds=30` | ✅ |
| NFR-28 | Có câu trả lời an toàn khi LLM không phản hồi | Fallback bằng luật thay vì báo lỗi | Fallback rate 40% trên bộ 10 câu, nghĩa là 4/10 câu phải dùng câu trả lời dự phòng | `eval_info.md` §2 | ⚠️ Tỷ lệ cao |
| NFR-29 | Kiểm tra sức khỏe dịch vụ | Có endpoint health và readiness | `/health`, `/health/ready` (kiểm tra kết nối DB) | `src/main.py` | ✅ |
| NFR-30 | Ngữ cảnh chat không mất khi khởi động lại | Người đã đăng nhập khôi phục được hội thoại | State được lưu vào `chat_conversations.checkpoint` | `src/services/chat_history.py` | ✅ (khách vẫn mất) |
| NFR-31 | Thông báo không bị mất khi gửi lỗi | Thử lại có giới hạn | Tối đa 5 lần, timeout xử lý 300 s | `src/config.py` (`notification_max_attempts`, `notification_processing_timeout_seconds`) | ✅ |
| NFR-32 | Theo dõi vận hành | Có log, metric, trace tập trung | Grafana, Loki, Tempo, Prometheus | `observability/`, `docker-compose.observability.yml` | ✅ |

## 6. Khả năng bảo trì & kiểm thử

| Mã | Yêu cầu | Chỉ tiêu | Thực đo | Nguồn | Đánh giá |
|---|---|---|---|---|---|
| NFR-33 | Bộ test tự động phải pass | ≥ 99% test pass | 749/754 = **99,3%** (5 fail) | `pytest tests/` trên develop `42c909e` | ✅ |
| NFR-34 | Bộ đánh giá AI đủ lớn để có ý nghĩa thống kê | ≥ 50 câu | 10 – 20 câu | `eval_info.md` (cảnh báo cỡ mẫu) | ⚠️ |
| NFR-35 | Code tuân thủ chuẩn lint | 0 lỗi `ruff` | 📏 Chưa đo trên develop mới nhất (bản 06/10 có 140 lỗi) | — | 📏 |

---

## Tổng hợp

| Nhóm | ✅ Đạt | ⚠️ Chưa đạt | 📏 Chưa đo |
|---|---|---|---|
| An toàn lâm sàng | 5 | 2 | 0 |
| Hiệu năng | 4 | 3 | 0 |
| Chi phí | 3 | 0 | 0 |
| Bảo mật | 8 | 1 | 0 |
| Khả dụng | 5 | 1 | 0 |
| Bảo trì & kiểm thử | 1 | 1 | 1 |
| **Tổng (35)** | **26** | **8** | **1** |

## Ưu tiên cải thiện

1. **NFR-11: cảnh báo cấp cứu mất 7,9–14,8 s** dù không gọi LLM. Cần tìm phần nào chậm (khởi tạo, truy vấn DB, ghi lịch sử) và trả cảnh báo ngay khi luật cấp cứu khớp. Đây là yêu cầu an toàn quan trọng nhất về tốc độ.
2. **NFR-07: nhãn bệnh sai trong cảnh báo cấp cứu.**
3. **NFR-34: mở rộng bộ đánh giá lên ≥ 50 câu**, rồi đo lại toàn bộ chỉ số ở mục 1–3.
4. **NFR-06, NFR-28: tool-call 80% và fallback 40%.** Hai ca lỗi đều là tra cứu bị quá thời gian và rơi vào câu trả lời dự phòng.
5. **NFR-09, NFR-10: p50 9,3 s, p95 26,4 s**, vượt mục tiêu.
6. **NFR-23: che PII trong tin nhắn trước khi gửi LLM** bên ngoài (hiện chỉ che ở đầu ra).
