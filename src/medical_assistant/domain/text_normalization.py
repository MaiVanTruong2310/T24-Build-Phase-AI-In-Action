"""Chuẩn hóa tin nhắn người dùng trước mọi bộ luật (cổng cấp cứu, router, phát hiện đặt hộ).

Chặn các cách né từ khóa mà người đọc vẫn hiểu nguyên nghĩa:
- ký tự vô hình (zero-width, soft hyphen, bidi mark) chèn giữa chữ: "méo m\u200biệng"
- chữ Cyrillic/Hy Lạp trông giống Latin trộn trong từ tiếng Việt: "\u0441ho" (\u0441 Cyrillic)
- dạng tương thích (chữ full-width, ký tự trình bày) → dạng chuẩn qua NFKC
- chữ tách bằng dấu chấm/gạch: "đ.a.u n.g.ự.c" → "đau ngực"
Bảng ký tự dùng chung với tường lửa bảo mật (security/deobfuscator.py).
"""

from __future__ import annotations

import re
import unicodedata

from src.medical_assistant.domain.security.deobfuscator import HOMOGLYPH_MAP, INVISIBLE_CHARS

ZWJ = "\u200d"
_HOMOGLYPHS = str.maketrans(HOMOGLYPH_MAP)
_WORD = re.compile(r"\w+")
# ≥ 3 chữ cái đơn nối bằng . - _ * · • (không gồm chữ số: giữ "37.8", "1.5")
_SPLIT_LETTERS = re.compile(r"(?<!\w)(?:[^\W\d_][.\-_*·•]){2,}[^\W\d_](?!\w)")


def _is_latin(ch: str) -> bool:
    return ch.isalpha() and unicodedata.name(ch, "").startswith("LATIN")


def _fix_mixed_word(match: re.Match) -> str:
    """Chỉ thay homoglyph trong từ TRỘN chữ Latin + chữ giống Latin, để không phá văn bản thuần Nga/Hy Lạp."""
    word = match.group()
    if any(c in HOMOGLYPH_MAP for c in word) and any(_is_latin(c) for c in word):
        return word.translate(_HOMOGLYPHS)
    return word


def _drop_invisible(text: str) -> str:
    # Giữ ZWJ nối emoji (👨\u200d⚕️); bỏ khi đứng sau chữ/số (dùng để né từ khóa)
    return "".join(
        ch
        for i, ch in enumerate(text)
        if ch not in INVISIBLE_CHARS or (ch == ZWJ and not (i and text[i - 1].isalnum()))
    )


# Phương ngữ / teencode → tiếng Việt chuẩn, CHỈ để so khớp luật (cổng cấp cứu, phủ định); không sửa tin nhắn
# được lưu/hiển thị. Không đưa từ đa nghĩa vào đây ("má" = mẹ / cái má, "răng" = sao / cái răng).
_DIALECT_WORDS = {
    "hổng": "không",
    "hem": "không",
    "khum": "không",
    "hok": "không",
    "ko": "không",
    "kh": "không",
    "tui": "tôi",
    "tớ": "tôi",
    "đc": "được",
    "dc": "được",
    "vs": "với",
    "ói": "nôn",
}
_DIALECT_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, sorted(_DIALECT_WORDS, key=len, reverse=True))) + r")\b", re.I
)
# "hông" = "không" (miền Nam) nhưng cũng là bộ phận cơ thể ("đau hông trái"): chỉ đổi khi KHÔNG đứng sau từ chỉ
# triệu chứng/vị trí và KHÔNG đứng trước bên/trái/phải.
_HONG_NEGATION = re.compile(
    r"(?<!\w)(?<!đau )(?<!nhức )(?<!mỏi )(?<!tê )(?<!sưng )(?<!bên )(?<!vùng )(?<!xương )(?<!khớp )(?<!eo )"
    r"(?<!mạn )(?<!ở )(?<!hai )(?<!cạnh )(?<!quanh )(?<!ngang )(?<!bầm )(?<!lệch )"
    r"hông(?!\w)(?!\s+(?:trái|phải|bên|hai|lưng|chậu|sườn|đùi))",
    re.I,
)


def canonicalize_for_matching(text: str) -> str:
    """Bản tiếng Việt chuẩn của tin nhắn để bộ luật tất định hiểu phương ngữ ("tui hông muốn sống" →
    "tôi không muốn sống"). Chỉ dùng nội bộ khi so khớp; idempotent."""
    if not text:
        return text
    text = _HONG_NEGATION.sub("không", text)
    return _DIALECT_RE.sub(lambda m: _DIALECT_WORDS[m.group(1).lower()], text)


def normalize_user_message(text: str) -> str:
    """Chuẩn hóa không đổi nghĩa; idempotent (gọi lại cho cùng kết quả)."""
    if not text:
        return text
    text = unicodedata.normalize("NFKC", text)
    text = _drop_invisible(text)
    text = _WORD.sub(_fix_mixed_word, text)
    text = _SPLIT_LETTERS.sub(lambda m: re.sub(r"[.\-_*·•]", "", m.group()), text)
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"[ \t]+", " ", text).strip()
