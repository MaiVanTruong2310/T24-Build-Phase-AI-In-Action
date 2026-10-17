"""Biên dịch luật viết CÓ DẤU thành regex "dấu là ràng buộc" + phân độ tin cậy cho mỗi lần khớp.

Tiếng Việt có hai lớp dấu: dấu chữ (ă â ê ô ơ ư đ) và dấu thanh (sắc huyền hỏi ngã nặng). Mỗi chữ trong luật khớp
mọi chữ có TẬP DẤU CON của nó: "ự" khớp ự/ư/ụ/u, "ắ" khớp ắ/ă/á/a, "đ" khớp đ/d; chữ không dấu chỉ khớp chính nó.
  - Dấu người dùng ĐÃ gõ phải đúng: "mất" ≠ "mắt", "với" ≠ "vôi", "từ từ" ≠ "tự tử", "cảm" ≠ "cầm", "rạn" ≠ "rắn".
  - Dấu người dùng bỏ (không dấu / dấu nửa vời / thiếu thanh: "ngưc", "dau") = chưa biết → vẫn khớp, không bỏ sót.
Độ tin cậy của một lần khớp (chỉ dùng để PHÂN ĐỘ, không bao giờ để loại):
  - CERTAIN: mọi chữ của đoạn khớp mang đủ dấu như luật.
  - MISSING: có chữ thiếu dấu nhưng âm tiết trơn đó không thể là một từ (vd "mat", "nguc", "giat": âm tiết tắc
    -p/-t/-c/-ch không mang thanh ngang) → coi như chắc chắn.
  - AMBIGUOUS: có âm tiết trơn vốn là từ có nghĩa khác ("voi", "lo", "bong", "tim", "tu") → vẫn nâng mức;
    GĐ2 xử lý bằng câu hỏi xác nhận. Danh sách từ trơn: vi_plain_words.py (sinh từ kho văn bản có dấu, bác sĩ duyệt).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from src.medical_assistant.domain.vi_plain_words import AMBIGUOUS_BARE

CERTAIN, MISSING, AMBIGUOUS = "certain", "missing_accent", "ambiguous"
_RANK = {CERTAIN: 0, MISSING: 1, AMBIGUOUS: 2}

_MODIFIERS = {"̆", "̂", "̛"}  # trăng (ă), mũ (â ê ô), móc (ơ ư)
_TONES = {"̀", "́", "̃", "̉", "̣"}  # huyền, sắc, ngã, hỏi, nặng
_STROKE = "STROKE"  # đ = d + gạch ngang (Unicode không tách được)


def _marks(ch: str) -> tuple[str, frozenset[str]]:
    """(chữ gốc, tập dấu) của một chữ thường."""
    if ch == "đ":
        return "d", frozenset({_STROKE})
    d = unicodedata.normalize("NFD", ch)
    return d[0], frozenset(d[1:])  # giữ MỌI dấu: chữ có dấu ngoài tiếng Việt (ǻ, ā) sẽ bị loại khỏi bảng chữ


def _alphabet() -> dict[str, list[str]]:
    """Mọi chữ thường tiếng Việt theo chữ gốc."""
    out: dict[str, list[str]] = {}
    for base in "aeiouyd":
        out.setdefault(base, [base])
    for cp in range(0x00C0, 0x1EFF + 1):
        ch = chr(cp).lower()
        if len(ch) != 1 or not ch.isalpha():
            continue
        base, marks = _marks(ch)
        if base in "aeiouyd" and marks and marks <= (_MODIFIERS | _TONES | {_STROKE}):
            if ch not in out.setdefault(base, [base]):
                out[base].append(ch)
    return out


_ALPHA = _alphabet()


_HOOK, _TILDE = "̉", "̃"


@lru_cache(maxsize=4096)
def char_class(ch: str) -> str:
    """Các chữ người dùng có thể gõ cho chữ `ch` của luật (tập dấu con).

    Hỏi ↔ ngã coi như nhau: nhầm hỏi/ngã là lỗi chính tả rất phổ biến (nhất là giọng Nam: "bất tĩnh" = "bất tỉnh");
    ưu tiên không bỏ sót hơn phân biệt vài cặp hiếm gặp trong luật cấp cứu.
    """
    base, marks = _marks(ch)
    if not marks or base not in _ALPHA:
        return ch
    allowed = [marks]
    if _HOOK in marks:
        allowed.append((marks - {_HOOK}) | {_TILDE})
    elif _TILDE in marks:
        allowed.append((marks - {_TILDE}) | {_HOOK})
    return "".join(c for c in _ALPHA[base] if any(_marks(c)[1] <= a for a in allowed))


def compile_rule(pattern: str, flags: int = 0) -> re.Pattern:
    """Đổi mỗi chữ có dấu (ngoài escape) thành lớp ký tự tập-dấu-con. Giữ nguyên cú pháp regex."""
    out, i, in_class = [], 0, False
    pattern = unicodedata.normalize("NFC", pattern)
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if c == "[" and not in_class:
            in_class = True
        elif c == "]" and in_class:
            in_class = False
        alts = char_class(c) if c.isalpha() else c
        out.append(alts if in_class or len(alts) == 1 else f"[{alts}]")
        i += 1
    return re.compile("".join(out), flags)


def prepare(text: str) -> str:
    """Văn bản để khớp: NFC, chữ thường, gộp khoảng trắng (giữ nguyên dấu)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "").lower())


def _bare(word: str) -> bool:
    return all(_marks(c)[1] == frozenset() for c in word)


def strip_marks(word: str) -> str:
    return "".join(_marks(c)[0] if c.isalpha() else c for c in unicodedata.normalize("NFC", word))


def _rule_words(pattern: str) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """(từ không dấu viết thẳng trong luật, bản bỏ dấu của các từ CÓ dấu, các từ có dấu nguyên dạng)."""
    text = re.sub(r"\\.", " ", unicodedata.normalize("NFC", pattern).lower())
    words = re.findall(r"[^\W\d_]+", text)
    accented = frozenset(w for w in words if not _bare(w))
    return frozenset(w for w in words if _bare(w)), frozenset(strip_marks(w) for w in accented), accented


def _swap_hook_tilde(word: str) -> str:
    d = unicodedata.normalize("NFD", word)
    return unicodedata.normalize("NFC", d.translate({ord(_HOOK): _TILDE, ord(_TILDE): _HOOK}))


@dataclass(frozen=True)
class AccentRule:
    pattern: str
    regex: re.Pattern
    plain_words: frozenset[str]
    needs_accent: frozenset[str]  # bản trơn của từ luật cần dấu ("mat" ← "mắt")
    accented_words: frozenset[str] = frozenset()  # từ có dấu của luật ("tỉnh") để nhận ra khớp nhờ đổi hỏi/ngã


def rule(pattern: str, flags: int = 0) -> AccentRule:
    plain, needs, accented = _rule_words(pattern)
    return AccentRule(pattern, compile_rule(pattern, flags), plain, needs, accented)


def confidence(r: AccentRule, matched: str) -> str:
    """Phân độ một đoạn đã khớp: chỉ xét chữ trơn đứng ở vị trí một từ CẦN DẤU của luật (bỏ qua chữ rơi vào
    khoảng wildcard như [^.;]{0,40}, và chữ luật vốn viết không dấu như "co" trong "co giật")."""
    level = CERTAIN
    swap_used = False
    words = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", matched).lower())
    for w in words:
        # Khớp nhờ đổi hỏi ↔ ngã ("bất tĩnh" cho "bất tỉnh"): bác sĩ duyệt "đúng từng trường hợp" → để LLM xét ngữ cảnh
        if not _bare(w) and w not in r.accented_words and _swap_hook_tilde(w) in r.accented_words:
            level, swap_used = AMBIGUOUS, True
            continue
        if not _bare(w) or w in r.plain_words or w not in r.needs_accent:
            continue
        # Chữ trơn ở chỗ luật cần dấu: là từ khác ("voi") hoặc có nhiều cách thêm dấu ("mat" = mắt/mất/mặt, "kiem")
        # → mơ hồ; chỉ một cách thêm dấu ("nguc" → ngực) → thiếu dấu.
        cand = AMBIGUOUS if w in AMBIGUOUS_BARE else MISSING
        if _RANK[cand] > _RANK[level]:
            level = cand
    # Sàn: đoạn khớp chứa ≥ 3 từ của chính luật ("dau nguc du doi", "goi khong day") gần như không thể trùng ngẫu
    # nhiên (các lần trùng đo được đều chỉ 2 từ: "voi … mat", "lo mo", "cam … sung") → coi như chỉ thiếu dấu.
    if level == AMBIGUOUS and not swap_used:
        vocab = r.plain_words | r.needs_accent
        if sum(1 for w in words if strip_marks(w) in vocab) >= 3:
            level = MISSING
    return level


def worst(*levels: str) -> str:
    return max(levels, key=_RANK.__getitem__) if levels else CERTAIN
