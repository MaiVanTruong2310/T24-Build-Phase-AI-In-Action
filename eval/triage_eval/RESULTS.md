# Kết quả triage eval — 10/10/2026

Báo cáo này ghi lại các số liệu đã kiểm chứng của bộ phân tầng cấp cứu (`ClinicalTriageService`) để dùng cho slide, báo cáo thực nghiệm và Demo Day. Mọi con số đều lấy từ báo cáo tự sinh trong `reports/triage_eval/` (tên file ghi ở mục Nguồn). Cách chạy và quy tắc xem `README.md`.

## Đọc nhanh

| Bộ test | Biến thể | Cỡ mẫu chính thức | Bắt ca cấp cứu | ATS đúng | Lệch ≤ 1 bậc | κ có trọng số | Báo động nhầm |
|---|---|---|---|---|---|---|---|
| ETEK test (bộ khóa, chạy 1 lần) | `patient` | 81 ca | **28/30 = 93,3%** (KTC 95%: 78,7–98,2) | 63,0% | 91,4% | 0,759 | 7/51 (13,7%) |
| ETEK test (bộ khóa, chạy 1 lần) | `full` | 94 ca | 26/41 = 63,4% (KTC 95%: 48,1–76,4) | 43,6% | 86,2% | 0,555 | 7/53 (13,2%) |
| ETEK dev (được chỉnh ngưỡng) | `patient` | 29 ca | 9/10 = 90,0% (KTC 95%: 59,6–98,2) | 62,1% | 93,1% | 0,768 | 4/19 (21,1%) |
| Bộ tự soạn (Được tham khảo) | — | 73 ca, chỉ tham khảo | 15/15 = 100% (KTC 95%: 79,6–100) | 79,5% | 98,6% | 0,855 | 2/58 (3,4%) |

"Báo động nhầm" là số ca có nhãn ATS 3–5 nhưng hệ thống lại báo cấp cứu, trên tổng số ca không cấp cứu.

## Hai biến thể ETEK — đừng so lẫn

Mỗi tình huống ETEK có hai cách viết:

- **`patient`**: bệnh nhân hoặc người nhà tự kể bằng lời thường, ví dụ "Bạn tôi vừa ly hôn, trầm cảm mấy tuần nay…". Đây là dạng chatbot thực sự nhận được, nên là **số chính** để báo cáo năng lực sản phẩm. Những ca cần số đo sinh hiệu (người bệnh không tự đo được) được tách thành ca tham khảo, không tính điểm chính thức: 13 ca ở test, 9 ca ở dev.
- **`full`**: mô tả lâm sàng ở ngôi thứ ba theo lời y tá phân loại, có sinh hiệu, ví dụ "Ông Fred 84 tuổi đến vì hồi hộp… mạch 142 lần/phút". Bộ phân tầng hiện chưa đọc tốt kiểu văn bản này, nên kết quả thấp hơn nhiều. Số này dùng để chỉ ra hướng cải thiện, không đại diện cho trải nghiệm người dùng.

Khi trình bày, hai hàng trong cùng một bảng phải cùng biến thể. Nếu muốn nêu cả số `full`, ghi rõ "mô tả lâm sàng của y tá".

## Chi tiết ETEK test (bộ khóa)

Chạy một lần lúc 02:11 ngày 10/10/2026 giờ Việt Nam (19:11 UTC ngày 09/10), dataset sha256 `04664a0cf903`, KB Supabase 741 bệnh. Không chỉnh luật hay ngưỡng dựa trên các ca trong bộ này.

Theo nhãn ATS của chuyên gia, biến thể `patient`:

| Nhãn | n | Bắt cấp cứu | ATS đúng |
|---|---|---|---|
| ATS 1 | 10 | 10/10 | 10/10 |
| ATS 2 | 20 | 18/20 | 15/20 |
| ATS 3 | 23 | — | 12/23 |
| ATS 4 | 22 | — | 14/22 |
| ATS 5 | 6 | — | 0/6 |

**Ca cấp cứu bị bỏ sót (`patient`).** Hai ca chính thức là ETEK-044 (loạn thần do ma túy đá kèm hành vi hung hăng) và ETEK-114 (nạn nhân bị cưỡng hiếp, hành hung, đang kích động). Tính thêm ca tham khảo thì có ETEK-096 (ngã từ độ cao 2 m). Nhóm yếu nhất là **sức khỏe tâm thần, hành vi kích động và chấn thương**.

**Ca cấp cứu bị bỏ sót (`full`, 15 ca).** Các ca rải ở tâm thần (044, 053, 101, 114), ngộ độc (070, 104), nhi khoa (074, 078), sản khoa (132), tim mạch (019, 064), chấn thương (096), phụ khoa (062) và ung bướu (117).

Điểm yếu chung của cả hai biến thể là ATS 5: hệ thống chưa phân biệt được ca rất nhẹ (0/6) mà thường xếp lên ATS 4. Hướng lệch này an toàn hơn xếp thấp, nhưng làm giảm số ca đúng ATS.

## Kiểm tra nhất quán (metamorphic)

Lần chạy mới nhất trên 111 ca (dev + etek_dev), không cần nhãn:

| Phép biến đổi | Số ca thay đổi |
|---|---|
| Bỏ dấu tiếng Việt làm **hạ** mức xử trí | 1/111 (ETEK-072) |
| Bỏ dấu làm đổi ATS nhưng cùng mức xử trí | 2/111 |
| Thêm câu không liên quan làm đổi ATS | 0/111 |
| Đảo thứ tự câu làm đổi mức xử trí | 1/111 |
| Thêm dấu hiệu nguy kịch mà **không** lên cấp cứu | **0/111** |

## Lưu ý khi dùng số liệu

1. **Thời điểm code khác nhau.** Số ETEK test đo trên code lúc 02:11 ngày 10/10. Số ETEK dev, bộ tự soạn và metamorphic đo trên code chiều 10/10, sau các bản sửa an toàn tự hại/quá liều, xử lý gõ không dấu và mức khẩn của bệnh khớp lỏng. Muốn số ETEK test theo code hiện tại thì phải chạy lại bộ khóa (`--confirm-test`, một lần) và không chỉnh luật theo kết quả đó.
2. **Cỡ mẫu nhỏ.** Mọi bộ đều dưới 100 ca chính thức, nên khoảng tin cậy rất rộng (xem cột KTC 95%).
3. **ETEK dev giảm κ có chủ đích.** κ của ETEK dev giảm từ 0,812 xuống 0,768 vì quyết định an toàn: ý định tự sát được xếp cấp cứu, trong khi nhãn ETEK là ATS 3 (ETEK-072). Đây là đánh đổi nhóm cần thống nhất.
4. **Bộ tự soạn chỉ để tham khảo.** Nhãn do AI soạn (`draft_unreviewed`), chưa có chuyên gia duyệt, nên không dùng làm số chính thức.
5. **Bản dịch do AI.** ETEK là nhãn của chuyên gia, nhưng bản tiếng Việt do AI dịch; chất lượng bản dịch có thể ảnh hưởng kết quả.

## Nguồn

Các file trong `reports/triage_eval/` (máy chạy eval, chưa đưa vào git):

| Hàng | File báo cáo |
|---|---|
| ETEK test `patient` | `etek_test_patient_20261010_021132.md` / `.json` |
| ETEK test `full` | `etek_test_full_20261010_021137.md` / `.json` |
| ETEK dev `patient` | `etek_dev_patient_20261010_152216.md` / `.json` |
| Bộ tự soạn | `dev_patient_20261010_152213.md` / `.json` |

ETEK: based on Commonwealth of Australia (Department of Health and Aged Care) material, ETEK 2nd ed., CC BY 4.0 — 132 tình huống (38 dev, 94 test), nhãn ATS của chuyên gia, bản tiếng Việt do AI dịch.
