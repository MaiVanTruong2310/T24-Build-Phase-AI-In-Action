# Triage eval khách quan

Chạy tất định, không gọi LLM, đo `ClinicalTriageService` (cổng cấp cứu + chọn chuyên khoa).

Kết quả đã kiểm chứng (dùng cho slide/báo cáo): xem [RESULTS.md](RESULTS.md).

## Quy tắc để kết quả đáng tin
1. **dev** được xem và chỉnh ngưỡng; **test** khóa, chỉ chạy trước release (`--confirm-test`). Không sửa luật/ngưỡng dựa trên ca trong test.
2. Nhãn (`gold_ats`, `gold_specialty`) do người có chuyên môn gán **trước khi xem output hệ thống**. Ghi tên vào `annotator`, đổi `label_status` thành `reviewed`. 2 người gán thì ghi thêm `annotator2` và tính Cohen's κ.
3. Ca `draft_unreviewed` (hiện là 25 ca do AI soạn) chỉ để thử runner; báo cáo tách riêng, không tính điểm chính thức.
4. Nguồn ca mới: mô tả triệu chứng ẩn danh từ log chat (có đồng ý), kịch bản y khoa công khai, lỗi thực đã gặp. Không sinh bằng code của hệ thống.
5. Mục tiêu cỡ mẫu: ≥300 ca (≥60 ATS 1-2), chia ~70% dev / 30% test, phủ: không dấu, viết tắt, nhiều triệu chứng, phủ định, mơ hồ.
6. `gold_specialty` dùng tên hệ thống phát ra (xem `--list-codes`) hoặc mã có trong `SPECIALTY_ALIASES` của `run_eval.py`; `null` = không chấm chuyên khoa.
7. Luật được nạp từ Supabase (`disease_triage`) hoặc file cục bộ khi offline, nên kết quả chỉ so sánh được khi cùng dòng `KB:` (nguồn/số bệnh/hash) trong báo cáo.
8. Stratum `trap_false_alarm` (câu thường chứa từ dễ gây báo động nhầm) và `emergency_obstetric`/`pregnancy_routine` canh hai lỗi đã gặp: cờ đỏ rác từ DB và bỏ sót cấp cứu sản khoa.
9. Quy ước mức xử trí của sản phẩm (đặt lịch, không phải phân loại trong khoa cấp cứu): ATS 1-2 = cấp cứu (115 / đến viện ngay), ATS 3 = ưu tiên khám trong ngày, ATS 4 = đặt lịch trong tuần, ATS 5 = linh hoạt. Nhãn ETEK theo nghĩa thời gian chờ trong khoa cấp cứu (ATS 3 = 30 phút); eval quy về 3 mức xử trí trên (`under/over_triage_disposition`).
10. ETEK (`--split etek_dev|etek_test`, `--variant patient|full`): 132 tình huống ETEK 2nd ed., based on Commonwealth of Australia (Department of Health and Aged Care) material, CC BY 4.0. Nhãn ATS của chuyên gia, bản tiếng Việt do AI dịch. `etek_test` khóa, chạy kèm `--confirm-test`.
11. `python eval/triage_eval/metamorphic.py`: kiểm tra nhất quán không cần nhãn (bỏ dấu, thêm câu thừa, đảo thứ tự, thêm dấu hiệu nguy kịch) trên dev + etek_dev.

## Tiêu chí chấp nhận khi sửa luật lâm sàng
Thứ tự ưu tiên: bỏ sót cấp cứu > hạ mức xử trí > báo động nhầm > lệch ATS. Một thay đổi chỉ được merge khi đạt **tất cả**:
1. `emergency_recall` = 100% trên `dev` và `etek_dev` (cả phần chính thức lẫn tham khảo), không thấp hơn trước khi sửa.
2. `under_triage_disposition` không tăng trên `dev` và `etek_dev`.
3. `metamorphic.py`: không thêm ca R1 "HẠ mức xử trí" hay R4 (thay đổi phải để số ca này giữ nguyên hoặc giảm).
4. `pytest tests/ -m "not integration"` xanh; mỗi luật mới/sửa có test hồi quy **2 chiều** (ca phải bắt + ca giống mà không được bắt).
5. Luật bám mô tả ATS/ACEM, ghi `rule_id`, lý do và nguồn trong comment; không viết luật riêng cho câu chữ của một ca dev.
6. Thay đổi **hạ mức** (ATS khẩn hơn → ít khẩn hơn) hoặc đổi ngưỡng có tác động chính sách (ví dụ đau 8/10 → ATS 2 = khóa đặt lịch, gọi 115) phải có **bác sĩ/điều dưỡng triage duyệt** trước khi merge, và giữ lưới an toàn (nhắc gọi 115 khi xấu đi, chuyển điều phối viên).
7. `etek_test`/`test` chỉ chạy lại ở mốc release, ghi rõ số lần đã chạy và các thay đổi kể từ lần trước.

Lưu ý thống kê: CI95 của recall còn rộng khi số ca cấp cứu nhỏ (0 ca bỏ sót trên n ca → cận dưới ≈ 1 − 3/n); cần ≥60 ca ATS 1-2 mới khẳng định được recall > 95%.

## Cách chạy
    python eval/triage_eval/run_eval.py --split dev
Báo cáo `.md` + `.json` ghi vào `reports/triage_eval/` kèm git sha và hash dataset. Exit code 1 nếu bỏ sót bất kỳ ca cấp cứu đã duyệt.
