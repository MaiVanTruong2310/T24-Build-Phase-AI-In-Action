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

## Cách chạy
    python eval/triage_eval/run_eval.py --split dev
Báo cáo `.md` + `.json` ghi vào `reports/triage_eval/` kèm git sha và hash dataset. Exit code 1 nếu bỏ sót bất kỳ ca cấp cứu đã duyệt.
