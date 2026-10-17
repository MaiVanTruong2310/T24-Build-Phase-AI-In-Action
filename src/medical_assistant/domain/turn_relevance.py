"""Nhận diện tin nhắn lạc đề / vô nghĩa chen vào giữa cuộc tư vấn ("tôi muốn đi chơi", "asdkjh qwe").

LLM là nguồn chính (trường `turn_relevance`). Các luật dưới đây chỉ dùng khi LLM lỗi nên cố ý thận trọng:
chỉ bắt câu rõ ràng không liên quan, tránh nuốt nhầm câu trả lời thật ("bình thường", "3 ngày nay", "không").
"""

from __future__ import annotations

import re
import unicodedata


def _fold(text: str) -> str:
    value = unicodedata.normalize("NFD", (text or "").lower())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d")
    return " ".join(value.split())


# Phụ âm đầu/cuối hợp lệ của âm tiết tiếng Việt (đã bỏ dấu) — từ không khớp là chuỗi gõ bậy ("asdkjh", "qwe").
_VI_SYLLABLE = re.compile(
    r"^(?:ngh|ng|nh|ch|tr|th|kh|ph|gh|gi|qu|[bcdghklmnpqrstvx])?"
    r"[aeiouy]{1,3}"
    r"(?:ng|nh|ch|[cmnpt])?$"
)
_COMMON_LATIN = {"ok", "hi", "hello", "bs", "sdt", "bhyt", "vinmec", "test", "alo", "ad", "bot"}


def is_gibberish(text: str) -> bool:
    """Chuỗi ký tự không thành từ tiếng Việt/Anh thông dụng (gõ bậy, ấn nhầm bàn phím)."""
    folded = _fold(text)
    if not folded or re.search(r"\d", folded):
        return False
    words = re.findall(r"[a-z]+", folded)
    if not words:
        return True  # chỉ có ký hiệu
    if len(words) == 1 and len(words[0]) <= 2:
        return False  # "ừ", "ok", "dạ" là câu trả lời ngắn hợp lệ
    invalid = [w for w in words if w not in _COMMON_LATIN and not _VI_SYLLABLE.match(w)]
    return len(invalid) / len(words) >= 0.6


# Câu nói về hoạt động thường ngày, không có nội dung sức khỏe: "tôi muốn đi chơi/đi ngủ/ăn thanh long".
_LEISURE = re.compile(
    r"^(?:toi|minh|em|tao|tui)?\s*(?:muon|thich|dinh|sap|dang|se|can)\s+"
    r"(?:di\s+)?(?:choi|ngu|an|uong|xem|nghe|hat|du lich|mua sam|mua|tam|nhau|cafe|ca phe|shopping|game|da bong)\b"
)
# Có các dấu hiệu này thì vẫn coi là liên quan (câu hỏi sức khỏe, trả lời câu hỏi, đặt lịch).
_HEALTH_OR_ANSWER = re.compile(
    r"\b(?:dau|sot|ho|met|kho|ngua|sung|non|oi|tieu|phan|mau|thuoc|benh|kham|bac si|bs|vien|lich|trieu chung|"
    r"kieng|co sao|duoc khong|co nen|nen|tot khong|anh huong|mat ngu|ngu khong duoc|khong ngu)\b"
)


def looks_off_topic(text: str) -> bool:
    folded = _fold(text)
    return bool(_LEISURE.search(folded)) and not _HEALTH_OR_ANSWER.search(folded) and not re.search(r"\d", folded)


def last_question(text: str) -> str | None:
    """Câu hỏi cuối cùng trong câu trả lời của bot (để hỏi lại khi người dùng lạc đề)."""
    body = (text or "").split("Khuyến cáo y tế")[0].split("**Khuyến cáo")[0]
    sentences = re.findall(r"[^.!?\n]*\?", body)
    question = sentences[-1].strip(" -•*\n") if sentences else ""
    return question or None
