# Evaluation Suite & Benchmarks

Thư mục này chứa toàn bộ công cụ, kịch bản benchmark và kết quả đánh giá chất lượng của **VCare Medical Assistant**.

---

## 1. Cấu trúc thư mục

- `results/`: Kết quả benchmark chi tiết dưới dạng JSON và báo cáo tổng hợp `report.md`.
  - `realistic_benchmark_10_cases.json`: Đánh giá 10 ca lâm sàng đời thực (triệu chứng cấp tính, mãn tính, câu hỏi thuốc, câu hỏi chi phí).
  - `advanced_benchmark_10_cases.json`: Đánh giá các trường hợp biên (nhiều triệu chứng phức tạp, phủ định triệu chứng, chuyển đổi ngôn ngữ Anh-Việt).
  - `multi_specialty_pipeline_benchmark_20_cases.json`: Đánh giá phân luồng đa chuyên khoa (Cardiology, Pediatrics, Dermatology, Gastroenterology...).
  - `report.md`: Báo cáo chỉ số KPI định lượng phục vụ Demo Day.
- `run_realistic_benchmark.py`: Script chạy benchmark 10 ca thực tế.
- `run_advanced_benchmark.py`: Script chạy benchmark 10 ca nâng cao.
- `run_multi_specialty_pipeline_benchmark.py`: Script chạy benchmark 20 ca phân luồng chuyên khoa.
- `run_manual_eval.py`: Công cụ hỗ trợ đánh giá thủ công có can thiệp của bác sĩ/chuyên gia y tế.

---

## 2. Tiêu chí đánh giá chất lượng (Metrics)

1. **ATS Emergency Triage Precision:** 100% ca cấp cứu (ATS 1-2) phải được kích hoạt cổng Zero-Token khẩn cấp, không được để sót hoặc xử lý chậm.
2. **Specialty Routing Accuracy:** Độ chính xác phân luồng chuyên khoa đạt > 90%.
3. **Adaptive Probing (Fact-Awareness):** Không bao giờ hỏi dồn nhiều hơn 1 câu/lượt và không hỏi lại triệu chứng bệnh nhân đã cung cấp.
4. **Clinical Critic Pass Rate:** Tỷ lệ phản tư lâm sàng đạt chuẩn an toàn y khoa trước khi phản hồi người bệnh.
5. **LLM Latency & Availability:** Phản hồi trung bình < 3 giây với cơ chế Hedged Requests & Failover Gateway.

---

## 3. Cách chạy Benchmark

```bash
# Chạy đánh giá 10 ca thực tế
python eval/run_realistic_benchmark.py

# Chạy đánh giá 20 ca đa chuyên khoa
python eval/run_multi_specialty_pipeline_benchmark.py
```
