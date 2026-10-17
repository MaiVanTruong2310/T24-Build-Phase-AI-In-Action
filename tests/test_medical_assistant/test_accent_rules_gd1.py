"""GĐ1 kế hoạch "luật cấp cứu viết có dấu là nguồn sự thật duy nhất": hồi quy 2 chiều trên cổng cấp cứu.

Phải bắt: không dấu, dấu nửa vời, IN HOA, nhầm hỏi/ngã, cách nói đời thường. Không được bắt: câu có dấu đời thường
chứa từ mà bỏ dấu sẽ trùng mẫu luật (bộ âm tính GĐ0).
"""

import pytest

from src.medical_assistant.domain.ats_descriptor_service import match_ats_descriptors
from src.medical_assistant.domain.triage_service import get_triage_service


def _eval(text):
    return get_triage_service().evaluate_symptoms(text)


@pytest.mark.parametrize(
    "text",
    [
        "Tôi bị ốm với ho khá nhiều cùng với việc cơ thể mệt mỏi và mất ngủ",
        "Tôi cảm thấy sưng ở cổ chân sau khi đi bộ nhiều.",
        "Mắt tôi nhìn lờ mờ khi đọc sách buổi tối.",
        "Tôi chạy dài 5km mỗi sáng, muốn khám tim mạch định kỳ.",
        "Tôi bị rạn da bụng sau sinh, có điều trị được không?",
        "Tôi đau đầu từ tối đó đến giờ, âm ỉ thôi.",
        "Tôi đi bộ từ từ thì đỡ đau.",
        "Tôi muốn kiểm tra da mặt vì hay nổi mụn.",
        "Lối xuống bãi gửi xe ở Vinmec Times City ở đâu?",
        "Tôi đá bóng bị bong gân cổ chân, sưng lớn.",
        "Nước tiểu màu vàng sẫm, không cảm thấy đau gì.",
        "Khí hư ra màu trắng đục nhiều, có ngứa nhẹ.",
        "Phòng khám ở nơi đó mở cửa từ sáng mấy giờ?",
        "Tôi đang mất phương hướng trong công việc nên hay căng thẳng.",
        "Răng khôn của tôi mọc lệch hẳn ra ngoài.",
        "Tôi leo 3 tầng là thở không nổi khi leo cầu thang mấy tháng nay",
    ],
)
def test_accented_everyday_text_is_not_emergency(text):
    r = _eval(text)
    assert not r.is_emergency and r.ats_level.value >= 4, (r.ats_level, r.triggered_rule_ids)


@pytest.mark.parametrize(
    "text",
    [
        "con tôi 2 tuoi dang co giat lien tuc",  # dấu nửa vời
        "con toi bi voi bot ban vào mắt, khóc thét",
        "CON TOI BI VOI BOT BAN VÀO MẮT, KHÓC THÉT",  # in hoa
        "TÔI BI DUT TAY MAU CHAY XOI XA KHONG CAM DUOC",
        "bạn tui uống rịu say xong bất tĩnh luôn, lay gọi k dậy",  # nhầm hỏi/ngã
        "Bố t 62t, nặng ngực kinh khủng, thở ko nổi, người nhợt nhạt.",
        "Bé nhà tui 1 tuổi bị hóc hạt lạc, giờ đang ho sặc với tím mặt nhen.",
        "Mẹ tôi 68 tuổi. Đang ăn cơm thì miệng méo, rơi đũa, nói không rõ.",
        "Bố tui tự nhiên nói hổng ra chi hết, rồi mặt bị xệ xuống một bên.",
        "Tui bị xăng cháy bỏng hết hai bàn tay với cái mặt luôn, rồi ho mà giọng khàn khàn nữa.",
        "dau nguc du doi lan ra tay trai, va mo hoi",
        "bố tôi lo mo không tỉnh",
        "bé nhà mik 1t bị hóc hạt lạc á, đag ho sặc vs tím mặt luôn",  # "mik" không phải phủ định "k"
    ],
)
def test_emergency_caught_in_any_accent_form(text):
    assert _eval(text).is_emergency


def test_confidence_grades_unaccented_ambiguity():
    # "voi" (con voi) đứng chỗ luật cần "vôi" → mơ hồ, VẪN nâng mức (GĐ2: hỏi xác nhận)
    r = _eval("toi ho nhieu cung voi mat ngu")
    assert r.is_emergency and r.match_confidence == "ambiguous"
    assert _eval("Con tôi bị vôi bột bắn vào mắt").match_confidence == "certain"


def test_doctor_name_nga_is_lowercased_and_never_emergency():
    """Bác sĩ duyệt 2026-10-13: đưa hết về chữ thường (không suy tên riêng). "Nga" khớp "ngã" ở mức mơ hồ →
    tối đa ATS 3 (khám trong ngày), không bao giờ cấp cứu."""
    r = _eval("Tôi muốn đặt lịch với bác sĩ Nga vì bị đau hông khi ngồi lâu.")
    assert not r.is_emergency


@pytest.mark.parametrize("text", ["toi muon kiem tra mat dinh ky", "tôi muốn kiểm tra mắt định kỳ", "kiem soat mat"])
def test_kiem_tra_mat_is_not_chemical_eye(text):
    # "kiem" = kiểm (tra/soát), không phải chất kiềm
    assert match_ats_descriptors(text) is None


@pytest.mark.parametrize("text", ["nước kiềm bắn vào mắt", "dung dich kiem ban vao mat"])
def test_alkali_in_eye_still_emergency(text):
    m = match_ats_descriptors(text)
    assert m and m.rule_id == "ATS2_EYE_CHEMICAL"


# ------------------------------------------------------------------ bench dev 13/10: 3 ca cấp cứu bản cũ bắt, bản mới hỏi lại
@pytest.mark.parametrize(
    "text",
    [
        "Be nha toi 3 tuoi bi sot tu hom qua. Chau non may lan roi. Gio chau cu li bi, co cung, khong cui dau duoc.",
        "Bo toi bi tieu duong dang tiem insulin, gio va mo hoi, run tay, noi ngong, lo mo.",
        "alo em oi bo anh tu nhien nga ra noi khong duoc tay phai khong nhac len duoc moi cach day",
    ],
)
def test_several_independent_signs_are_emergency_without_asking(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and r.match_confidence != "ambiguous"


@pytest.mark.parametrize(
    "text",
    ["đột nhiên tay trái không cử động được", "tay chân bên trái không cử động được, miệng lệch"],
)
def test_paralysis_phrased_with_khong_is_focal_neuro(text):
    r = get_triage_service().evaluate_symptoms(text)
    assert r.is_emergency and "ATS2_ACUTE_FOCAL_NEURO" in r.triggered_rule_ids


@pytest.mark.parametrize(
    "text",
    ["không có yếu tay chân", "tay phải không yếu, vẫn nhấc lên được", "tôi không ngất", "miệng hơi lệch từ nhỏ"],
)
def test_true_negations_and_chronic_stay_non_emergency(text):
    assert not get_triage_service().evaluate_symptoms(text).is_emergency


def test_ambiguous_turn_uses_prior_turns_as_evidence():
    # EMR-ACC-005 (bench): "bé 3 tuổi sốt" → "nôn" → "li bi, co cung" — đủ chứng cứ, không hỏi lại
    msgs = [
        {"role": "user", "content": "Be nha toi 3 tuoi bi sot tu hom qua."},
        {"role": "user", "content": "Chau non may lan roi."},
    ]
    r = get_triage_service().evaluate_with_recent_context("Gio chau cu li bi, co cung, khong cui dau duoc.", msgs)
    assert r.is_emergency and r.match_confidence != "ambiguous"
