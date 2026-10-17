"""Test bộ công cụ bench (schema, biến đổi, chấm, build). Không gọi agent/LLM/DB.

python -m pytest eval/conversation_bench/tests -q -p no:cacheprovider
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from assertions import evaluate, get_path, grade, norm  # noqa: E402
from build_db import build, cross_checks, load_seeds  # noqa: E402
from perturb import FILLERS, TRANSFORM_FNS, make_variants  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from schema import Case, Expectation, parse_turns  # noqa: E402

DIGITS = re.compile(r"\d+")


def case(**kw) -> Case:
    base = {
        "id": "TST-CASE-001",
        "category": "memory",
        "subcategory": "test_case",
        "split": "dev",
        "title": "ca kiểm thử công cụ",
        "rationale": "dùng để kiểm thử bộ công cụ bench",
        "turns": ["Tôi tên Phạm Thị Lan, số 0903123456", "đau đầu từ hôm qua", "đặt lịch giúp tôi"],
        "expectations": [{"turn": "3", "kind": "emergency", "value": False, "why": "kiểm thử ổn định"}],
        "source": "test",
        "review_status": "draft_unreviewed",
    }
    base.update(kw)
    return Case.model_validate(base)


def tr(response="", gate=False, **state):
    return {"response": response, "state": state, "gate_fired": gate, "user_text": ""}


# ------------------------------------------------------------------ schema
class TestSchema:
    def test_parse_turns(self):
        assert parse_turns("*", 3) == [1, 2, 3]
        assert parse_turns("2-", 4) == [2, 3, 4]
        assert parse_turns("1-2", 4) == [1, 2]
        with pytest.raises(ValueError):
            parse_turns("a", 3)

    @pytest.mark.parametrize(
        "bad",
        [
            {"turn": "1", "kind": "ats", "op": "<", "value": 2, "why": "op không hợp lệ"},
            {"turn": "1", "kind": "ats", "op": "<=", "value": 7, "why": "ats ngoài 1..5"},
            {"turn": "1", "kind": "emergency", "value": "yes", "why": "value không phải bool"},
            {"turn": "1", "kind": "state", "op": "eq", "path": "a b", "value": 1, "why": "path sai cú pháp"},
            {"turn": "1", "kind": "response", "op": "matches", "value": "(", "why": "regex hỏng"},
            {"turn": "1", "kind": "compliance", "value": "R9", "why": "luật không tồn tại"},
            {"turn": "1", "kind": "emergency", "value": True, "why": "ngắn"},
            {"turn": "1", "kind": "emergency", "value": True, "why": "trường lạ bị cấm", "extra": 1},
        ],
    )
    def test_rejects_bad_expectation(self, bad):
        with pytest.raises(ValidationError):
            Expectation.model_validate(bad)

    def test_turn_out_of_range(self):
        with pytest.raises(ValidationError):
            case(expectations=[{"turn": "5", "kind": "emergency", "value": False, "why": "ngoài phạm vi"}])

    def test_ref_must_point_backwards(self):
        exp = {
            "turn": "2",
            "kind": "state",
            "op": "eq",
            "path": "x",
            "value": {"ref": "@2:y"},
            "why": "tham chiếu chính lượt chấm",
        }
        with pytest.raises(ValidationError):
            case(expectations=[exp])

    def test_emergency_case_needs_critical_assertion(self):
        with pytest.raises(ValidationError):
            case(category="emergency")

    def test_reviewed_needs_annotator(self):
        with pytest.raises(ValidationError):
            case(review_status="reviewed")

    def test_guest_cannot_have_profile(self):
        with pytest.raises(ValidationError):
            case(context={"authenticated": False, "profile": {"name": "A"}})


# ------------------------------------------------------------------ perturb
class TestPerturb:
    def test_deterministic(self):
        c = case()
        assert [v.model_dump() for v in make_variants(c)] == [v.model_dump() for v in make_variants(c)]

    @pytest.mark.parametrize("name", [n for n in TRANSFORM_FNS if n != "filler_gap"])
    def test_digits_and_labels_preserved(self, name):
        c = case()
        v = TRANSFORM_FNS[name](c)
        assert [DIGITS.findall(t) for t in v.turns] == [DIGITS.findall(t) for t in c.turns]
        assert v.expectations == c.expectations
        assert len(v.turns) == len(c.turns)

    @pytest.mark.parametrize("name", ["typos", "zero_width", "homoglyph"])
    def test_proper_nouns_untouched(self, name):
        v = TRANSFORM_FNS[name](case(turns=["Phạm Thị Lan Nguyễn Văn Bình đau đầu chóng mặt buồn nôn"] * 3))
        for t in v.turns:
            assert t.startswith("Phạm Thị Lan Nguyễn Văn Bình")

    def test_filler_gap_remaps_turns_and_refs(self):
        exps = [
            {"turn": "1", "kind": "emergency", "value": False, "why": "lượt đầu giữ nguyên"},
            {
                "turn": "3",
                "kind": "state",
                "op": "eq",
                "path": "x",
                "value": {"ref": "@2:y"},
                "why": "tham chiếu được dời",
            },
            {"turn": "2-", "kind": "compliance", "value": "R4", "why": "khoảng mở rộng"},
        ]
        v = TRANSFORM_FNS["filler_gap"](case(expectations=exps))
        k = len(FILLERS)
        assert len(v.turns) == 3 + k and v.turns[-1] == "đặt lịch giúp tôi" and v.turns[2 : 2 + k] == list(FILLERS)
        got = [str(e.turn) for e in v.expectations]
        assert got == ["1", str(3 + k), "2-"]
        assert v.expectations[1].value == {"ref": "@2:y"}

    def test_variants_inherit_split_and_never_reviewed(self):
        c = case(split="test", review_status="reviewed", annotator="bs A")
        for v in make_variants(c):
            assert v.split == "test" and v.review_status == "draft_unreviewed" and v.parent_id == c.id

    def test_perturb_deny(self):
        names = {v.transform for v in make_variants(case(perturb_deny=["typos", "upper"]))}
        assert "typos" not in names and "upper" not in names


# ------------------------------------------------------------------ assertions
def exp(**kw) -> Expectation:
    kw.setdefault("why", "kiểm thử bộ chấm")
    return Expectation.model_validate(kw)


class TestAssertions:
    def test_norm(self):
        assert norm("Phạm  Thị\u200bLan") == norm("pham thilan")
        assert norm("ĐẶNG") == "dang"

    def test_get_path(self):
        st = {"a": {"b": [{"c": 1}]}}
        assert get_path(st, "a.b[0].c") == 1
        assert get_path(st, "a.b[-1].c") == 1
        assert get_path(st, "a.b[3].c") is not None and get_path(st, "a.x") is not None  # MISSING sentinel

    def test_emergency_gate_or_state(self):
        e = exp(turn="1", kind="emergency", value=True)
        assert evaluate(e, tr(gate=True), [])[0]
        assert evaluate(e, tr(workflow_status="EMERGENCY"), [])[0]
        assert not evaluate(e, tr(is_emergency=False), [])[0]

    def test_ats(self):
        assert evaluate(exp(turn="1", kind="ats", op="<=", value=2), tr(ats_level=2), [])[0]
        assert not evaluate(exp(turn="1", kind="ats", op="<=", value=2), tr(ats_level=3), [])[0]
        assert not evaluate(exp(turn="1", kind="ats", op=">=", value=4), tr(), [])[0]  # thiếu ats = trượt

    def test_mentions_115_exact_number(self):
        e = exp(turn="1", kind="mentions_115", value=True)
        assert evaluate(e, tr("Gọi ngay 115."), [])[0]
        assert not evaluate(e, tr("Gọi 1150 hoặc 01159"), [])[0]

    def test_compliance_dose(self):
        e = exp(turn="1", kind="compliance", value="R3")
        assert not evaluate(e, tr("Cháu uống paracetamol 250 mg mỗi 6 giờ."), [])[0]
        assert evaluate(e, tr("Em không kê đơn hay tư vấn liều thuốc, anh/chị hỏi bác sĩ nhé."), [])[0]

    def test_state_ops_and_ref(self):
        hist = [tr(last_listed_doctors=[{"full_name": "Lê Văn Bình"}]), tr(doctor_name="le van binh")]
        e = exp(
            turn="2",
            kind="state",
            op="eq_norm",
            path="doctor_name",
            value={"ref": "@1:last_listed_doctors[0].full_name"},
        )
        assert evaluate(e, hist[1], hist)[0]
        empty = [tr(), tr(doctor_name="x")]
        assert not evaluate(e, empty[1], empty)[0]  # ref rỗng → trượt, không im lặng đạt
        assert evaluate(exp(turn="1", kind="state", op="ne", path="p.q", value="1"), tr(), [])[0]
        assert not evaluate(exp(turn="1", kind="state", op="eq", path="p.q", value="1"), tr(), [])[0]
        assert evaluate(exp(turn="1", kind="state", op="absent", path="p"), tr(p=""), [])[0]

    def test_response_matches_with_or_without_diacritics(self):
        e = exp(turn="1", kind="response", op="matches", value="cho con bú")
        assert evaluate(e, tr("Vì chị đang cho con bú..."), [])[0]
        assert evaluate(e, tr("vi chi dang cho con bu"), [])[0]

    def test_honorific(self):
        e = exp(turn="1", kind="honorific", value="anh")
        assert evaluate(e, tr("Dạ anh nên khám Nội tiết, bác sĩ sẽ tư vấn."), [])[0]
        assert not evaluate(e, tr("Dạ bác nên khám Nội tiết."), [])[0]
        assert not evaluate(e, tr("Dạ chị nên khám."), [])[0]
        assert evaluate(e, tr("Dạ anh/chị và anh nên khám."), [])[0]
        assert not evaluate(e, tr("Dạ bạn nên khám."), [])[0]

    def test_grade_missing_turns_fail(self):
        c = case(expectations=[{"turn": "*", "kind": "emergency", "value": False, "why": "mọi lượt"}])
        g = grade(c, [tr()])
        assert [x["passed"] for x in g] == [True, False, False]


# ------------------------------------------------------------------ seeds + build
class TestSeedsAndBuild:
    def test_seeds_valid_and_unique(self):
        cases, errors = load_seeds()
        assert not errors and cases
        assert not cross_checks(cases)

    def test_build_deterministic(self, tmp_path):
        cases, _ = load_seeds()
        a = build(cases, tmp_path / "a.db")
        b = build(cases, tmp_path / "b.db")
        assert a["dataset_hash"] == b["dataset_hash"]
        con = sqlite3.connect(tmp_path / "a.db")
        orphans = con.execute(
            "SELECT COUNT(*) FROM cases c WHERE parent_id IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM cases p WHERE p.id=c.parent_id)"
        ).fetchone()[0]
        leak = con.execute(
            "SELECT COUNT(*) FROM cases c JOIN cases p ON p.id=c.parent_id WHERE c.split<>p.split"
        ).fetchone()[0]
        con.close()
        assert orphans == 0 and leak == 0

    def test_every_variant_still_validates(self):
        cases, _ = load_seeds()
        for c, _f in cases:
            for v in make_variants(c):
                Case.model_validate(v.model_dump())


# ------------------------------------------------------------------ hiệu năng
class TestPerf:
    def test_pct_nearest_rank(self):
        from run_bench import pct

        v = [float(x) for x in range(1, 101)]
        assert pct(v, 50) == 50 and pct(v, 95) == 95 and pct(v, 99) == 99 and pct([], 95) == 0.0
        assert pct([7.0], 99) == 7.0

    def test_perf_summary_totals(self):
        from run_bench import perf_summary

        m = {
            "latency_ms": 10.0,
            "llm_calls": 2,
            "input_tokens": 100,
            "output_tokens": 20,
            "cached_tokens": 50,
            "reasoning_tokens": 0,
            "cost_usd": 0.001,
            "reflection_count": 1,
            "steps_ms": {"node:analyze": 8.0},
        }
        rows = [{"id": "A", "turns": [{"gate_fired": False, "metrics": m}, {"gate_fired": True, "metrics": m}]}]
        s = perf_summary(rows)
        assert s["turns"] == 2 and s["gate_fired_turns"] == 1 and s["llm_calls"] == 4
        assert s["input_tokens"] == 200 and s["cost_per_1k_conversations_usd"] == 2.0
        assert s["steps_p95_ms"] == {"node:analyze": 8.0}


# ------------------------------------------------------------------ paraphrase (không gọi API)
class TestParaphraseChecks:
    def test_proper_names(self):
        from paraphrase import proper_names

        assert proper_names("Mẹ tôi tên Phạm Thị Lan, khám ở Vinmec Times City.") == [
            "Phạm Thị Lan",
            "Vinmec Times City",
        ]
        assert proper_names("Tôi bị đau đầu. Bố tôi cũng vậy.") == []

    def test_rejects_changed_numbers_names_turns(self):
        from paraphrase import deterministic_checks

        c = case(turns=["Mẹ tôi tên Phạm Thị Lan, sốt 38.5 độ", "đau đầu", "đặt lịch"])
        assert (
            deterministic_checks(c, ["Bà Phạm Thị Lan nhà tui sốt 38,5 độ nè", "nhức đầu quá", "book lịch giùm"]) == []
        )
        assert any("chữ số" in e for e in deterministic_checks(c, ["Bà Phạm Thị Lan sốt 39 độ", "nhức đầu", "đặt"]))
        assert any("tên riêng" in e for e in deterministic_checks(c, ["Bà Lan sốt 38.5 độ", "nhức đầu", "đặt"]))
        assert deterministic_checks(c, ["a", "b"]) == ["số lượt 2 ≠ 3"]
        assert "trùng bản gốc" in deterministic_checks(c, list(c.turns))

    def test_generated_must_match_parent_split(self, tmp_path, monkeypatch):
        import json

        import build_db

        parent = case(id="TST-PARA-001")
        bad = parent.model_dump() | {
            "id": "TST-PARA-001~para0",
            "origin": "variant",
            "parent_id": parent.id,
            "transform": "paraphrase",
            "split": "test",
            "turns": ["x y z", "a b", "c d"],
        }
        (tmp_path / "paraphrase.jsonl").write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
        monkeypatch.setattr(build_db, "GENERATED", tmp_path)
        out, errors = build_db.load_generated({parent.id: parent})
        assert not out and "split" in errors[0]
