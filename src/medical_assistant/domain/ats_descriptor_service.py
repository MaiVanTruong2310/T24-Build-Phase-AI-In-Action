"""Mô tả lâm sàng theo thang ATS (ACEM 2023, Appendix A trong ETEK 2nd ed.) cho lời kể tiếng Việt.

Chỉ dùng để NÂNG mức khẩn cấp: trả về mức ATS khẩn nhất khớp được (1-3) hoặc None.
Luật viết CÓ DẤU (nguồn sự thật duy nhất) và được biên dịch "dấu là ràng buộc" (accent_matcher): dấu người dùng
đã gõ phải đúng ("với" ≠ "vôi", "mất" ≠ "mắt"); dấu bị bỏ (không dấu, dấu nửa vời, thiếu thanh) vẫn khớp.
Mỗi lần khớp mang `confidence` (certain / missing_accent / ambiguous) — chỉ để phân độ, không để loại.
Nguồn mô tả: Guidelines on the Implementation of the ATS in Emergency Departments, ACEM 2023.
Luật đánh dấu [BS duyệt] = siết ngữ cảnh khi trùng NGHĨA (dấu không phân biệt được), chờ bác sĩ duyệt.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from src.medical_assistant.domain.accent_matcher import (
    _RANK,
    CERTAIN,
    AccentRule,
    confidence,
    prepare,
    rule,
    strip_marks,
    worst,
)


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên chữ hoa/thường và độ dài → dùng được cho cả regex pattern."""
    value = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text or ""))
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def _strip(text: str) -> str:
    return re.sub(r"\s+", " ", strip_accents((text or "").lower()))


# \b: "mik" (mình) không được hiểu là "k" (không)
# "không được / không nổi / không đặng" là ĐUÔI của triệu chứng trước ("nói không được tay phải…" — lời thoại giọng
# nói không dấu phẩy), không phủ định triệu chứng sau.
_NEG_BEFORE = rule(r"\b(?:không|chưa|hết|chẳng|ko|k)\s+(?!(?:được|đặng|nổi)\s+(?:\w+\s+)?$)(?:\w+\s+){0,2}$")


@dataclass(frozen=True)
class AtsDescriptorMatch:
    ats_level: int
    rule_id: str
    name: str
    specialty: str | None
    confidence: str = CERTAIN


# (ATS, rule_id, regex CÓ DẤU, tên hiển thị, chuyên khoa gợi ý)
_RULES: list[tuple[int, str, str, str, str | None]] = [
    # --- ATS 1: đe dọa tính mạng tức thì ---
    (
        1,
        "ATS1_UNRESPONSIVE",
        r"bất tỉnh|gọi (?:thế nào )?(?:cũng )?không (?:tỉnh|dậy)|lay (?:gọi )?(?:thế nào )?(?:cũng )?không tỉnh"
        r"|không (?:đánh thức|gọi) (?:được|dậy)|không (?:tỉnh )?dậy được|gọi gần như không tỉnh|mềm oặt",
        "Không đáp ứng / chỉ đáp ứng kích thích đau",
        "Cấp cứu",
    ),
    (
        1,
        "ATS1_HYPOVENTILATION",
        r"lâu lâu mới thở|thở (?:rất )?chậm|thở ngáp|thoi thóp",
        "Thở chậm / thở ngáp",
        "Cấp cứu",
    ),  # fmt: skip
    (
        1,
        "ATS1_VIOLENCE",
        r"(?:rút|cầm|vung|giữ) (?:\w+ )?(?:dao|súng|kiếm)|đâm (?:chết|người)|dọa giết|định đánh (?:mọi )?người",
        "Hành vi bạo lực đe dọa tức thì",
        "Cấp cứu",
    ),
    (
        1,
        "ATS1_CORD_PROLAPSE",
        r"dây rốn (?:thòng|thò|sa|rơi)|(?:sa|thấy|thòng) dây rốn|như dây rốn",
        "Sa dây rốn khi chuyển dạ",
        "Sản phụ khoa",
    ),
    # --- ATS 2: có thể đe dọa tính mạng trong 10 phút ---
    (
        2,
        "ATS2_VERY_SEVERE_PAIN",
        # 9-10/10. Ngưỡng 8/10 → ATS 2 là quyết định chính sách lâm sàng (ATS 2 = khóa đặt lịch, gọi 115),
        # chưa đổi; người già đau bụng nặng được nâng riêng ở ATS2_ABD_PAIN_ELDERLY_SEVERE.
        r"(?:đau|nhức|buốt)[^.;,]{0,40}?(?:\b(?:9|10)\s*(?:/|trên)\s*10\b|dữ dội|kinh khủng|khủng khiếp|tột độ"
        r"|không chịu nổi|phát khóc|nhất từ trước)|\b(?:9|10)\s*(?:/|trên)\s*10\b",
        "Đau rất nặng",
        None,
    ),
    (
        2,
        "ATS2_CIRCULATORY_COMPROMISE",
        r"vã mồ hôi lạnh|(?:da|người) (?:tái )?lạnh (?:và )?(?:ẩm|vã mồ hôi)|tái lạnh|lạnh ngắt|nổi vân tím",
        "Dấu hiệu tuần hoàn kém (da lạnh ẩm, vân tím)",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_SEVERE_RESP_DISTRESS",
        r"nói (?:được )?(?:vài|một vài|\d|hai|ba) (?:chữ|từ)[^.;]{0,15}(?:dừng|nghỉ|thở)"
        r"|không nói (?:được )?(?:thành )?câu|thở (?:rất )?gắng sức|co rút lồng ngực|ngồi (?:dậy|chống tay)[^.;]{0,10}thở"
        r"|thở không nói|thở hổn hển|thở không (?:nói|ra hơi)|chảy dãi"
        # Dấu hiệu suy hô hấp cấp (youmed.vn/tin-tuc/suy-ho-hap, đối chiếu ACEM ATS 2 "severe respiratory distress")
        r"|nói không (?:hết|thành|trọn|được hết) (?:câu|câu nói)|nói (?:\w+ ){0,2}(?:đứt quãng|ngắt quãng)"
        r"|\bthở rít\b|rút lõm (?:lồng ngực|hõm ức|hố ức|dưới sườn)|co kéo (?:cơ )?(?:hô hấp|liên sườn)"
        r"|cánh mũi phập phồng"
        # [BS duyệt] "thở không nổi/được" = khó thở nặng (bản cũ bắt nhờ trùng "tho khong noi"); trừ ngữ cảnh gắng sức
        r"|(?:thở không (?:nổi|được)|không thở (?:nổi|được))(?! khi (?:leo|chạy|đi|gắng sức|vận động|làm việc))",
        "Suy hô hấp nặng",
        "Nội hô hấp",
    ),
    (
        2,
        "ATS2_FEVER_LETHARGY",
        r"\bsốt\b[^.;]{0,60}\b(?:li bì|lơ mơ|lừ đừ)\b|\b(?:li bì|lơ mơ|lừ đừ)\b[^.;]{0,60}\bsốt\b",
        "Sốt kèm li bì",
        None,
    ),
    (
        2,
        "ATS2_DROWSY",
        r"\blơ mơ\b|\bli bì\b|\blừ đừ\b|gọi (?:mới|khó) (?:tỉnh|mở mắt)"
        # [BS duyệt] "nhắm mắt … gọi" chỉ khi gọi mãi/mới/khó mở (không phải "nhắm mắt… gọi điện đặt lịch")
        r"|nhắm mắt[^.;]{0,25}gọi (?:mãi |hỏi )?(?:không|mới|khó)|khó đánh thức|đánh thức (?:mới|rất khó)"
        # [BS duyệt] "mất phương hướng" trừ nghĩa bóng (công việc, cuộc sống, học tập, tình cảm)
        r"|mất phương hướng(?! (?:trong |về )?(?:công việc|cuộc sống|học tập|tình cảm|sự nghiệp|tương lai))",
        "Giảm đáp ứng / lơ mơ",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_EYE_CHEMICAL",
        # [BS duyệt mục 2: siết chỗ trùng nghĩa] "kiem tra/che/soat/nen" = kiểm tra, kiềm chế… không phải chất kiềm
        r"(?:hóa chất|axit|acid|kiềm(?!\s+(?:tra|chế|soát|nén))|xút|thuốc tẩy|vôi|xi măng|nước tẩy)[^.;]{0,40}\bmắt\b"
        r"|\bmắt\b[^.;]{0,30}(?:hóa chất|axit|acid|xút|thuốc tẩy|vôi bột)",
        "Hóa chất bắn vào mắt",
        "Mắt (Nhãn khoa)",
    ),
    (
        2,
        "ATS2_MAJOR_TRAUMA",
        r"xương (?:lòi|trồi|đâm) ra|lòi (?:cả )?xương|cụt (?:rời )?(?:ngón|tay|chân|bàn)|đứt (?:rời )?(?:ngón|tay)",
        "Chấn thương khu trú nặng (gãy hở, cụt chi)",
        "Chấn thương chỉnh hình - Y học thể thao",
    ),
    (
        2,
        "ATS2_TESTICULAR_TORSION",
        r"xoắn tinh hoàn|(?:đau|sưng) (?:tinh hoàn|hòn dái|bìu|hòn bi)[^.;]{0,30}(?:đột ngột|dữ dội|tự nhiên)"
        r"|(?:đột ngột|tự nhiên)[^.;]{0,20}đau (?:tinh hoàn|hòn dái|bìu)",
        "Nghi xoắn tinh hoàn",
        "Thận - Tiết niệu",
    ),
    (
        2,
        "ATS2_ENVENOMATION",
        r"rắn (?:độc )?cắn|bị rắn|sứa (?:biển )?(?:đốt|cắn)|bọ cạp|nhện độc",
        "Động vật có nọc độc",
        None,
    ),  # fmt: skip
    (
        2,
        "ATS2_TOXIC_EXPOSURE",
        r"(?:thuốc trừ sâu|thuốc diệt cỏ|hóa chất|thuốc chuột)[^.;]{0,80}(?:nôn|vã mồ hôi|khó thở|chóng mặt|co giật|lơ mơ)",
        "Phơi nhiễm chất độc có triệu chứng",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_FEBRILE_NEUTROPENIA",
        r"(?:hóa trị|truyền hóa chất|điều trị ung thư)[^.;]{0,80}sốt|sốt[^.;]{0,80}hóa trị",
        "Sốt sau hóa trị",
        None,
    ),
    (
        2,
        "ATS2_BURN_LARGE",
        # [BS duyệt] "bong gân", "bong tróc" viết đúng là không dấu, không phải "bỏng"
        r"bỏng(?! (?:gân|tróc|da tay))[^.;]{0,40}(?:rộng|cả (?:mặt|hai)|hai (?:bên )?(?:bàn )?(?:đùi|chân|tay)|nhiều chỗ|lớn"
        # [BS duyệt] bỏng kèm dấu hiệu đường thở (khàn tiếng, ho khàn sau bỏng lửa) là ATS 2 dù diện tích nhỏ;
        # không lấy "mặt" đơn lẻ (bỏng nắng nhẹ ở mặt không phải ATS 2)
        r"|khàn tiếng|giọng khàn|ho khàn)",
        "Bỏng diện rộng",
        None,
    ),
    (
        2,
        "ATS2_AIRWAY_FOREIGN_BODY",
        # [BS duyệt] hóc/nghẹn dị vật kèm tím, không thở/không nói được (tắc đường thở; ACEM ATS 1-2, sàn ATS 2)
        r"hóc[^.;]{0,40}(?:tím|không thở|không nói|ngạt|ho sặc)|(?:nghẹn|mắc nghẹn)[^.;]{0,30}(?:tím|không thở|không nói)",
        "Dị vật đường thở",
        "Cấp cứu",
    ),
    (2, "ATS2_SEVERE_BLEEDING", r"(?:máu|chảy máu)[^.;]{0,30}(?:khắp sàn|ồ ạt|xối xả|không cầm)", "Mất máu nặng", None),
    (
        2,
        "ATS2_SELF_HARM_IMMINENT",
        # Quá liều: từ 10 viên trở lên ("vừa uống 2 viên paracetamol" không tính).
        r"(?:tự (?:làm hại|tử)|muốn chết)[^.;]{0,60}(?:sẽ làm (?:nữa|tiếp)|ngay khi|vừa uống)|vừa uống (?:[1-9]\d|\d{3}) viên",
        "Nguy cơ tự hại tức thì",
        "Cấp cứu",
    ),
    # --- ATS 3: có thể đe dọa tính mạng trong 30 phút ---
    (3, "ATS3_MODERATELY_SEVERE_PAIN", r"\b[78]\s*(?:/|trên)\s*10\b", "Đau mức nặng vừa (7-8/10)", None),
    (
        3,
        "ATS3_SYNCOPE",
        r"\b(?:vừa|mới|đã|bị|từng|lại)\s+(?:bị\s+)?ngất\b(?!\s+(?:mũi|lời|điện|quãng|mạch|kết nối))|\bngất xỉu\b"
        r"|\b(?:vừa|mới|bị|lại)\s+(?:bị\s+)?xỉu\b|\bxỉu (?:đi|ngã)\b|\blên cơn ngất\b",
        "Ngất / xỉu vừa xảy ra",
        "Trung tâm Tim mạch",
    ),
    (
        3,
        "ATS3_FALL_CANNOT_BEAR_WEIGHT",
        r"\bngã\b[^.;]{0,80}(?:không (?:tự )?(?:đứng|đi|đứng dậy|đứng lên) (?:dậy|được|lên)|ôm (?:hông|đùi)"
        r"|đau (?:hông|khớp háng))|(?:không (?:tự )?(?:đứng|đi) (?:dậy|được)|ôm (?:hông|đùi))[^.;]{0,60}\bngã\b",
        "Ngã, không đứng dậy được / đau hông (nghi gãy xương)",
        "Chấn thương chỉnh hình - Y học thể thao",
    ),
    (
        3,
        "ATS3_INTOXICATED_AT_RISK",
        r"(?:say (?:rượu|xỉn)|mùi rượu|ngáo đá|phê (?:thuốc|ma túy)|dùng ma túy)[^.;]{0,100}"
        r"(?:giữa đường|cao tốc|lắc lư|nằm (?:dưới )?đất|nói (?:rất )?ít|không tỉnh táo|lú lẫn|không biết gì)"
        r"|(?:giữa đường|cao tốc|lắc lư|nằm (?:dưới )?đất)[^.;]{0,100}(?:say (?:rượu|xỉn)|mùi rượu|ngáo đá"
        r"|phê (?:thuốc|ma túy))",
        "Say / dùng chất kèm hành vi nguy hiểm",
        None,
    ),
    # Thành ngữ "đau bụng muốn chết" = đau rất nặng (không phải ý nghĩ tự sát).
    (3, "ATS3_SEVERE_PAIN_IDIOM", r"\b(?:đau|nhức)\b[^.,;!?]{0,15}muốn chết", "Đau rất nặng", None),
    (
        3,
        "ATS3_ACUTE_CONFUSION",
        r"(?:tự nhiên|đột nhiên|hôm nay|bỗng nhiên)[^.;]{0,20}(?:lú lẫn|lẫn lộn|mất định hướng)",
        "Lú lẫn cấp",
        "Thần kinh",
    ),
    (
        3,
        "ATS3_PERSISTENT_VOMITING",
        r"nôn (?:liên tục|không ngừng|nhiều lần|[3-9] lần|hơn \d+ lần)|uống gì nôn nấy|nôn hết",
        "Nôn kéo dài",
        None,
    ),
    # Mất nước chỉ khi đang nôn/tiêu chảy ("tiểu ít vì uống ít nước" không tính).
    (
        3,
        "ATS3_DEHYDRATION",
        r"^(?=.*(?:\bnôn\b|tiêu chảy|đi lỏng|đi ngoài))(?:.*?)(?:nước tiểu sẫm|tiểu (?:rất )?ít|miệng khô|mắt trũng)",
        "Mất nước",
        None,
    ),
    (
        3,
        "ATS3_HEAD_INJURY_LOC",
        r"(?:đập đầu|ngã[^.;]{0,30}đầu|chấn thương đầu)[^.;]{0,60}(?:ngất|bất động|mất ý thức)",
        "Chấn thương đầu có mất ý thức ngắn",
        "Thần kinh",
    ),
    (
        3,
        "ATS3_LIMB_INJURY",
        # [BS duyệt] lệch/biến dạng/cong vẹo chỉ tính khi có bối cảnh chấn thương (không phải răng mọc lệch,
        # móng biến dạng do nấm, cong vẹo cột sống bẩm sinh)
        r"^(?=.*(?:\bngã\b|\btế\b|va (?:đập|chạm)|tai nạn|chấn thương|\bđập\b|\bgãy\b|\btrật\b))"
        r"(?:.*?)(?:lệch (?:hẳn|đi)|biến dạng|cong vẹo)|vết rách sâu|lộ (?:cả )?gân|dập nát",
        "Chấn thương chi mức vừa (biến dạng, rách sâu)",
        "Chấn thương chỉnh hình - Y học thể thao",
    ),
    (
        3,
        "ATS3_MODERATE_BLEEDING",
        r"(?:chảy máu|ra máu)[^.;]{0,30}(?:nhiều|đầy)|đầy (?:cả )?bồn cầu",
        "Mất máu mức vừa",
        None,
    ),
    (
        3,
        "ATS3_PSYCHOSIS",
        r"ảo giác|hoang tưởng|tiếng nói bảo|nói chuyện một mình|nghi (?:đồ ăn )?bị đầu độc|phát tia|người ngoài hành tinh",
        "Loạn thần cấp",
        "Trung tâm chăm sóc sức khỏe tinh thần tích hợp",
    ),
    (
        3,
        "ATS3_SELF_HARM",
        r"tự (?:làm hại|tử|sát)|muốn chết|rạch tay|cắt tay|vết cắt[^.;]{0,15}cổ tay",
        "Nguy cơ tự hại",
        "Trung tâm chăm sóc sức khỏe tinh thần tích hợp",
    ),
    (
        3,
        "ATS3_CHILD_ABUSE_RISK",
        r"(?:bé|con|trẻ)[^.;]{0,60}(?:vết bầm|bầm (?:xanh|tím|vàng))",
        "Trẻ có vết bầm không rõ nguyên nhân",
        None,
    ),
]

_COMPILED: list[tuple[int, str, AccentRule, str, str | None]] = [
    (ats, rid, rule(p), name, spec) for ats, rid, p, name, spec in _RULES
]

_INFANT = rule(r"\b(?:\d+|một|hai|ba|bốn) tuần tuổi|\b[12] tháng tuổi|sơ sinh|mới sinh")
# Thêm vân tím (tuần hoàn kém) và gọi rất khó tỉnh (chỉ đáp ứng kích thích mạnh) ở trẻ < 3 tháng: ATS 1.
_INFANT_CRITICAL = rule(
    r"thở yếu|thở bất thường|xám|tím tái|ngừng thở|mềm oặt|vân tím|nổi vân|gọi (?:rất |thật )?khó tỉnh"
    r"|lay (?:rất )?khó tỉnh"
)
_INFANT_UNWELL = rule(r"bú kém|bỏ bú|li bì|ngủ (?:li bì|nhiều)|khó (?:đánh thức|tỉnh)|sốt|lừ đừ|tái|lạnh")
_AGE = re.compile(r"\b(\d{2,3}) tu[ổôoóòỏõọ]i\b")
_ABD_PAIN = rule(r"đau bụng|đau (?:dạ dày|thượng vị)")
_ELDERLY_ABD_SEVERE = rule(
    r"\b(?:8|9|10)\s*(?:/|trên)\s*10\b|\bsốt\b|\btăng dần\b|\bngày càng (?:tăng|đau)\b|\bdữ dội\b"
)


def _num(value: str) -> float:
    return float(value.replace(",", "."))


_V_SPO2 = rule(r"(?:spo2|sp02|oxy|o2|bão hòa)[^\d]{0,20}(\d{2,3})\s*%?")
_V_BP = rule(r"huyết áp[^\d]{0,20}(\d{2,3})\s*/\s*(\d{2,3})")
_V_HR = rule(r"(?:mạch|nhịp tim|tim đập)[^\d]{0,20}(\d{2,3})")
_V_RR = rule(r"nhịp thở[^\d]{0,20}(\d{1,2})")
_V_GCS = rule(r"gcs[^\d]{0,4}(\d{1,2})")
_V_BGL = rule(r"đường (?:huyết|máu)[^\d]{0,20}(\d+(?:[.,]\d+)?)")


def _vitals(t: str) -> list[tuple[int, str, str]]:
    """Ngưỡng sinh hiệu ACEM (người lớn) khi bệnh nhân/người nhà tự nhắn số đo."""
    hits: list[tuple[int, str, str]] = []
    if m := _V_SPO2.regex.search(t):
        v = _num(m.group(1))
        if v < 85:
            hits.append((1, "VITAL_SPO2_CRITICAL", f"SpO2 {v:.0f}%"))
        elif v <= 92:
            hits.append((2, "VITAL_SPO2_LOW", f"SpO2 {v:.0f}%"))
    if m := _V_BP.regex.search(t):
        sys_, dia = _num(m.group(1)), _num(m.group(2))
        if sys_ < 80:
            hits.append((1, "VITAL_BP_SHOCK", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
        elif sys_ < 90:
            hits.append((2, "VITAL_BP_LOW", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
        elif sys_ >= 180 or dia >= 110:
            hits.append((3, "VITAL_BP_SEVERE_HTN", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
    if m := _V_HR.regex.search(t):
        v = _num(m.group(1))
        if v > 150 or v < 50:
            hits.append((2, "VITAL_HR_EXTREME", f"Mạch {v:.0f}"))
    if m := _V_RR.regex.search(t):
        v = _num(m.group(1))
        if v < 10:
            hits.append((1, "VITAL_RR_LOW", f"Nhịp thở {v:.0f}"))
        elif v >= 30:
            hits.append((2, "VITAL_RR_HIGH", f"Nhịp thở {v:.0f}"))
    if m := _V_GCS.regex.search(t):
        v = _num(m.group(1))
        if v < 9:
            hits.append((1, "VITAL_GCS_LT9", f"GCS {v:.0f}"))
        elif v < 13:
            hits.append((2, "VITAL_GCS_LT13", f"GCS {v:.0f}"))
        elif v < 15:
            hits.append((3, "VITAL_GCS_13_14", f"GCS {v:.0f}"))
    if (m := _V_BGL.regex.search(t)) and _num(m.group(1)) < 3:
        hits.append((2, "VITAL_BGL_LOW", "Hạ đường huyết"))
    return hits


_INTENSITY_IDIOM_BEFORE = re.compile(
    r"\b(?:dau|met|nhuc|ngua|nong|lanh|doi|khat|so|cuoi|buon ngu|chan|xot)\b[^.,;!?]{0,15}$"
)


def is_intensity_idiom(text: str, match_start: int, matched: str) -> bool:
    """ "đau bụng muốn chết", "mệt muốn chết" là thành ngữ chỉ mức độ, không phải ý nghĩ tự sát.

    "chan" (chán) chỉ tính khi là "chán ăn"/"ngán" kiểu cảm giác; "buồn chán muốn chết" vẫn là khí sắc trầm.
    """
    if not re.search(r"mu[oốồổỗộ]n\s+ch[eếềểễệ]t", matched, re.IGNORECASE):
        return False
    prefix = _strip(text[:match_start])
    if re.search(r"\bbuon chan\b[^.,;!?]{0,15}$", prefix):
        return False
    return bool(_INTENSITY_IDIOM_BEFORE.search(prefix))


# ---------------------------------------------------------------------------
# Thần kinh khu trú cấp (ACEM ATS 2: "acute hemiparesis / dysphasia"; nhóm dấu hiệu theo bài "Các dấu hiệu thần
# kinh khu trú", ThS.BS Bùi Ngọc Phương Hòa, Vinmec Đà Nẵng). Nâng ATS 2 khi ≥ 2 nhóm, hoặc 1 nhóm + khởi phát
# cấp; không áp khi có dấu hiệu mạn tính/tiền sử.
_FOCAL = {
    "motor": rule(
        r"(?:yếu|liệt|bại liệt)\s+(?:\w+\s+){0,2}(?:nửa người|một bên|1 bên|tay|chân)"
        r"|(?:tay|chân|nửa người)\s+(?:trái|phải)?\s*(?:\w+\s+){0,3}(?:yếu|liệt|không nhấc (?:lên )?được"
        r"|không cử động được|không co được|buông thõng|lóng ngóng|vụng về)"
        r"|cầm\s+(?:đồ|cốc|ly|đũa|bút|thìa|chén|bát|vật|điện thoại)\s+(?:\w+\s+){0,3}"
        r"(?:không chặt|hay rơi|làm rơi|rơi xuống|rớt|lóng ngóng)"
        # [BS duyệt] "rơi/rớt đũa" (đảo trật tự, giọng Nam)
        r"|(?:rơi|rớt|đánh rơi|làm rớt) (?:đũa|cốc|ly|bát|chén|thìa|bút|đồ)"
    ),
    "speech": rule(
        r"nói (?:ngọng|đớ|lắp bắp|khó|không rõ (?:lời|chữ)|không ra tiếng)"
        r"|(?:không|ko) nói (?:được|ra lời)(?! (?:\w+ ){0,2}câu)|nói không (?:được|ra lời)(?! (?:\w+ ){0,2}câu)"
        r"|mất (?:khả năng )?(?:nói|diễn đạt)|không hiểu (?:người khác|ai|mình) nói|nuốt (?:khó|sặc|không được)"
        # [BS duyệt] "nói không rõ / không ra / không nổi / không đặng" (bản cũ bắt nhờ trùng "noi kho")
        r"|nói (?:không|chẳng) (?:rõ|ra (?:lời|tiếng|chi|gì)|nổi|đặng)(?! (?:\w+ ){0,2}câu)"
    ),
    "face": rule(
        r"méo (?:miệng|mặt)|miệng (?:\w+ ){0,2}méo|lệch (?:miệng|mặt)|xệ (?:một bên )?(?:mặt|miệng)"
        r"|(?:mặt|miệng) (?:\w+ ){0,3}xệ"
        # đảo trật tự như "xệ" ([BS duyệt mục 3]): "miệng lệch", "miệng bị méo lệch"
        r"|miệng (?:\w+ ){0,2}lệch"
    ),
    "vision": rule(
        r"(?:nhìn (?:\w+ ){0,2}mờ|tối sầm|mất thị lực|không nhìn thấy|màng che|màn che)[^.;]{0,25}(?:một|1|nửa) bên"
        r"|nhìn (?:thành )?(?:đôi|hai hình)|song thị|mất (?:\w+ )?nửa (?:thị trường|tầm nhìn)|mù (?:đột ngột|tạm thời)"
    ),
    "balance": rule(r"đi (?:không vững|loạng choạng|xiêu vẹo)|mất thăng bằng"),
    "sensory": rule(r"tê (?:bì )?(?:nửa người|một bên (?:người|mặt)|nửa (?:mặt|miệng)|nửa bên)"),
}
_FOCAL_ACUTE = rule(
    r"đột ngột|đột nhiên|tự nhiên|bỗng (?:nhiên|dưng)|bất ngờ|vừa (?:mới|bị|xong)|mới (?:bị|cách đây)"
    r"|cách đây \d+ (?:phút|giờ|tiếng)|\b(?:\d+|mười|vài|mấy) phút\b|\b(?:sáng|trưa|chiều|tối|đêm) nay\b"
    r"|từ (?:sáng|trưa|chiều|tối|nãy|lúc)\b|lúc ngủ dậy|sáng ngủ dậy|đêm qua"
)
_FOCAL_CHRONIC = rule(
    r"\b(?:\d+|một|hai|ba|vài|mấy|nhiều) (?:tuần|tháng|năm)\b|lâu năm|từ lâu|mạn tính|bẩm sinh|từ nhỏ|di chứng"
    r"|đã từng|từng bị|năm ngoái|trước đây"
)
# Mất tiếng do họng/thanh quản không phải rối loạn ngôn ngữ thần kinh
_THROAT = rule(r"\b(?:đau họng|viêm họng|rát họng|khản tiếng|mất tiếng|amidan|thanh quản)\b")
_INNER_NEG = re.compile(r"\b(?:khong|ko|chua|het|chang)\b")


def _accepted(r: AccentRule, t: str, orig: str):  # noqa: ARG001 - orig giữ cho tương thích chỗ gọi
    """Các lần khớp hợp lệ (không phủ định trước) kèm độ tin cậy.

    Bác sĩ duyệt 2026-10-13: đưa hết về chữ thường, không suy tên riêng từ chữ hoa. "bác sĩ Nga … đau hông" khớp
    "ngã" ở mức MƠ HỒ ("nga" là từ trơn có nghĩa) → LLM phục hồi dấu theo ngữ cảnh (ambiguity_resolution)."""
    for m in r.regex.finditer(t):
        if _NEG_BEFORE.regex.search(t[: m.start()]):
            continue
        yield m, confidence(r, m.group(0))


def _focal_domains(t: str, orig: str) -> dict[str, str]:
    hits: dict[str, str] = {}
    for name, r in _FOCAL.items():
        if name == "speech" and r_search(_THROAT, t):
            continue
        for m, conf in _accepted(r, t, orig):
            inner = _strip(m.group(0))
            if name == "speech":
                inner = re.sub(r"(?:khong|ko) noi|noi khong", "", inner)  # phủ định là một phần của triệu chứng
            elif name == "motor":
                # "không nhấc lên được / không cử động được / không co được" chính là triệu chứng liệt
                inner = re.sub(r"(?:khong|ko) (?:nhac (?:len )?duoc|cu dong duoc|co duoc)", "", inner)
            if _INNER_NEG.search(inner):
                continue
            hits[name] = conf
            break
    return hits


def rule_evidence_words(r: AccentRule, matched: str) -> set[str]:
    """Các từ (bỏ dấu) của chính luật xuất hiện trong đoạn khớp — bằng chứng, không tính chữ rơi vào wildcard."""
    vocab = r.plain_words | r.needs_accent
    return {w for w in (strip_marks(x) for x in re.findall(r"[^\W\d_]+", matched.lower())) if w in vocab}


def emergency_evidence_words(text: str) -> set[str]:
    """Hợp các từ-luật khớp được của MỌI luật cấp cứu (ATS 1-2 + thần kinh khu trú) trong cả tin nhắn.

    Sàn chứng cứ (mở rộng sàn 3 từ mà bác sĩ đã duyệt từ MỘT đoạn khớp ra cả tin nhắn): ≥ 3 từ-luật khác nhau từ
    các dấu hiệu độc lập ("lo mo" + "noi ngong") gần như không thể cùng trùng ngẫu nhiên → coi như chỉ thiếu dấu.
    """
    orig = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or ""))
    t = prepare(orig)
    words: set[str] = set()
    for ats, rid, r, _name, _spec in _COMPILED:
        if ats > 2:
            continue
        for m, _conf in _accepted(r, t, orig):
            if rid.endswith("SELF_HARM") and is_intensity_idiom(t, m.start(), m.group(0)):
                continue
            words |= rule_evidence_words(r, m.group(0))
    for name, r in _FOCAL.items():
        if name == "speech" and r_search(_THROAT, t):
            continue
        for m, _conf in _accepted(r, t, orig):
            inner = _strip(m.group(0))
            if name == "speech":
                inner = re.sub(r"(?:khong|ko) noi|noi khong", "", inner)
            elif name == "motor":
                inner = re.sub(r"(?:khong|ko) (?:nhac (?:len )?duoc|cu dong duoc|co duoc)", "", inner)
            if not _INNER_NEG.search(inner):
                words |= rule_evidence_words(r, m.group(0))
    return words


def r_search(r: AccentRule, t: str) -> bool:
    return bool(r.regex.search(t))


# Tím tái kèm khó thở (youmed.vn: suy hô hấp độ 2-3 "môi, đầu chi tím tái"; ACEM ATS 2).
_CYANOSIS = rule(
    r"(?<!\w)(?:môi|miệng|đầu ngón|ngón tay|ngón chân|đầu chi|móng tay|da|mặt|người|toàn thân)(?: \w+){0,2} tím"
    r"(?!\w)(?! (?:mạch|đập|phổi|nhanh))|tím tái|xanh tím"
)
_DYSPNEA = rule(r"\b(?:khó thở|thở gấp|thở nhanh|thở dốc|hụt hơi|thở không ra hơi|thở khò khè|ngộp thở)\b")


def _unnegated(r: AccentRule, t: str, orig: str) -> str | None:
    """Độ tin cậy của lần khớp đầu tiên không bị phủ định trước/bên trong ("môi không tím"), hoặc None."""
    for m, conf in _accepted(r, t, orig):
        if not _INNER_NEG.search(_strip(m.group(0))):
            return conf
    return None


def match_ats_descriptors(text: str) -> AtsDescriptorMatch | None:
    """Trả về mô tả ATS khẩn nhất (1-3) khớp với lời kể, hoặc None."""
    orig = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or ""))
    t = prepare(orig)
    found: list[AtsDescriptorMatch] = []
    for ats, rid, r, name, spec in _COMPILED:
        best: str | None = None  # lần khớp CHẮC CHẮN nhất của luật ("bất tĩnh… gọi không dậy" → lấy "gọi không dậy")
        for m, conf in _accepted(r, t, orig):
            if rid.endswith("SELF_HARM") and is_intensity_idiom(t, m.start(), m.group(0)):
                continue
            if best is None or _RANK[conf] < _RANK[best]:
                best = conf
            if conf == CERTAIN:
                break
        if best is not None:
            found.append(AtsDescriptorMatch(ats, rid, name, spec, best))
    if m := _INFANT.regex.search(t):
        conf = confidence(_INFANT, m.group(0))
        if m2 := _INFANT_CRITICAL.regex.search(t):
            found.append(AtsDescriptorMatch(1, "ATS1_INFANT_CRITICAL", "Trẻ sơ sinh thở yếu / tím tái", "Nhi khoa",
                                            worst(conf, confidence(_INFANT_CRITICAL, m2.group(0)))))  # fmt: skip
        elif m2 := _INFANT_UNWELL.regex.search(t):
            found.append(AtsDescriptorMatch(2, "ATS2_INFANT_UNWELL", "Trẻ dưới 3 tháng có dấu hiệu bệnh", "Nhi khoa",
                                            worst(conf, confidence(_INFANT_UNWELL, m2.group(0)))))  # fmt: skip
        else:
            found.append(AtsDescriptorMatch(3, "ATS3_NEONATE", "Trẻ sơ sinh", "Nhi khoa", conf))
    if (age := _AGE.search(t)) and int(age.group(1)) > 65 and (ab := _ABD_PAIN.regex.search(t)):
        conf = confidence(_ABD_PAIN, ab.group(0))
        # Người già đau bụng kèm đau nặng >= 8/10, sốt hoặc đau tăng dần: nguy cơ bụng ngoại khoa cao → ATS 2.
        if sev := _ELDERLY_ABD_SEVERE.regex.search(t):
            found.append(AtsDescriptorMatch(2, "ATS2_ABD_PAIN_ELDERLY_SEVERE", "Đau bụng nặng ở người trên 65 tuổi",
                                            "Tiêu hóa - Gan mật",
                                            worst(conf, confidence(_ELDERLY_ABD_SEVERE, sev.group(0)))))  # fmt: skip
        found.append(
            AtsDescriptorMatch(3, "ATS3_ABD_PAIN_ELDERLY", "Đau bụng ở người trên 65 tuổi", "Tiêu hóa - Gan mật", conf)
        )
    domains = _focal_domains(t, orig)
    if domains and not r_search(_FOCAL_CHRONIC, t) and (len(domains) >= 2 or r_search(_FOCAL_ACUTE, t)):
        found.append(
            AtsDescriptorMatch(
                2,
                "ATS2_ACUTE_FOCAL_NEURO",
                "Dấu hiệu thần kinh khu trú cấp (nghi đột quỵ / TIA)",
                "Thần kinh",
                worst(*domains.values()),
            )  # fmt: skip
        )
    if (c1 := _unnegated(_CYANOSIS, t, orig)) and (c2 := _unnegated(_DYSPNEA, t, orig)):
        found.append(
            AtsDescriptorMatch(
                2, "ATS2_CYANOSIS_DYSPNEA", "Khó thở kèm tím tái (suy hô hấp)", "Nội hô hấp", worst(c1, c2)
            )
        )
    found += [AtsDescriptorMatch(ats, rid, name, None) for ats, rid, name in _vitals(t)]
    if not found:
        return None
    # Khẩn nhất trước; cùng mức thì ưu tiên có chuyên khoa, rồi độ tin cậy cao hơn
    rank = {"certain": 0, "missing_accent": 1, "ambiguous": 2}
    return min(found, key=lambda m: (m.ats_level, m.specialty is None, rank.get(m.confidence, 0)))
