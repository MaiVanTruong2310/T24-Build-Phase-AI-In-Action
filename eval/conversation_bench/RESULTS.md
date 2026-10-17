# Kết quả benchmark VCare+ (13–14/10/2026)

Số liệu đo trên nhánh `feature/triage-compliance-presentation` trong đợt làm GĐ0–GĐ2 (khớp luật cấp cứu có dấu),
câu quá ngắn (bác sĩ duyệt mục 9), định tuyến chuyên khoa và kênh Zalo. Mọi tỉ lệ kèm khoảng tin cậy 95% Wilson
trong báo cáo chi tiết; ở đây làm tròn để đọc nhanh.

Hai loại lượt chạy, đọc khác nhau:

| Chế độ | Ý nghĩa | Dùng để |
|---|---|---|
| **Offline** (LLM tắt) | Chỉ luật tất định + luồng dự phòng. Miễn phí, chạy lại cùng code ra cùng kết quả | So **trước/sau** khi sửa code, kiểm tra tầng an toàn khi LLM sập |
| **Live** (LLM thật, DeepSeek qua OpenRouter) | Đúng như production | Ước lượng **chất lượng thực tế** khi người dùng chat |

Kết quả offline **thấp hơn thực tế** ở mọi phần phụ thuộc LLM (chuyên khoa, ATS, trạng thái luồng, nhận yêu cầu
"gặp người thật").

## 1. Bộ dữ liệu

| Bộ | Số ca | Nguồn |
|---|---|---|
| Conversation bench, split `dev` | 4.741 (357 gốc + 4.384 biến thể) | `seeds/*.jsonl` + biến thể tất định + `generated/paraphrase.jsonl` |
| Conversation bench, split `test` (bộ khóa) | 2.044 (150 gốc + 1.894 biến thể) | như trên; chỉ chạy ở mốc phát hành, không dùng để chỉnh code |
| Kỳ vọng trong bench | 6.970 compliance · 5.429 emergency · 1.865 nhắc 115 · 1.785 trạng thái · 1.570 ATS · 1.568 nội dung · **1.429 chuyên khoa** · 33 xưng hô | `expectations` |
| `eval/triage_eval` dev / etek_dev | 73 / 29 (+9 tham khảo) | ca có nhãn chuyên gia (ETEK 2nd ed., CC BY 4.0) |
| Luật lâm sàng cứng (`eval/compliance_eval`) | 131 | dev + etek_dev + adversarial |
| Metamorphic | 111 ca × 4 phép biến đổi | bỏ dấu, thêm câu nhiễu, đảo thứ tự, thêm dấu hiệu nguy kịch |

Biến thể: bỏ dấu (`no_diacritics`), dấu nửa vời (`partial_accent`), gõ sai (`typos`), viết hoa (`upper`), văn nói
(`voice`), ký tự ẩn (`zero_width`), ký tự giả dạng (`homoglyph`), chen từ đệm (`filler_gap`), diễn đạt lại bằng
LLM có chấm duyệt (`paraphrase`).

## 2. Code cũ → code mới (offline)

| Chỉ số | Code cũ | Code mới |
|---|---|---|
| Ca dev đạt toàn bộ (385 ca có ở cả hai lượt) | 73,5% | **75,1%** |
| Cấp cứu code cũ bắt mà code mới bỏ sót | – | **0** |
| Câu có dấu bình thường bị báo cấp cứu nhầm (ATS 1–2) | 362 | **57** |
| Câu bình thường bị báo cấp cứu nhầm (ATS 1–2) | 448 | **141** |
| Bộ âm tính: ATS 1–2 nhầm / ATS 3 nhầm | – | **0/107** / 2/107 (1,9%, mục tiêu ≤ 1%) |
| pytest (không tính `integration`) | 1.014 đạt | **1.297 đạt / 0 lỗi** (sau khi gộp develop) |

## 3. Eval bắt buộc trên code cuối (offline)

| Chỉ số | dev | etek_dev |
|---|---|---|
| Bắt cấp cứu (emergency recall) | **15/15** | **10/10** |
| Báo cấp cứu thừa | 2/58 = 3,4% | 4/19 = 21,1% |
| Đúng chính xác ATS | 58/73 = 79,5% | 21/29 = 72,4% |
| Hạ mức xử trí sai (nguy hiểm) | 5/73 = 6,8% | 0/29 |
| Kappa có trọng số | 0,855 | 0,807 |
| Chuyên khoa top-1 / đa chuyên khoa đủ | 7/7 / 17/17 | – |

| Luật lâm sàng cứng (131 ca) | Đạt |
|---|---|
| R1 cấp cứu có hướng dẫn gọi 115 | 44/44 |
| R2 không chẩn đoán xác định | 131/131 |
| R3 không kê đơn/liều thuốc | 131/131 |
| R4 tối đa 1 câu hỏi mỗi lượt | 131/131 |
| R5 cấp cứu không mời đặt lịch | 44/44 |

| Metamorphic (111 ca) | Kết quả |
|---|---|
| Bỏ dấu làm HẠ mức xử trí | 1/111 (ETEK-072, có từ trước) |
| Thêm câu không liên quan làm đổi ATS | 0/111 |
| Đảo thứ tự làm đổi mức xử trí | 1/111 |
| Thêm dấu hiệu nguy kịch mà KHÔNG lên cấp cứu | **0/111** |

## 4. Toàn bộ conversation bench

| Kỳ vọng | Offline dev 4.741 ca | Offline test 2.044 ca ¹ | **Live 1.039 ca** ² |
|---|---|---|---|
| Ca đạt toàn bộ | 62,8% | 62,3% | 56,6% |
| Trượt kỳ vọng nghiêm trọng | 7,9% | 6,8% | **0,1%** |
| Luật lâm sàng (compliance) | 100% | 99,9% | 98,9% |
| Cấp cứu | 91,8% | 93,2% | **98,8%** |
| Trạng thái luồng | 82,0% | 73,7% | **94,0%** |
| Nội dung trả lời | 84,2% | 78,0% | **97,6%** |
| **Chuyên khoa** | 55,5% | 57,7% | **63,1%** |
| Mức ATS | 41,6% | 36,0% | 72,0% |
| Xưng hô | 100% | – | 100% |

¹ Split test chạy một lần trên code trước các sửa cuối (sàn chứng cứ, ngữ cảnh nhiều lượt, Zalo), không chỉnh code
theo kết quả bộ này. ² Live: chọn các ca có kỳ vọng chuyên khoa + HITL và biến thể gõ của chúng.

Nhóm cấp cứu (1.306 ca, offline) trên code cuối: 74,2% đạt toàn bộ; so với lượt dev đầu tiên cùng code mới +31 ca.

### Đúng chuyên khoa theo cách gõ (live)

| Cách gõ | Đúng khoa |
|---|---|
| Văn nói | 72,3% |
| Viết hoa | 71,1% |
| Gõ sai chính tả | 69,8% |
| Ký tự ẩn | 69,1% |
| Câu gốc có dấu | 67,5% |
| Ký tự giả dạng | 67,5% |
| Diễn đạt lại | 64,0% |
| Dấu nửa vời | 58,5% |
| **Không dấu** | **45,8%** |
| Chen từ đệm | 42,4% |

### Cổng cấp cứu bắt được theo cách gõ (offline, tầng tất định)

| Cách gõ | Bắt được |
|---|---|
| Câu gốc / viết hoa | 86,2% |
| Không dấu / ký tự ẩn / ký tự giả dạng | 86,0% |
| Văn nói | 84,1% |
| Dấu nửa vời | 82,5% |
| Chen từ đệm | 75,0% |
| Diễn đạt lại | 74,3% |
| Gõ sai chính tả | 69,0% |

Khoảng 14% ca trượt ngay ở câu gốc là do bộ luật **thiếu từ vựng** (ví dụ "uống thuốc trừ sâu", "bị đâm vào bụng"),
không do dấu; ở chế độ live, LLM bù lại phần lớn (cấp cứu 98,8%).

## 5. Độ trễ và chi phí (live)

| Loại tin nhắn | Độ trễ trung vị |
|---|---|
| Cấp cứu rõ ràng (cổng zero-token) | ~7 ms |
| Câu quá ngắn ("khó thở", "co giật") → hỏi mức độ | ~6 ms |
| Khớp mơ hồ do thiếu dấu, câu lành tính | ~4,5 s (lượt thường ~2,8 s + 1,4–1,6 s khôi phục dấu bằng LLM) |

| Toàn lượt live 1.039 ca | Giá trị |
|---|---|
| Độ trễ p50 / p90 / p95 / p99 / max | 2,9 s / 4,2 s / 4,9 s / 7,2 s / 12,8 s |
| Lời gọi LLM | 2.191 |
| Token vào / ra | 11,98 triệu / 0,84 triệu |
| Chi phí | 0,73 USD tổng · **0,70 USD / 1.000 hội thoại** |

## 6. Tồn tại đã biết (ưu tiên cho bước sau)

1. **Chuyên khoa khi gõ không dấu** (45,8%) và lỗi rơi về "Sức khỏe tổng quát" khi triệu chứng rõ (xương khớp,
   hô hấp, mắt, nhi, sản phụ khoa); bệnh thần kinh do đái tháo đường bị đưa sang Xương khớp.
2. Khi bật LLM: 27 lượt hỏi > 1 câu; 14/2.130 lượt trả lời bằng tiếng Anh (một nửa là câu không dấu).
3. Offline không nhận ra yêu cầu "muốn gặp người thật" (nhóm HITL 0% offline, 53% live).
4. Chờ bác sĩ duyệt: co giật cục bộ (mí mắt, bắp chân) đang bị báo cấp cứu; luật dấu hiệu màng não
   ("cổ cứng", "không cúi đầu được").

## Tái lập

```bash
python eval/conversation_bench/build_db.py                       # dựng bench.db từ seeds + biến thể
python eval/conversation_bench/run_bench.py --split dev          # offline, ghi results.db
RUN_LIVE_LLM=1 python eval/conversation_bench/run_bench.py --split dev --category routing --live
python eval/conversation_bench/accent_baseline.py --compare      # so với reports/accent_baseline/FROZEN_BASELINE.json
python eval/triage_eval/run_eval.py --split dev && python eval/triage_eval/run_eval.py --split etek_dev
python eval/triage_eval/metamorphic.py && python eval/compliance_eval/run_compliance.py
```

`bench.db`, `results.db`, báo cáo theo lượt (`reports/*/<thời điểm>/`) là **kết quả sinh ra khi chạy**, không commit
(xem `.gitignore`).
