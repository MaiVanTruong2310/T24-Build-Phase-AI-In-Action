"""Mô tả lâm sàng theo thang ATS (ACEM 2023, Appendix A trong ETEK 2nd ed.) cho lời kể tiếng Việt.

Chỉ dùng để NÂNG mức khẩn cấp: trả về mức ATS khẩn nhất khớp được (1-3) hoặc None.
Văn bản được bỏ dấu trước khi khớp nên áp dụng cho cả câu có dấu lẫn không dấu.
Nguồn mô tả: Guidelines on the Implementation of the ATS in Emergency Departments, ACEM 2023.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt, giữ nguyên chữ hoa/thường và độ dài → dùng được cho cả regex pattern."""
    value = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text or ""))
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def _strip(text: str) -> str:
    return re.sub(r"\s+", " ", strip_accents((text or "").lower()))


_NEG_BEFORE = re.compile(r"(?:khong|chua|het|chang|ko|k)\s+(?:\w+\s+){0,2}$")


@dataclass(frozen=True)
class AtsDescriptorMatch:
    ats_level: int
    rule_id: str
    name: str
    specialty: str | None


# (ATS, rule_id, regex trên văn bản đã bỏ dấu, tên hiển thị, chuyên khoa gợi ý)
_RULES: list[tuple[int, str, str, str, str | None]] = [
    # --- ATS 1: đe dọa tính mạng tức thì ---
    (
        1,
        "ATS1_UNRESPONSIVE",
        r"bat tinh|goi (?:the nao )?(?:cung )?khong (?:tinh|day)|lay (?:goi )?(?:the nao )?(?:cung )?khong tinh"
        r"|khong (?:danh thuc|goi) (?:duoc|day)|khong (?:tinh )?day duoc|goi gan nhu khong tinh|mem oat",
        "Không đáp ứng / chỉ đáp ứng kích thích đau",
        "Cấp cứu",
    ),
    (
        1,
        "ATS1_HYPOVENTILATION",
        r"lau lau moi tho|tho (?:rat )?cham|tho ngap|thoi thop",
        "Thở chậm / thở ngáp",
        "Cấp cứu",
    ),
    (
        1,
        "ATS1_VIOLENCE",
        r"(?:rut|cam|vung|giu) (?:\w+ )?(?:dao|sung|kiem)|dam (?:chet|nguoi)|doa giet|dinh danh (?:moi )?nguoi",
        "Hành vi bạo lực đe dọa tức thì",
        "Cấp cứu",
    ),
    (
        1,
        "ATS1_CORD_PROLAPSE",
        r"day ron (?:thong|tho|sa|roi)|(?:sa|thay|thong) day ron|nhu day ron",
        "Sa dây rốn khi chuyển dạ",
        "Sản phụ khoa",
    ),
    # --- ATS 2: có thể đe dọa tính mạng trong 10 phút ---
    (
        2,
        "ATS2_VERY_SEVERE_PAIN",
        r"(?:dau|nhuc|buot)[^.;,]{0,40}?(?:\b(?:9|10)\s*/\s*10\b|du doi|kinh khung|khung khiep|toi do|khong chiu noi|phat khoc|nhat tu truoc)"
        r"|\b(?:9|10)\s*/\s*10\b",
        "Đau rất nặng",
        None,
    ),
    (
        2,
        "ATS2_CIRCULATORY_COMPROMISE",
        r"va mo hoi lanh|(?:da|nguoi) (?:tai )?lanh (?:va )?(?:am|va mo hoi)|tai lanh|lanh ngat|noi van tim",
        "Dấu hiệu tuần hoàn kém (da lạnh ẩm, vân tím)",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_SEVERE_RESP_DISTRESS",
        r"noi (?:duoc )?(?:vai|mot vai|\d|hai|ba) (?:chu|tu)[^.;]{0,15}(?:dung|nghi|tho)|khong noi (?:duoc )?(?:thanh )?cau"
        r"|tho (?:rat )?gang suc|co rut long nguc|ngoi (?:day|chong tay)[^.;]{0,10}tho|tho khong noi|tho hon hen"
        r"|tho khong (?:noi|ra hoi)|chay dai",
        "Suy hô hấp nặng",
        "Nội hô hấp",
    ),
    (
        2,
        "ATS2_FEVER_LETHARGY",
        r"\bsot\b[^.;]{0,60}\b(?:li bi|lo mo|lu du|lu dua)\b|\b(?:li bi|lo mo|lu du)\b[^.;]{0,60}\bsot\b",
        "Sốt kèm li bì",
        None,
    ),
    (
        2,
        "ATS2_DROWSY",
        r"\blo mo\b|\bli bi\b|\blu du\b|goi (?:moi|kho) (?:tinh|mo mat)|nham mat[^.;]{0,25}goi|kho danh thuc|danh thuc (?:moi|rat kho)"
        r"|mat phuong huong",
        "Giảm đáp ứng / lơ mơ",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_EYE_CHEMICAL",
        r"(?:hoa chat|axit|acid|kiem|xut|thuoc tay|voi|xi mang|nuoc tay)[^.;]{0,40}\bmat\b"
        r"|\bmat\b[^.;]{0,30}(?:hoa chat|axit|acid|xut|thuoc tay|voi bot)",
        "Hóa chất bắn vào mắt",
        "Mắt (Nhãn khoa)",
    ),
    (
        2,
        "ATS2_MAJOR_TRAUMA",
        r"xuong (?:loi|troi|dam) ra|loi (?:ca )?xuong|cut (?:roi )?(?:ngon|tay|chan|ban)|dut (?:roi )?(?:ngon|tay)",
        "Chấn thương khu trú nặng (gãy hở, cụt chi)",
        "Chấn thương chỉnh hình - Y học thể thao",
    ),
    (
        2,
        "ATS2_TESTICULAR_TORSION",
        r"xoan tinh hoan|(?:dau|sung) (?:tinh hoan|hon dai|bi)[^.;]{0,30}(?:dot ngot|du doi|tu nhien)"
        r"|(?:dot ngot|tu nhien)[^.;]{0,20}dau (?:tinh hoan|hon dai)",
        "Nghi xoắn tinh hoàn",
        "Thận - Tiết niệu",
    ),
    (
        2,
        "ATS2_ENVENOMATION",
        r"ran (?:doc )?can|bi ran|sua (?:bien )?(?:dot|can)|bo cap|nhen doc",
        "Động vật có nọc độc",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_TOXIC_EXPOSURE",
        r"(?:thuoc tru sau|thuoc diet co|hoa chat|thuoc chuot)[^.;]{0,80}(?:non|va mo hoi|kho tho|chong mat|co giat|lo mo)",
        "Phơi nhiễm chất độc có triệu chứng",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_FEBRILE_NEUTROPENIA",
        r"(?:hoa tri|truyen hoa chat|dieu tri ung thu)[^.;]{0,80}sot|sot[^.;]{0,80}hoa tri",
        "Sốt sau hóa trị",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_BURN_LARGE",
        r"bong[^.;]{0,40}(?:rong|ca (?:mat|hai)|hai (?:ben )?(?:dui|chan|tay)|nhieu cho|lon)",
        "Bỏng diện rộng",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_SEVERE_BLEEDING",
        r"(?:mau|chay mau)[^.;]{0,30}(?:khap san|o at|xoi xa|khong cam)",
        "Mất máu nặng",
        "Cấp cứu",
    ),
    (
        2,
        "ATS2_SELF_HARM_IMMINENT",
        # Quá liều: từ 10 viên trở lên ("vừa uống 2 viên paracetamol" không tính).
        r"(?:tu (?:lam hai|tu)|muon chet)[^.;]{0,60}(?:se lam (?:nua|tiep)|ngay khi|vua uong)|vua uong (?:[1-9]\d|\d{3}) vien",
        "Nguy cơ tự hại tức thì",
        "Cấp cứu",
    ),
    # --- ATS 3: có thể đe dọa tính mạng trong 30 phút ---
    (3, "ATS3_MODERATELY_SEVERE_PAIN", r"\b[78]\s*/\s*10\b", "Đau mức nặng vừa (7-8/10)", None),
    # Thành ngữ "đau bụng muốn chết" = đau rất nặng (không phải ý nghĩ tự sát).
    (3, "ATS3_SEVERE_PAIN_IDIOM", r"\b(?:dau|nhuc)\b[^.,;!?]{0,15}muon chet", "Đau rất nặng", None),
    (
        3,
        "ATS3_ACUTE_CONFUSION",
        r"(?:tu nhien|dot nhien|hom nay|bong nhien)[^.;]{0,20}(?:lu lan|lan lon|mat dinh huong)",
        "Lú lẫn cấp",
        "Thần kinh",
    ),
    (
        3,
        "ATS3_PERSISTENT_VOMITING",
        r"non (?:lien tuc|khong ngung|nhieu lan|[3-9] lan|hon \d+ lan)|uong gi non nay|non het",
        "Nôn kéo dài",
        None,
    ),
    # Mất nước chỉ khi đang nôn/tiêu chảy ("tiểu ít vì uống ít nước" không tính).
    (
        3,
        "ATS3_DEHYDRATION",
        r"^(?=.*(?:\bnon\b|tieu chay|di long|di ngoai))(?:.*?)(?:nuoc tieu sam|tieu (?:rat )?it|mieng kho|mat trung)",
        "Mất nước",
        None,
    ),
    (
        3,
        "ATS3_HEAD_INJURY_LOC",
        r"(?:dap dau|nga[^.;]{0,30}dau|chan thuong dau)[^.;]{0,60}(?:ngat|bat dong|mat y thuc)",
        "Chấn thương đầu có mất ý thức ngắn",
        "Thần kinh",
    ),
    (
        3,
        "ATS3_LIMB_INJURY",
        r"lech (?:han|di)|bien dang|vet rach sau|lo (?:ca )?gan|dap nat|cong veo",
        "Chấn thương chi mức vừa (biến dạng, rách sâu)",
        "Chấn thương chỉnh hình - Y học thể thao",
    ),
    (
        3,
        "ATS3_MODERATE_BLEEDING",
        r"(?:chay mau|ra mau)[^.;]{0,30}(?:nhieu|day)|day (?:ca )?bon cau",
        "Mất máu mức vừa",
        None,
    ),
    (
        3,
        "ATS3_PSYCHOSIS",
        r"ao giac|hoang tuong|tieng noi bao|noi chuyen mot minh|nghi (?:do an )?bi dau doc|phat tia|nguoi ngoai hanh tinh",
        "Loạn thần cấp",
        "Trung tâm chăm sóc sức khỏe tinh thần tích hợp",
    ),
    (
        3,
        "ATS3_SELF_HARM",
        r"tu (?:lam hai|tu|sat)|muon chet|rach tay|cat tay|vet cat[^.;]{0,15}co tay",
        "Nguy cơ tự hại",
        "Trung tâm chăm sóc sức khỏe tinh thần tích hợp",
    ),
    (
        3,
        "ATS3_CHILD_ABUSE_RISK",
        r"(?:be|con|tre)[^.;]{0,60}(?:vet bam|bam (?:xanh|tim|vang))",
        "Trẻ có vết bầm không rõ nguyên nhân",
        "Nhi khoa",
    ),
]
_COMPILED = [(ats, rid, re.compile(p), name, spec) for ats, rid, p, name, spec in _RULES]

_INFANT = re.compile(r"\b(?:\d+|mot|hai|ba|bon) tuan tuoi|\b[12] thang tuoi|so sinh|moi sinh")
_INFANT_CRITICAL = re.compile(r"tho yeu|tho bat thuong|xam|tim tai|ngung tho|mem oat")
_INFANT_UNWELL = re.compile(r"bu kem|bo bu|li bi|ngu (?:li bi|nhieu)|kho (?:danh thuc|tinh)|sot|lu du|tai|lanh")
_AGE = re.compile(r"\b(\d{2,3}) tuoi\b")
_ABD_PAIN = re.compile(r"dau bung|dau (?:da day|thuong vi)")


def _num(value: str) -> float:
    return float(value.replace(",", "."))


def _vitals(t: str) -> list[tuple[int, str, str]]:
    """Ngưỡng sinh hiệu ACEM (người lớn) khi bệnh nhân/người nhà tự nhắn số đo."""
    hits: list[tuple[int, str, str]] = []
    if m := re.search(r"(?:spo2|sp02|oxy|o2|bao hoa)[^\d]{0,20}(\d{2,3})\s*%?", t):
        v = _num(m.group(1))
        if v < 85:
            hits.append((1, "VITAL_SPO2_CRITICAL", f"SpO2 {v:.0f}%"))
        elif v <= 92:
            hits.append((2, "VITAL_SPO2_LOW", f"SpO2 {v:.0f}%"))
    if m := re.search(r"huyet ap[^\d]{0,20}(\d{2,3})\s*/\s*(\d{2,3})", t):
        sys_, dia = _num(m.group(1)), _num(m.group(2))
        if sys_ < 80:
            hits.append((1, "VITAL_BP_SHOCK", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
        elif sys_ < 90:
            hits.append((2, "VITAL_BP_LOW", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
        elif sys_ >= 180 or dia >= 110:
            hits.append((3, "VITAL_BP_SEVERE_HTN", f"Huyết áp {sys_:.0f}/{dia:.0f}"))
    if m := re.search(r"(?:mach|nhip tim|tim dap)[^\d]{0,20}(\d{2,3})", t):
        v = _num(m.group(1))
        if v > 150 or v < 50:
            hits.append((2, "VITAL_HR_EXTREME", f"Mạch {v:.0f}"))
    if m := re.search(r"nhip tho[^\d]{0,20}(\d{1,2})", t):
        v = _num(m.group(1))
        if v < 10:
            hits.append((1, "VITAL_RR_LOW", f"Nhịp thở {v:.0f}"))
        elif v >= 30:
            hits.append((2, "VITAL_RR_HIGH", f"Nhịp thở {v:.0f}"))
    if m := re.search(r"gcs[^\d]{0,4}(\d{1,2})", t):
        v = _num(m.group(1))
        if v < 9:
            hits.append((1, "VITAL_GCS_LT9", f"GCS {v:.0f}"))
        elif v < 13:
            hits.append((2, "VITAL_GCS_LT13", f"GCS {v:.0f}"))
        elif v < 15:
            hits.append((3, "VITAL_GCS_13_14", f"GCS {v:.0f}"))
    if m := re.search(r"duong (?:huyet|mau)[^\d]{0,20}(\d+(?:[.,]\d+)?)", t):
        if _num(m.group(1)) < 3:
            hits.append((2, "VITAL_BGL_LOW", "Hạ đường huyết"))
    return hits


_INTENSITY_IDIOM_BEFORE = re.compile(
    r"\b(?:dau|met|nhuc|ngua|nong|lanh|doi|khat|so|cuoi|buon ngu|chan|xot)\b[^.,;!?]{0,15}$"
)


def is_intensity_idiom(text: str, match_start: int, matched: str) -> bool:
    """ "đau bụng muốn chết", "mệt muốn chết" là thành ngữ chỉ mức độ, không phải ý nghĩ tự sát.

    "chan" (chán) chỉ tính khi là "chán ăn"/"ngán" kiểu cảm giác; "buồn chán muốn chết" vẫn là khí sắc trầm.
    """
    if not re.search(r"mu[oố]n\s+ch[eế]t", matched, re.IGNORECASE):
        return False
    prefix = _strip(text[:match_start])
    if re.search(r"\bbuon chan\b[^.,;!?]{0,15}$", prefix):
        return False
    return bool(_INTENSITY_IDIOM_BEFORE.search(prefix))


def match_ats_descriptors(text: str) -> AtsDescriptorMatch | None:
    """Trả về mô tả ATS khẩn nhất (1-3) khớp với lời kể, hoặc None."""
    t = _strip(text)
    found: list[AtsDescriptorMatch] = []
    for ats, rid, pattern, name, spec in _COMPILED:
        for m in pattern.finditer(t):
            if rid.endswith("SELF_HARM") and is_intensity_idiom(t, m.start(), m.group(0)):
                continue
            if not _NEG_BEFORE.search(t[: m.start()]):
                found.append(AtsDescriptorMatch(ats, rid, name, spec))
                break
    if _INFANT.search(t):
        if _INFANT_CRITICAL.search(t):
            found.append(AtsDescriptorMatch(1, "ATS1_INFANT_CRITICAL", "Trẻ sơ sinh thở yếu / tím tái", "Nhi khoa"))
        elif _INFANT_UNWELL.search(t):
            found.append(AtsDescriptorMatch(2, "ATS2_INFANT_UNWELL", "Trẻ dưới 3 tháng có dấu hiệu bệnh", "Nhi khoa"))
        else:
            found.append(AtsDescriptorMatch(3, "ATS3_NEONATE", "Trẻ sơ sinh", "Nhi khoa"))
    if (age := _AGE.search(t)) and int(age.group(1)) > 65 and _ABD_PAIN.search(t):
        found.append(
            AtsDescriptorMatch(3, "ATS3_ABD_PAIN_ELDERLY", "Đau bụng ở người trên 65 tuổi", "Tiêu hóa - Gan mật")
        )
    found += [AtsDescriptorMatch(ats, rid, name, None) for ats, rid, name in _vitals(t)]
    if not found:
        return None
    return min(found, key=lambda m: (m.ats_level, m.specialty is None))
