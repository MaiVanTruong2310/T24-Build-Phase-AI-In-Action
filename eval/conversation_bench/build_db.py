"""Validate seeds/*.jsonl → sinh biến thể → ghi bench.db (SQLite). Tất định: cùng seeds ⇒ cùng DB hash.

  python eval/conversation_bench/build_db.py            # validate + build
  python eval/conversation_bench/build_db.py --check    # chỉ validate, không ghi DB
Seeds JSONL là nguồn chuẩn (đọc/diff được); bench.db chỉ là bản dựng, xóa đi build lại được.
Kết quả chạy ghi ở results.db riêng → build lại bench.db không mất lịch sử chạy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from perturb import make_variants, strip_diacritics  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from schema import Case  # noqa: E402

SEEDS = HERE / "seeds"
GENERATED = HERE / "generated"  # biến thể do LLM sinh (paraphrase.py), đã qua kiểm tra + judge
DB = HERE / "bench.db"

DDL = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE cases(
  id TEXT PRIMARY KEY, origin TEXT NOT NULL CHECK(origin IN ('seed','variant')),
  parent_id TEXT REFERENCES cases(id), transform TEXT,
  category TEXT NOT NULL, subcategory TEXT NOT NULL, split TEXT NOT NULL CHECK(split IN ('dev','test')),
  title TEXT NOT NULL, rationale TEXT NOT NULL, context_json TEXT NOT NULL, tags_json TEXT NOT NULL,
  source TEXT NOT NULL, review_status TEXT NOT NULL, annotator TEXT, annotator2 TEXT,
  n_turns INTEGER NOT NULL, seed_file TEXT NOT NULL, content_hash TEXT NOT NULL
);
CREATE TABLE turns(
  case_id TEXT NOT NULL REFERENCES cases(id), idx INTEGER NOT NULL, content TEXT NOT NULL,
  PRIMARY KEY(case_id, idx)
);
CREATE TABLE expectations(
  case_id TEXT NOT NULL REFERENCES cases(id), seq INTEGER NOT NULL, turn TEXT NOT NULL, kind TEXT NOT NULL,
  op TEXT, path TEXT, value_json TEXT, critical INTEGER NOT NULL, why TEXT NOT NULL,
  PRIMARY KEY(case_id, seq)
);
CREATE INDEX ix_cases_cat ON cases(category, subcategory);
CREATE INDEX ix_cases_split ON cases(split, origin, review_status);
"""


def content_hash(c: Case) -> str:
    blob = json.dumps(
        {"turns": c.turns, "context": c.context.model_dump(), "exp": [e.model_dump() for e in c.expectations]},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def load_seeds() -> tuple[list[tuple[Case, str]], list[str]]:
    cases, errors = [], []
    files = sorted(SEEDS.glob("*.jsonl"))
    if not files:
        errors.append(f"không có seed trong {SEEDS}")
    for f in files:
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                c = Case.model_validate(json.loads(line))
                if c.origin != "seed":
                    raise ValueError("file seeds chỉ chứa origin=seed")
                cases.append((c, f.name))
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{f.name}:{ln}: {exc}")
    return cases, errors


def cross_checks(cases: list[tuple[Case, str]]) -> list[str]:
    """Kiểm tra toàn tập: id trùng, nội dung trùng (sau chuẩn hóa), rò rỉ dev/test."""
    errors = []
    ids = Counter(c.id for c, _ in cases)
    errors += [f"id trùng: {i}" for i, n in ids.items() if n > 1]
    seen: dict[str, str] = {}
    for c, _ in cases:
        key = "\x1f".join(" ".join(strip_diacritics(t).casefold().split()) for t in c.turns)
        if key in seen:
            errors.append(f"nội dung trùng: {c.id} == {seen[key]} (cùng lượt sau khi bỏ dấu/hoa thường)")
        seen.setdefault(key, c.id)
    # Rò rỉ: một lượt mở đầu giống hệt xuất hiện ở cả dev lẫn test
    first: dict[str, set] = {}
    for c, _ in cases:
        first.setdefault(strip_diacritics(c.turns[0]).casefold().strip(), set()).add(c.split)
    errors += [f"rò rỉ dev/test (lượt 1 giống nhau): {k[:60]}" for k, v in first.items() if len(v) > 1]
    return errors


def _content_key(turns: list[str]) -> str:
    return "\x1f".join(" ".join(strip_diacritics(t).casefold().split()) for t in turns)


def load_generated(seeds: dict[str, Case]) -> tuple[list[tuple[Case, str]], list[str]]:
    """Biến thể LLM: parent phải là seed hiện có, split phải trùng parent (chống rò rỉ), validate lại."""
    out, errors = [], []
    # Bỏ biến thể trùng nội dung (sau bỏ dấu/hoa thường) với seed hoặc biến thể khác cùng parent
    seen = {sid: {_content_key(s.turns)} for sid, s in seeds.items()}
    for f in sorted(GENERATED.glob("*.jsonl")) if GENERATED.exists() else []:
        if f.name.endswith(("_cache.jsonl", "_rejected.jsonl")):
            continue
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                v = Case.model_validate(json.loads(line))
                parent = seeds.get(v.parent_id or "")
                if v.origin != "variant" or parent is None:
                    raise ValueError(f"parent {v.parent_id} không phải seed hiện có")
                if v.split != parent.split:
                    raise ValueError(f"split {v.split} ≠ split của parent {parent.split}")
                if v.review_status == "reviewed" and not v.annotator:
                    raise ValueError("reviewed cần annotator")
                key = _content_key(v.turns)
                if key in seen[parent.id]:
                    continue
                seen[parent.id].add(key)
                out.append((v, f"generated/{f.name}"))
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"generated/{f.name}:{ln}: {exc}")
    return out, errors


def build(cases: list[tuple[Case, str]], path: Path, generated: list[tuple[Case, str]] | None = None) -> dict:
    rows: list[tuple[Case, str]] = []
    gen_by_parent: dict[str, list[tuple[Case, str]]] = {}
    for v, f in generated or []:
        gen_by_parent.setdefault(v.parent_id, []).append((v, f))
    for c, f in sorted(cases, key=lambda x: x[0].id):
        rows.append((c, f))
        rows += [(v, f) for v in make_variants(c)]  # biến thể kế thừa split của seed → không rò rỉ
        rows += sorted(gen_by_parent.get(c.id, []), key=lambda x: x[0].id)
    tmp = path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript(DDL)
    digest = hashlib.sha256()
    for c, f in rows:
        h = content_hash(c)
        digest.update(f"{c.id}:{h}".encode())
        con.execute(
            "INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                c.id,
                c.origin,
                c.parent_id,
                c.transform,
                c.category,
                c.subcategory,
                c.split,
                c.title,
                c.rationale,
                json.dumps(c.context.model_dump(), ensure_ascii=False),
                json.dumps(c.tags, ensure_ascii=False),
                c.source,
                c.review_status,
                c.annotator,
                c.annotator2,
                len(c.turns),
                f,
                h,
            ),
        )
        con.executemany("INSERT INTO turns VALUES (?,?,?)", [(c.id, i, t) for i, t in enumerate(c.turns, 1)])
        con.executemany(
            "INSERT INTO expectations VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    c.id,
                    i,
                    str(e.turn),
                    e.kind,
                    e.op,
                    e.path,
                    json.dumps(e.value, ensure_ascii=False),
                    int(e.critical),
                    e.why,
                )
                for i, e in enumerate(c.expectations, 1)
            ],
        )
    stats = {
        "dataset_hash": digest.hexdigest()[:16],
        "seeds": sum(1 for c, _ in rows if c.origin == "seed"),
        "variants": sum(1 for c, _ in rows if c.origin == "variant"),
        "llm_variants": sum(1 for c, _ in rows if c.transform == "paraphrase"),
        "by_category": dict(sorted(Counter(c.category for c, _ in rows if c.origin == "seed").items())),
        "by_split": dict(sorted(Counter(c.split for c, _ in rows if c.origin == "seed").items())),
    }
    con.executemany("INSERT INTO meta VALUES (?,?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in stats.items()])
    con.commit()
    con.close()
    path.unlink(missing_ok=True)
    tmp.rename(path)
    return stats


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 không in được tiếng Việt
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="chỉ validate")
    ap.add_argument("--db", default=str(DB))
    a = ap.parse_args()
    cases, errors = load_seeds()
    errors += cross_checks(cases)
    if errors:
        print(f"[build_db] {len(errors)} lỗi:", *errors, sep="\n  ")
        return 1
    if a.check:
        print(f"[build_db] OK: {len(cases)} seed hợp lệ")
        return 0
    generated, gen_errors = load_generated({c.id: c for c, _ in cases})
    if gen_errors:
        print(f"[build_db] {len(gen_errors)} lỗi biến thể sinh:", *gen_errors, sep="\n  ")
        return 1
    stats = build(cases, Path(a.db), generated)
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
