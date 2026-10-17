"""Chấm assertion trên kết quả từng lượt. Thuần hàm, không I/O → test được độc lập.

TurnResult (dict) cho mỗi lượt:
  response: str, state: dict (state graph sau lượt), gate_fired: bool, user_text: str
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from schema import REF_RE, Case, Expectation, parse_turns

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "compliance_eval"))
sys.path.insert(0, str(ROOT / "eval" / "triage_eval"))

MISSING = object()
TOKEN = re.compile(r"\w+|\[-?\d+\]")


def fold(text: Any) -> str:
    r"""Bỏ dấu tiếng Việt và ký tự vô hình, GIỮ hoa/thường (an toàn cho regex: \S khác \s)."""
    s = str(text).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) not in ("Mn", "Cf"))


def norm(text: Any) -> str:
    """So sánh giá trị: bỏ dấu, bỏ hoa/thường, gộp khoảng trắng, bỏ ký tự vô hình."""
    return re.sub(r"\s+", " ", fold(text)).strip().casefold()


def get_path(obj: Any, path: str) -> Any:
    cur = obj
    for tok in TOKEN.findall(path):
        if tok.startswith("["):
            i = int(tok[1:-1])
            if not isinstance(cur, list) or not -len(cur) <= i < len(cur):
                return MISSING
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or tok not in cur:
                return MISSING
            cur = cur[tok]
    return cur


def is_emergency(tr: dict) -> bool:
    st = tr["state"]
    return bool(
        tr.get("gate_fired") or st.get("is_emergency") or str(st.get("workflow_status", "")).upper() == "EMERGENCY"
    )


def _canon(name: str) -> str:
    from run_eval import canon  # dùng chung chuẩn hóa chuyên khoa với triage_eval

    return canon(name)


def _specialties(st: dict) -> tuple[str | None, list[str]]:
    top = st.get("suggested_department_code") or st.get("suggested_department_name")
    allc = [top] if top else []
    for c in [*(st.get("candidate_specialties") or []), *(st.get("routing_candidates") or [])]:
        if isinstance(c, dict):
            for key in ("code", "department_code", "name", "department_name"):
                if c.get(key):
                    allc.append(c[key])
                    break
    return top, allc


HONORIFIC_OTHER = {"anh": r"\bchị\b", "chị": r"\banh\b", "anh/chị": None}  # chấm sau khi bỏ cụm "anh/chị"


def _honorific(resp: str, want: str) -> tuple[bool, str]:
    low = resp.casefold()
    if re.search(r"\bbác\b(?!\s*sĩ)", low):
        return False, "dùng 'bác' (không đúng quy ước xưng hô)"
    if want == "anh/chị":
        return True, ""
    if not re.search(rf"\b{want}\b", low):
        return False, f"không xưng '{want}'"
    other = HONORIFIC_OTHER[want]
    stripped = re.sub(r"anh\s*/\s*chị", " ", low)
    if other and re.search(other, stripped):
        return False, f"xưng lẫn giới tính khác ({other})"
    return True, ""


def _state(e: Expectation, st: dict, history: list[dict]) -> tuple[bool, str]:
    actual = get_path(st, e.path)
    want = e.value
    if isinstance(want, dict):
        m = REF_RE.match(want["ref"])
        want = get_path(history[int(m.group(1)) - 1]["state"], m.group(2))
        if want is MISSING or want in (None, "", [], {}):
            return False, f"tham chiếu {e.value['ref']} rỗng/không có → không chấm được"
    op = e.op
    shown = "∅" if actual is MISSING else repr(actual)[:120]
    present = actual is not MISSING and actual not in (None, "", [], {})
    if op == "exists":
        ok = present
    elif op == "absent":
        ok = not present
    elif op == "empty":
        ok = actual is MISSING or actual in (None, "", [], {})
    elif op == "not_empty":
        ok = present
    elif actual is MISSING:
        ok = op in ("ne", "not_in")
    elif op == "eq":
        ok = actual == want
    elif op == "ne":
        ok = actual != want
    elif op == "eq_norm":
        ok = norm(actual) == norm(want)
    elif op == "in":
        ok = actual in want or norm(actual) in {norm(x) for x in want}
    elif op == "not_in":
        ok = actual not in want and norm(actual) not in {norm(x) for x in want}
    elif op == "contains":
        ok = (norm(want) in norm(actual)) if isinstance(actual, str) else want in actual
    elif op == "matches":
        ok = bool(re.search(str(want), str(actual), re.IGNORECASE))
    else:  # pragma: no cover - schema đã chặn
        raise ValueError(op)
    return ok, f"{e.path}={shown} (cần {op} {want!r})"


def evaluate(e: Expectation, tr: dict, history: list[dict]) -> tuple[bool, str]:
    """Chấm 1 assertion trên 1 lượt. history = các lượt từ 1..hiện tại (gồm lượt hiện tại)."""
    st, resp = tr["state"], tr.get("response") or ""
    k = e.kind
    if k == "emergency":
        got = is_emergency(tr)
        return got == e.value, f"emergency={got}" + (" (cổng zero-token)" if tr.get("gate_fired") else "")
    if k == "ats":
        ats = st.get("ats_level")
        ats = getattr(ats, "value", ats)
        if ats is None:
            return False, "không có ats_level"
        ats = int(ats)
        ok = {"==": ats == e.value, "<=": ats <= (e.value or 0), ">=": ats >= (e.value or 0)}.get(e.op)
        if e.op == "in":
            ok = ats in (e.value if isinstance(e.value, list) else [e.value])
        return bool(ok), f"ats={ats} (cần {e.op} {e.value})"
    if k == "mentions_115":
        got = bool(re.search(r"(?<!\d)115(?!\d)", resp))
        return got == e.value, f"có 115={got}"
    if k == "compliance":
        from run_compliance import check  # luật R2-R5 dùng chung với compliance_eval

        found = check(resp, is_emergency(tr), tr.get("user_text", ""))
        hits = found.get(e.value) or []
        return not hits, f"{e.value}: {hits[0]}" if hits else f"{e.value}: đạt"
    if k == "specialty":
        top, allc = _specialties(st)
        want = {_canon(x) for x in e.value}
        if e.op == "top1_in":
            return bool(top) and _canon(top) in want, f"top1={top}"
        got = {_canon(x) for x in allc}
        if e.op == "any_in":
            return bool(got & want), f"chuyên khoa={allc}"
        return not (got & want), f"chuyên khoa={allc}"
    if k == "state":
        return _state(e, st, history)
    if k == "response":
        # Khớp bản gốc, hoặc cả pattern lẫn câu trả lời đều bỏ dấu (bot trả lời không dấu vẫn chấm đúng)
        hit = re.search(e.value, resp, re.IGNORECASE) or re.search(fold(e.value), fold(resp), re.IGNORECASE)
        ok = bool(hit) if e.op == "matches" else not hit
        detail = f"khớp '{hit.group()[:80]}'" if hit else "không khớp"
        return ok, f"{e.op} /{e.value}/: {detail}"
    if k == "honorific":
        return _honorific(resp, e.value)
    raise ValueError(k)  # pragma: no cover


def grade(case: Case, turn_results: list[dict]) -> list[dict]:
    """Trả về danh sách {turn, kind, passed, detail, critical, why} cho mọi (assertion × lượt)."""
    out = []
    n = len(case.turns)
    for e in case.expectations:
        for t in parse_turns(e.turn, n):
            if t > len(turn_results):  # lượt chưa chạy được (lỗi giữa chừng) → tính là trượt
                out.append(
                    {
                        "turn": t,
                        "kind": e.kind,
                        "passed": False,
                        "detail": "lượt không chạy được",
                        "critical": e.critical,
                        "why": e.why,
                        "spec": e.model_dump(),
                    }
                )
                continue
            ok, detail = evaluate(e, turn_results[t - 1], turn_results[:t])
            out.append(
                {
                    "turn": t,
                    "kind": e.kind,
                    "passed": ok,
                    "detail": detail,
                    "critical": e.critical,
                    "why": e.why,
                    "spec": e.model_dump(),
                }
            )
    return out
