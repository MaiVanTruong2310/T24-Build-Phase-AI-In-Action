"""Schema ca test hội thoại (seed JSONL) + kiểm tra chặt chẽ.

Mỗi ca = các lượt NGƯỜI DÙNG + danh sách assertion chấm trên state/câu trả lời sau từng lượt.
Không lưu câu trả lời mẫu của bot: bot được chạy lại thật (replay) mỗi lần đánh giá.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CATEGORIES = (
    "memory",  # trí nhớ hội thoại nhiều lượt
    "emergency",  # cấp cứu ATS 1-2 (phải bắt)
    "false_alarm",  # câu giống cấp cứu nhưng KHÔNG phải (không được báo động nhầm)
    "safety_rule",  # luật lâm sàng cứng: chẩn đoán, liều thuốc, 1 câu hỏi
    "adversarial",  # tấn công / prompt injection / thao túng
    "booking",  # đặt lịch, bác sĩ, đặt hộ
    "routing",  # phân tầng + chuyên khoa không cấp cứu
    "privacy",  # PII, thông tin người khác
    "scope",  # ngoài phạm vi, xã giao
    "info",  # câu hỏi thông tin dịch vụ (giờ khám, giá, BHYT, địa chỉ)
    "hitl",  # xin gặp người thật, khiếu nại, chuyển điều phối viên
)
SPLITS = ("dev", "test")
REVIEW = ("draft_unreviewed", "reviewed", "disputed")
TRANSFORMS = (
    "no_diacritics",
    "typos",
    "zero_width",
    "homoglyph",
    "upper",
    "voice",
    "filler_gap",
    "paraphrase",
    "partial_accent",
)
KINDS = ("emergency", "ats", "mentions_115", "compliance", "specialty", "state", "response", "honorific")
STATE_OPS = ("eq", "ne", "eq_norm", "in", "not_in", "exists", "absent", "empty", "not_empty", "contains", "matches")
ID_RE = re.compile(r"^[A-Z]{2,6}(?:-[A-Z0-9]{2,10})+$")
TURN_RE = re.compile(r"^(?:\*|\d+|\d+-|\d+-\d+)$")
REF_RE = re.compile(r"^@(\d+):([A-Za-z_][\w.\[\]-]*)$")
PATH_RE = re.compile(r"^[A-Za-z_]\w*(?:\.\w+|\[-?\d+\])*$")


def compile_regex(pattern: str) -> re.Pattern:
    """re.error không phải ValueError → pydantic sẽ không báo lỗi validate; đổi sang ValueError."""
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"regex hỏng {pattern!r}: {exc}") from exc


def parse_turns(spec: str | int, n_turns: int) -> list[int]:
    """'3' → [3]; '3-5' → [3,4,5]; '3-' → 3..cuối; '*' → mọi lượt. Đánh số từ 1."""
    s = str(spec)
    if not TURN_RE.match(s):
        raise ValueError(f"turn '{s}' sai cú pháp (dùng N, N-M, N-, *)")
    if s == "*":
        return list(range(1, n_turns + 1))
    if s.endswith("-"):
        return list(range(int(s[:-1]), n_turns + 1))
    if "-" in s:
        a, b = map(int, s.split("-"))
        return list(range(a, b + 1))
    return [int(s)]


class Expectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn: str | int = Field(description="lượt áp dụng: N, N-M, N-, *")
    kind: Literal[KINDS]  # type: ignore[valid-type]
    op: str | None = None
    path: str | None = None
    value: Any = None
    critical: bool = False  # vi phạm → exit code 1 (an toàn bệnh nhân)
    why: str = Field(min_length=8, description="căn cứ của kỳ vọng (luật/quy ước/nguồn)")

    @model_validator(mode="after")
    def _check(self) -> Expectation:  # noqa: C901
        k, op, v = self.kind, self.op, self.value
        if k in ("emergency", "mentions_115"):
            if not isinstance(v, bool) or op is not None:
                raise ValueError(f"{k}: value phải là bool, không có op")
        elif k == "ats":
            if op not in ("==", "<=", ">=", "in"):
                raise ValueError("ats: op ∈ ==, <=, >=, in")
            vals = v if isinstance(v, list) else [v]
            if op != "in" and isinstance(v, list):
                raise ValueError("ats: value list chỉ đi với op 'in'")
            if not vals or any(not isinstance(x, int) or not 1 <= x <= 5 for x in vals):
                raise ValueError("ats: value phải là ATS 1..5")
        elif k == "compliance":
            if v not in ("R2", "R3", "R4", "R5") or op is not None:
                raise ValueError("compliance: value ∈ R2 (chẩn đoán), R3 (liều), R4 (1 câu hỏi), R5 (mời đặt lịch)")
        elif k == "specialty":
            if op not in ("top1_in", "any_in", "not_any_in"):
                raise ValueError("specialty: op ∈ top1_in, any_in, not_any_in")
            if not isinstance(v, list) or not v or not all(isinstance(x, str) for x in v):
                raise ValueError("specialty: value là list mã/tên chuyên khoa")
        elif k == "state":
            if op not in STATE_OPS:
                raise ValueError(f"state: op ∈ {STATE_OPS}")
            if not self.path or not PATH_RE.match(self.path):
                raise ValueError("state: cần path hợp lệ, vd proxy_patient.patient_phone, last_listed_doctors[0].id")
            if op in ("exists", "absent", "empty", "not_empty"):
                if v is not None:
                    raise ValueError(f"state op {op} không nhận value")
            elif op in ("in", "not_in") and not isinstance(v, list):
                raise ValueError(f"state op {op} cần value list")
            elif op == "matches":
                compile_regex(str(v))
            if isinstance(v, dict):
                if set(v) != {"ref"} or not REF_RE.match(str(v["ref"])):
                    raise ValueError("value tham chiếu phải dạng {'ref': '@<lượt>:<path>'}")
        elif k == "response":
            if op not in ("matches", "not_matches") or not isinstance(v, str):
                raise ValueError("response: op ∈ matches, not_matches; value là regex")
            compile_regex(v)
        elif k == "honorific":
            if v not in ("anh", "chị", "anh/chị") or op is not None:
                raise ValueError("honorific: value ∈ anh, chị, anh/chị")
        if self.path and k != "state":
            raise ValueError("path chỉ dùng cho kind=state")
        return self


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    gender: Literal["male", "female"] | None = None


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: bool = False
    profile: Profile | None = None

    @model_validator(mode="after")
    def _profile_needs_auth(self) -> Context:
        if self.profile and not self.authenticated:
            raise ValueError("profile chỉ có khi authenticated=true (khách không có hồ sơ)")
        return self


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: Literal[CATEGORIES]  # type: ignore[valid-type]
    subcategory: str = Field(pattern=r"^[a-z][a-z0-9_]{2,40}$")
    split: Literal[SPLITS]  # type: ignore[valid-type]
    title: str = Field(min_length=8)
    rationale: str = Field(min_length=20, description="vì sao ca này tồn tại, đo năng lực gì")
    context: Context = Context()
    turns: list[str] = Field(min_length=1, max_length=40)
    expectations: list[Expectation] = Field(min_length=1)
    tags: list[str] = []
    source: str = Field(min_length=3)
    review_status: Literal[REVIEW]  # type: ignore[valid-type]
    annotator: str | None = None
    annotator2: str | None = None
    perturb_deny: list[Literal[TRANSFORMS]] = []  # type: ignore[valid-type]
    # chỉ có ở biến thể sinh tự động
    origin: Literal["seed", "variant"] = "seed"
    parent_id: str | None = None
    transform: str | None = None

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        base = v.split("~", 1)[0]
        if not ID_RE.match(base):
            raise ValueError(f"id '{v}' phải dạng PREFIX-XXX (chữ in hoa/số)")
        return v

    @field_validator("turns")
    @classmethod
    def _turns(cls, v: list[str]) -> list[str]:
        if any(not t.strip() for t in v):
            raise ValueError("lượt rỗng")
        return v

    @model_validator(mode="after")
    def _consistency(self) -> Case:
        n = len(self.turns)
        for e in self.expectations:
            idx = parse_turns(e.turn, n)
            if not idx or min(idx) < 1 or max(idx) > n:
                raise ValueError(f"{self.id}: expectation turn {e.turn} ngoài phạm vi 1..{n}")
            if isinstance(e.value, dict):
                ref_turn = int(REF_RE.match(e.value["ref"]).group(1))
                if ref_turn < 1 or ref_turn >= min(idx):
                    raise ValueError(f"{self.id}: ref @{ref_turn} phải trỏ về lượt TRƯỚC lượt chấm {e.turn}")
        if self.review_status == "reviewed" and not self.annotator:
            raise ValueError(f"{self.id}: reviewed cần tên annotator")
        if self.category == "emergency" and not any(
            e.critical and e.kind == "emergency" and e.value is True for e in self.expectations
        ):
            raise ValueError(f"{self.id}: ca emergency phải có assertion critical emergency=true")
        if self.category == "false_alarm" and not any(
            e.kind == "emergency" and e.value is False for e in self.expectations
        ):
            raise ValueError(f"{self.id}: ca false_alarm phải có assertion emergency=false")
        if self.origin == "seed" and (self.parent_id or self.transform):
            raise ValueError(f"{self.id}: seed không có parent_id/transform")
        if self.origin == "variant" and not (self.parent_id and self.transform):
            raise ValueError(f"{self.id}: variant cần parent_id + transform")
        return self
