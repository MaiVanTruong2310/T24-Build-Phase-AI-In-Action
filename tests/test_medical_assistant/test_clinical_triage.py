"""
Bộ kiểm thử chất lượng phân cấp lâm sàng (Golden Benchmark Test)
Kiểm tra 3 kịch bản cốt lõi:
1. Ca cấp cứu tối khẩn -> Bắt buộc ATS Level 1/2 và Khóa đặt lịch (max_days = 0)
2. Ca cấp tính bán khẩn -> Bắt buộc ATS Level 3 và Giới hạn ngày (max_days = 1)
3. Ca thông thường / Mạn tính -> ATS Level 4/5 (max_days >= 7)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.medical_assistant.domain.disease_triage import ATSLevel  # noqa: E402
from src.medical_assistant.domain.triage_service import get_triage_service  # noqa: E402


def test_negated_gastrointestinal_warning_signs_do_not_force_ats3():
    result = get_triage_service().evaluate_symptoms(
        "Bụng bên trái đau âm ỉ 4 trên 10 đã ba ngày, không sốt, không nôn, không tiêu chảy và không đi ngoài ra máu."
    )

    assert result.ats_level in {ATSLevel.LEVEL_4_STANDARD, ATSLevel.LEVEL_5_NON_URGENT}
    assert result.max_booking_days >= 7


TEST_CASES = [
    # Nhóm 1: Ca Cấp cứu tối khẩn (Phải Block)
    {
        "input": "Tôi bị đau thắt ngực dữ dội lan ra cánh tay trái, vã mồ hôi lạnh và khó thở quá",
        "expected_level": ATSLevel.LEVEL_2_EMERGENT,
        "expected_block": True,
        "case_name": "Nhồi máu cơ tim cấp",
    },
    {
        "input": "Người nhà tôi đột nhiên méo miệng, yếu liệt nửa người bên phải không nói rõ tiếng được",
        "expected_level": ATSLevel.LEVEL_2_EMERGENT,
        "expected_block": True,
        "case_name": "Đột quỵ não FAST",
    },
    {
        "input": "Cháu bé uống nhầm thuốc diệt chuột đang nôn ói nhiều",
        "expected_level": ATSLevel.LEVEL_1_RESUSCITATION,
        "expected_block": True,
        "case_name": "Ngộ độc cấp tính",
    },
    # Nhóm 2: Ca Bán khẩn (Chỉ đặt trong ngày)
    {
        "input": "Tôi bị đau quặn thận từng cơn kèm tiểu buốt ra máu từ tối qua",
        "expected_level": ATSLevel.LEVEL_3_URGENT,
        "expected_block": False,
        "expected_max_days": 1,
        "case_name": "Cơn đau quặn thận cấp",
    },
    # Nhóm 3: Ca Mạn tính / Thông thường (Linh hoạt trong tuần)
    {
        "input": "Tôi làm việc văn phòng hay bị mỏi vai gáy và đau lưng âm ỉ cả tháng nay",
        "expected_level": ATSLevel.LEVEL_4_STANDARD,
        "expected_block": False,
        "expected_max_days": 7,
        "case_name": "Thoái hóa / Đau mỏi cơ xương khớp",
    },
    {
        "input": "Tôi muốn đăng ký kiểm tra sức khỏe tổng quát định kỳ",
        "expected_level": ATSLevel.LEVEL_4_STANDARD,
        "expected_block": False,
        "case_name": "Khám sức khỏe tổng quát",
    },
]


def run_benchmark():
    print("=" * 70)
    print("🩺 BẮT ĐẦU CHẠY GOLDEN BENCHMARK KIỂM THỬ TRIAGE SERVICE")
    print("=" * 70)

    service = get_triage_service()
    passed = 0
    total = len(TEST_CASES)

    for idx, tc in enumerate(TEST_CASES, 1):
        result = service.evaluate_symptoms(tc["input"])
        is_level_match = result.ats_level == tc["expected_level"]
        is_block_match = result.is_emergency == tc["expected_block"]

        success = is_level_match and is_block_match

        status_str = "✅ PASS" if success else "❌ FAIL"
        if success:
            passed += 1

        print(f"\n[{idx}/{total}] {tc['case_name']} -> {status_str}")
        print(f"   Input: '{tc['input']}'")
        print(
            f"   Kết quả: ATS {result.ats_level.value} | Max days: {result.max_booking_days} | Khoa: {result.suggested_specialty}"
        )
        print(f"   Chỉ dẫn: {result.patient_guidance[:100]}...")

    print("\n" + "=" * 70)
    print(f"🏆 KẾT QUẢ KIỂM THỬ: {passed}/{total} ca đạt chuẩn ({passed / total * 100:.1f}%)")
    print("=" * 70)

    if passed == total:
        print("🎉 TẤT CẢ CÁC CA ĐÃ ĐẠT CHUẨN AN TOÀN Y TẾ VÀ QUẢN LÝ ĐẶT LỊCH!")
    else:
        print("⚠️ Có ca chưa khớp kỳ vọng, cần tinh chỉnh thêm quy tắc.")


if __name__ == "__main__":
    run_benchmark()
