# Nâng cấp ghi nhớ và xử lý đa triệu chứng

## Trạng thái

Đã triển khai trong `` ngày 2026-09-30. Thiết kế giữ tương thích với các consumer cũ qua `chief_complaint` và `active_probing_category`, đồng thời bổ sung state có cấu trúc cho luồng mới.

## Luồng xử lý

1. Rule extractor và LLM cùng tạo các complaint delta.
2. `ClinicalFactService.merge()` hợp nhất theo mã complaint, giữ thứ tự xuất hiện và vòng đời `active`, `denied`, `resolved`, `uncertain`.
3. Cổng an toàn ATS chạy trước. Kết quả cấp cứu hoặc khám trong ngày luôn có quyền ưu tiên.
4. `resolve_multi_symptom()` tạo các ứng viên chuyên khoa có bằng chứng, dữ kiện còn thiếu, điểm và ATS.
5. Probing lưu ngân sách riêng trong `probing_by_complaint`. Khi nhiều hệ cơ quan cùng hoạt động, agent hỏi một câu tổng hợp về triệu chứng chính và cờ đỏ.
6. Response và API/SSE trả cả hướng ưu tiên, các chuyên khoa đang cân nhắc và lý do xung đột.

## State mới

```json
{
  "clinical_facts": {
    "primary_complaint": "headache",
    "active_complaint_codes": ["headache", "sore_throat", "abdominal_pain"],
    "complaints": [
      {
        "code": "headache",
        "system": "neurology",
        "status": "active",
        "first_seen_turn": 1,
        "last_seen_turn": 1,
        "evidence": ["dau dau"],
        "confidence": 1.0,
        "source": "deterministic"
      }
    ]
  },
  "active_probing_categories": ["DAU_DAU", "DAU_BUNG"],
  "probing_by_complaint": {
    "headache": {"category": "DAU_DAU", "status": "active", "questions_asked": 1}
  },
  "candidate_specialties": [
    {
      "code": "THAN_KINH",
      "name": "Thần kinh",
      "score": 1.25,
      "ats_level": 4,
      "evidence": ["headache"],
      "missing_information": ["onset", "severity"]
    }
  ],
  "conflict_reason": "Các triệu chứng hiện hướng tới nhiều chuyên khoa."
}
```

## Quy tắc ưu tiên

- ATS 1–2 giữ nguyên kết quả cấp cứu, không chờ hỏi thêm.
- ATS 3 được xếp trước ứng viên ATS 4–5.
- Khi các ứng viên cùng ATS, complaint được người bệnh nêu là chính được ưu tiên; nếu chưa nêu rõ thì giữ thứ tự xuất hiện.
- Complaint đã phủ định hoặc đã hết không tham gia định tuyến hiện tại nhưng vẫn còn trong lịch sử để giải thích diễn biến.
- Mỗi complaint có ngân sách tối đa hai câu hỏi; câu hỏi tổng hợp được tính cho các complaint đang hoạt động.

## Cổng an toàn đau ngực và thần kinh

- Nhận dạng các cách nói `đau tức lồng ngực`, `tức lồng ngực`, `đau tức ngực`, `chest pressure` và `chest discomfort`.
- Đau hoặc tức ngực mới, chưa đủ dữ kiện loại trừ nguyên nhân tim phổi: ATS 3, đánh giá trực tiếp trong ngày.
- Đau ngực có tính chất nghi tim hoặc kèm khó thở, vã mồ hôi, choáng/ngất, hướng lan hay khởi phát khi gắng sức: ATS 2, chuyển Cấp cứu.
- ATS 1 dành cho bất ổn tức thời như ngừng tuần hoàn, ngừng thở, hôn mê hoặc suy hô hấp cực kỳ nặng.
- Đau đầu kèm nhìn mờ hoặc nhìn đôi: ATS 3 và bắt buộc safety review; các dấu hiệu FAST vẫn chuyển Cấp cứu ATS 2.
- `SAFETY_REVIEW` luôn khóa lịch thường (`max_booking_days = 0`) và trả `acuity_status` cùng `disposition`, tránh hiển thị mâu thuẫn `WITHIN_WEEK`.

## Tương thích API

`ChatResponse` và event metadata của SSE có thêm:

- `suggested_department`
- `candidate_specialties`
- `conflict_reason`

Các field cũ vẫn được giữ.

## Ngưỡng công khai nhiều chuyên khoa

Mỗi ứng viên có thêm `routing_confidence`, `evidence_strength`, `has_independent_evidence`,
`publicly_recommended` và `suppression_reason`. Đây là độ tin cậy điều hướng, không phải xác suất mắc bệnh.

- Khoa chính phải đạt `routing_confidence >= 0.65`.
- Khoa thứ hai phải đạt `routing_confidence >= 0.60`.
- Điểm khoa thứ hai phải đạt ít nhất 75% điểm khoa chính.
- Khoa thứ hai phải có bằng chứng độc lập từ complaint được rule xác nhận.
- API chỉ công khai tối đa hai khoa; các ứng viên còn lại được giữ trong `routing_candidates` để kiểm tra nội bộ.
- Ứng viên chỉ do LLM suy ra và không có rule xác nhận sẽ không được công khai nếu chưa đạt ngưỡng.
- ATS 1–2 vẫn chỉ điều hướng Cấp cứu; danh sách khoa không được dùng để trì hoãn xử trí.

## Kiểm thử

`tests/test_multi_symptom_routing.py` bao phủ:

- Tích lũy complaint qua nhiều lượt và không ghi đè complaint đầu.
- Nhận dạng `đau thêm cả bụng`, `đau họng` và lỗi gõ `đau học`.
- Chuyển complaint sang `resolved` và đổi complaint chính khi người bệnh nói rõ.
- Tạo nhiều ứng viên chuyên khoa, ưu tiên ATS 3 và bảo toàn cổng cấp cứu.
- Ngân sách probing riêng theo complaint.
- Agent hỏi câu tổng hợp thay vì chốt sớm Tiêu hóa.
- Response hiển thị hướng chính và hướng cần cân nhắc.
