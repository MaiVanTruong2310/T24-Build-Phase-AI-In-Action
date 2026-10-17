"""Biến đổi cơ học, tất định (không LLM) sinh biến thể từ seed. Nhãn được KẾ THỪA nguyên vẹn.

Nguyên tắc giữ nhãn:
- Không đụng chữ số (SĐT, tuổi, nhiệt độ, ngày) và từ viết hoa đầu (tên riêng) → assertion trên dữ liệu
  người dùng cung cấp vẫn đúng.
- Mỗi phép chỉ đổi BỀ MẶT chữ, không đổi nghĩa; người đọc bình thường vẫn hiểu như bản gốc.
- RNG seed theo (id, transform) → chạy lại luôn ra cùng biến thể.
"""

from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from collections.abc import Callable

from schema import TURN_RE, Case

ZWSP = "\u200b"
# Latin → Cyrillic trông giống hệt (chỉ chữ không dấu)
HOMOGLYPHS = {
    "a": "\u0430",
    "e": "\u0435",
    "o": "\u043e",
    "c": "\u0441",
    "p": "\u0440",
    "x": "\u0445",
    "y": "\u0443",
    "i": "\u0456",
}
# Lượt chen vào giữa: trung tính, không triệu chứng, không xác nhận/từ chối, không hỏi thông tin.
FILLERS = ("chờ tôi một chút nhé", "xin lỗi, tôi vừa bận việc chút", "để tôi nhớ lại đã")
WORD = re.compile(r"\S+")


def strip_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _rng(case_id: str, name: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"{case_id}|{name}".encode()).hexdigest(), 16))


def _mutable(word: str) -> bool:
    """Từ được phép biến đổi: toàn chữ cái, ≥ 3 ký tự, không viết hoa đầu (tên riêng)."""
    core = word.strip(".,!?;:\"'()")
    return len(core) >= 3 and core.isalpha() and not core[0].isupper()


def _map_words(text: str, rng: random.Random, p: float, fn: Callable[[str, random.Random], str]) -> str:
    return WORD.sub(lambda m: fn(m.group(), rng) if _mutable(m.group()) and rng.random() < p else m.group(), text)


def _typo(word: str, rng: random.Random) -> str:
    letters = [i for i, c in enumerate(word) if c.isalpha()]
    if len(letters) < 4:
        return word
    i = rng.choice(letters[1:-2])  # tránh chữ đầu/cuối để từ vẫn đọc được
    w = list(word)
    if rng.random() < 0.5 and w[i + 1].isalpha():
        w[i], w[i + 1] = w[i + 1], w[i]  # đảo 2 chữ kề nhau
    else:
        del w[i]  # sót 1 chữ
    return "".join(w)


def _zero_width(word: str, rng: random.Random) -> str:
    i = rng.randint(1, len(word) - 1)
    return word[:i] + ZWSP + word[i:]


def _homoglyph(word: str, rng: random.Random) -> str:
    idx = [i for i, c in enumerate(word) if c in HOMOGLYPHS]
    if not idx:
        return word
    i = rng.choice(idx)
    return word[:i] + HOMOGLYPHS[word[i]] + word[i + 1 :]


def _partial_accent(word: str, rng: random.Random) -> str:
    """Bỏ dấu một từ (người gõ vội/bàn phím lỗi: câu lẫn có dấu và không dấu)."""
    return strip_diacritics(word)


def _voice(text: str) -> str:
    """Văn phong nhận dạng giọng nói: chữ thường, bỏ dấu câu (giữ số, dấu thập phân giữa 2 số)."""
    text = re.sub(r"(?<!\d)[.,](?!\d)|[!?;:\"()…]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _turnwise(fn: Callable[[str, random.Random], str]) -> Callable[[Case], Case]:
    def apply(case: Case) -> Case:
        rng = _rng(case.id, fn.__name__)
        return case.model_copy(update={"turns": [fn(t, rng) for t in case.turns]})

    return apply


def _shift(spec: str | int, at: int, k: int) -> str:
    """Dời chỉ số lượt ≥ at thêm k (sau khi chèn k lượt trước lượt `at`)."""
    s = str(spec)
    if s == "*":
        return s
    sh = lambda x: str(int(x) + k if int(x) >= at else int(x))  # noqa: E731
    if s.endswith("-"):
        return sh(s[:-1]) + "-"
    if "-" in s:
        a, b = s.split("-")
        return f"{sh(a)}-{sh(b)}"
    return sh(s)


def filler_gap(case: Case) -> Case | None:
    """Chèn 3 lượt trung tính ngay trước lượt cuối → đo trí nhớ khi khoảng cách tăng."""
    n = len(case.turns)
    if n < 2:
        return None
    at = n  # lượt cuối (đánh số từ 1) bị dời
    k = len(FILLERS)
    turns = [*case.turns[: at - 1], *FILLERS, *case.turns[at - 1 :]]
    exps = []
    for e in case.expectations:
        upd: dict = {"turn": _shift(e.turn, at, k)}  # "*" giữ nguyên: áp cho mọi lượt, gồm cả lượt chèn
        if isinstance(e.value, dict):
            m = re.match(r"^@(\d+):(.*)$", e.value["ref"])
            upd["value"] = {"ref": f"@{_shift(m.group(1), at, k)}:{m.group(2)}"}
        exps.append(e.model_copy(update=upd))
    assert all(TURN_RE.match(str(e.turn)) for e in exps)
    return case.model_copy(update={"turns": turns, "expectations": exps})


TRANSFORM_FNS: dict[str, Callable[[Case], Case | None]] = {
    "no_diacritics": _turnwise(lambda t, _r: strip_diacritics(t)),
    "typos": _turnwise(lambda t, r: _map_words(t, r, 0.2, _typo)),
    "zero_width": _turnwise(lambda t, r: _map_words(t, r, 0.35, _zero_width)),
    "homoglyph": _turnwise(lambda t, r: _map_words(t, r, 0.35, _homoglyph)),
    "upper": _turnwise(lambda t, _r: t.upper()),
    "voice": _turnwise(lambda t, _r: _voice(t)),
    "filler_gap": filler_gap,
    # ~50% số từ mất dấu (GĐ0 kế hoạch khớp có dấu: rủi ro bỏ sót với người gõ dấu nửa vời)
    "partial_accent": _turnwise(lambda t, r: _map_words(t, r, 0.5, _partial_accent)),
}


def make_variants(seed: Case) -> list[Case]:
    out = []
    for name, fn in TRANSFORM_FNS.items():
        if name in seed.perturb_deny:
            continue
        v = fn(seed)
        if v is None or v.turns == seed.turns:
            continue  # biến đổi không tạo khác biệt → bỏ, tránh trùng lặp
        data = v.model_dump()
        data.update(
            id=f"{seed.id}~{name}",
            origin="variant",
            parent_id=seed.id,
            transform=name,
            review_status="draft_unreviewed",  # biến thể không bao giờ tự thành "reviewed"
            annotator=None,
            annotator2=None,
        )
        out.append(Case.model_validate(data))  # validate lại toàn bộ sau biến đổi
    return out
