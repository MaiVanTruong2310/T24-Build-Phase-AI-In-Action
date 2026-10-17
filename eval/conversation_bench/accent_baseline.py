"""GĐ0 kế hoạch "khớp luật cấp cứu trên tiếng Việt có dấu": đo và ĐÓNG BĂNG mốc trước khi sửa luật.

Đo tất định tầng cổng cấp cứu (triage_service.evaluate_symptoms = cổng zero-token của production), không LLM:
  A. Bộ âm tính có dấu (false_alarm/accent_collision): tỉ lệ ATS 1-2 và ATS 3 nhầm, luật gây ra.
  B. Mọi lượt "lành tính" trong bench (routing, info, scope, booking, hitl, false_alarm): báo nhầm theo luật.
  C. Recall cấp cứu theo biến đổi (seed, no_diacritics, partial_accent, paraphrase…), có ngữ cảnh 2 lượt trước.
  D. triage_eval dev + etek_dev, bản có dấu và bỏ dấu: rule_id descriptor từng câu (mốc "bản cũ khớp thì bản mới
     vẫn khớp"). Không dùng etek_test (bộ khóa).
  E. Lưu nguyên output run_eval (dev, etek_dev) và metamorphic.py.

  python eval/conversation_bench/accent_baseline.py                 # đo + đóng băng mốc (FROZEN_BASELINE.json)
  python eval/conversation_bench/accent_baseline.py --compare       # GĐ3: đo lại và so với mốc đã đóng băng
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "eval" / "triage_eval")]

from perturb import strip_diacritics  # noqa: E402

OUT = ROOT / "reports" / "accent_baseline"
FROZEN = OUT / "FROZEN_BASELINE.json"
BENIGN_CATS = ("routing", "info", "scope", "booking", "hitl", "false_alarm")


def gate(triage, text: str, prior: list[str]) -> dict:
    """Một lượt qua cổng cấp cứu (có ngữ cảnh 2 lượt trước như router/analyze) + luật descriptor nào khớp."""
    from src.medical_assistant.domain.ats_descriptor_service import match_ats_descriptors
    from src.medical_assistant.domain.text_normalization import canonicalize_for_matching, normalize_user_message

    # Giống API: ChatRequest chuẩn hóa từng tin nhắn (ký tự vô hình, homoglyph) trước cổng cấp cứu
    text, prior = normalize_user_message(text), [normalize_user_message(p) for p in prior]
    msgs = [{"role": "user", "content": p} for p in prior]
    r = triage.evaluate_with_recent_context(text, msgs) if prior else triage.evaluate_symptoms(text)
    d = match_ats_descriptors(canonicalize_for_matching(text))
    return {
        "ats": r.ats_level.value,
        "emergency": bool(r.is_emergency),
        "rule": (r.triggered_rule_ids or [None])[0],
        "desc": d.rule_id if d else None,
        "desc_ats": d.ats_level if d else None,
    }


def load_bench(db: Path) -> list[dict]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cases = []
    for r in con.execute("SELECT id, category, subcategory, origin, transform, parent_id, split FROM cases"):
        turns = [t[0] for t in con.execute("SELECT content FROM turns WHERE case_id=? ORDER BY idx", (r["id"],))]
        exps = [
            dict(e) for e in con.execute("SELECT turn, kind, value_json FROM expectations WHERE case_id=?", (r["id"],))
        ]
        cases.append({**dict(r), "turns": turns, "exps": exps})
    con.close()
    return cases


def emergency_turns(case: dict) -> list[int]:
    from schema import parse_turns

    out = []
    for e in case["exps"]:
        if e["kind"] == "emergency" and json.loads(e["value_json"]) is True:
            out += parse_turns(e["turn"], len(case["turns"]))
    return sorted(set(out))


def rate(k: int, n: int) -> str:
    from run_eval import fmt

    return fmt(k, n)


def measure(triage) -> dict:
    cases = load_bench(HERE / "bench.db")
    res: dict = {"negatives": [], "benign": [], "emergency": [], "eval": []}
    # A + B: lượt lành tính (mỗi lượt đánh giá đơn lẻ = cổng zero-token before_turn)
    for c in cases:
        if c["category"] not in BENIGN_CATS or emergency_turns(c):
            continue
        for i, t in enumerate(c["turns"], 1):
            row = {"id": c["id"], "turn": i, "text": t, "transform": c["transform"] or "seed",
                   "category": c["category"], **gate(triage, t, [])}  # fmt: skip
            res["benign"].append(row)
            if c["subcategory"] == "accent_collision":
                res["negatives"].append(row)
    # C: recall cấp cứu ở lượt kỳ vọng cấp cứu, với 2 lượt người dùng trước làm ngữ cảnh
    for c in cases:
        for t in emergency_turns(c):
            prior = c["turns"][max(0, t - 3) : t - 1]
            res["emergency"].append({"id": c["id"], "turn": t, "text": c["turns"][t - 1],
                                     "transform": c["transform"] or "seed", "category": c["category"],
                                     **gate(triage, c["turns"][t - 1], prior)})  # fmt: skip
    # D: triage_eval dev + etek_dev, có dấu và bỏ dấu
    for split in ("dev", "etek_dev"):
        path = ROOT / "eval" / "triage_eval" / "data" / f"{split}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            text = " ".join(r.get("turns") or [r["query"]])
            for form, q in (("accented", text), ("stripped", strip_diacritics(text))):
                res["eval"].append({"split": split, "id": r["id"], "form": form, "gold_ats": r.get("gold_ats"),
                                    **gate(triage, q, [])})  # fmt: skip
    return res


def summarize(res: dict) -> dict:
    s: dict = {}
    neg_seed = [r for r in res["negatives"] if r["transform"] == "seed"]
    s["A_negatives_seed"] = {
        "n": len(neg_seed),
        "ats1_2": sum(r["emergency"] for r in neg_seed),
        "ats3": sum(r["ats"] == 3 for r in neg_seed),
        "by_rule": Counter(r["rule"] for r in neg_seed if r["ats"] <= 3).most_common(),
    }
    by_tf: dict = defaultdict(lambda: [0, 0, 0])
    for r in res["negatives"]:
        by_tf[r["transform"]][0] += 1
        by_tf[r["transform"]][1] += r["emergency"]
        by_tf[r["transform"]][2] += r["ats"] == 3
    s["A_negatives_by_transform"] = {k: {"n": v[0], "ats1_2": v[1], "ats3": v[2]} for k, v in sorted(by_tf.items())}
    ben = res["benign"]
    s["B_benign_turns"] = {
        "n": len(ben),
        "ats1_2": sum(r["emergency"] for r in ben),
        "ats3": sum(r["ats"] == 3 for r in ben),
        "ats1_2_by_rule": Counter(r["rule"] for r in ben if r["emergency"]).most_common(15),
        "ats3_by_rule": Counter(r["rule"] for r in ben if r["ats"] == 3).most_common(10),
        "by_category": {
            cat: {
                "n": sum(1 for r in ben if r["category"] == cat),
                "ats1_2": sum(r["emergency"] for r in ben if r["category"] == cat),
            }
            for cat in BENIGN_CATS
        },  # fmt: skip
    }
    rec: dict = defaultdict(lambda: [0, 0])
    for r in res["emergency"]:
        rec[r["transform"]][0] += 1
        rec[r["transform"]][1] += r["emergency"]
    s["C_emergency_recall_by_transform"] = {k: {"n": v[0], "caught": v[1]} for k, v in sorted(rec.items())}
    ev = res["eval"]
    s["D_eval"] = {}
    for split in ("dev", "etek_dev"):
        for form in ("accented", "stripped"):
            rows = [r for r in ev if r["split"] == split and r["form"] == form]
            gold_e = [r for r in rows if r["gold_ats"] is not None and r["gold_ats"] <= 2]
            gold_n = [r for r in rows if r["gold_ats"] is not None and r["gold_ats"] > 2]
            s["D_eval"][f"{split}/{form}"] = {
                "n": len(rows),
                "recall": [sum(r["emergency"] for r in gold_e), len(gold_e)],
                "false_alarm": [sum(r["emergency"] for r in gold_n), len(gold_n)],
                "descriptor_rule_ids": len({r["desc"] for r in rows if r["desc"]}),
            }
    return s


def report_md(s: dict, meta: dict) -> str:
    a, b = s["A_negatives_seed"], s["B_benign_turns"]
    lines = [
        "# Mốc GĐ0: khớp luật cấp cứu (trước khi sửa)",
        f"- {meta['when']} UTC | git {meta['git']} | KB {meta['kb']} | bench {meta['dataset']}",
        "- Đo tầng cổng cấp cứu tất định (`evaluate_symptoms` + ngữ cảnh 2 lượt), không LLM.",
        "",
        "## A. Bộ âm tính có dấu (107 câu đời thường chứa từ trùng mẫu khi bỏ dấu)",
        f"- ATS 1-2 (báo cấp cứu nhầm): **{rate(a['ats1_2'], a['n'])}** — tiêu chí nghiệm thu: 0",
        f"- ATS 3 nhầm: **{rate(a['ats3'], a['n'])}** — tiêu chí: ≤ 1%",
        "",
        "| Luật gây nhầm (ATS ≤ 3) | Số câu |",
        "|---|---|",
        *[f"| `{k}` | {v} |" for k, v in a["by_rule"]],
        "",
        "| Biến thể của bộ âm tính | n | ATS 1-2 | ATS 3 |",
        "|---|---|---|---|",
        *[f"| {k} | {v['n']} | {v['ats1_2']} | {v['ats3']} |" for k, v in s["A_negatives_by_transform"].items()],
        "",
        "## B. Mọi lượt lành tính trong bench",
        f"- {b['n']} lượt | ATS 1-2: **{rate(b['ats1_2'], b['n'])}** | ATS 3: **{rate(b['ats3'], b['n'])}**",
        "",
        "| Nhóm | Lượt | ATS 1-2 nhầm |",
        "|---|---|---|",
        *[f"| {k} | {v['n']} | {v['ats1_2']} |" for k, v in b["by_category"].items()],
        "",
        "| Luật gây ATS 1-2 nhầm (top 15) | Lượt |",
        "|---|---|",
        *[f"| `{k}` | {v} |" for k, v in b["ats1_2_by_rule"]],
        "",
        "## C. Recall cấp cứu theo biến đổi (lượt kỳ vọng cấp cứu)",
        "",
        "| Biến đổi | Bắt được |",
        "|---|---|",
        *[f"| {k} | {rate(v['caught'], v['n'])} |" for k, v in s["C_emergency_recall_by_transform"].items()],
        "",
        "## D. triage_eval (dev, etek_dev): có dấu vs bỏ dấu",
        "",
        "| Tập / dạng | Recall cấp cứu | Báo nhầm (gold ATS ≥ 3) | Số rule_id descriptor khớp |",
        "|---|---|---|---|",
        *[
            f"| {k} | {rate(*v['recall'])} | {rate(*v['false_alarm'])} | {v['descriptor_rule_ids']} |"
            for k, v in s["D_eval"].items()
        ],  # fmt: skip
        "",
        "Chi tiết từng câu: `negatives.jsonl`, `benign.jsonl`, `emergency.jsonl`, `eval_hits.jsonl` cùng thư mục.",
    ]
    return "\n".join(lines)


def compare(cur: dict, frozen: dict) -> str:
    """GĐ3: so từng mục với mốc đóng băng (chặn release nếu bỏ sót mới)."""

    def key(r):
        return (r.get("id"), r.get("turn"), r.get("form"), r.get("split"))

    lines = ["# So với mốc GĐ0", ""]
    old = {key(r): r for r in frozen["items"]["emergency"]}
    lost = [r for r in cur["emergency"] if not r["emergency"] and old.get(key(r), {}).get("emergency")]
    lines.append(f"- Cấp cứu bản cũ bắt mà bản mới BỎ SÓT: **{len(lost)}** (phải = 0)")
    lines += [f"  - {r['id']}#{r['turn']}: {r['text'][:90]}" for r in lost[:30]]
    oldev = {key(r): r for r in frozen["items"]["eval"]}
    lost_d = [r for r in cur["eval"] if oldev.get(key(r), {}).get("desc") and not r["desc"]]
    lines.append(f"- Câu eval bản cũ khớp descriptor mà bản mới không khớp: **{len(lost_d)}** (xem lại từng câu)")
    lines += [f"  - {r['split']}/{r['id']} ({r['form']}): {oldev[key(r)]['desc']}" for r in lost_d[:30]]
    for name in ("negatives", "benign"):
        o = sum(r["emergency"] for r in frozen["items"][name])
        n = sum(r["emergency"] for r in cur[name])
        lines.append(f"- {name}: ATS 1-2 nhầm {o} → {n}")
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true", help="đo lại và so với FROZEN_BASELINE.json")
    a = ap.parse_args()
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    from run_eval import kb_fingerprint

    from src.medical_assistant.domain.triage_service import get_triage_service

    triage = get_triage_service()
    stamp = datetime.now(UTC)
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout
    con = sqlite3.connect(HERE / "bench.db")
    dataset = json.loads(con.execute("SELECT value FROM meta WHERE key='dataset_hash'").fetchone()[0])
    con.close()
    meta = {"when": f"{stamp:%Y-%m-%d %H:%M}", "git": git.strip() + " (working tree)", "kb": kb_fingerprint(triage),
            "dataset": dataset}  # fmt: skip
    res = measure(triage)
    summary = summarize(res)
    if a.compare and not FROZEN.exists():
        print("Chưa có mốc: chạy không kèm --compare trước.")
        return 2
    d = OUT / f"{stamp:%Y%m%d_%H%M%S}{'_compare' if a.compare else ''}"
    d.mkdir(parents=True, exist_ok=True)
    for name, key in (
        ("negatives", "negatives"),
        ("benign", "benign"),
        ("emergency", "emergency"),
        ("eval_hits", "eval"),
    ):
        (d / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res[key]),
                                         encoding="utf-8")  # fmt: skip
    md = report_md(summary, meta)
    (d / "summary.md").write_text(md, encoding="utf-8")
    (d / "summary.json").write_text(
        json.dumps({"meta": meta, **summary}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # E: output nguyên văn của eval hiện có
    env = {**os.environ, "PYTHONUTF8": "1"}
    for name, cmd in (("run_eval_dev", ["eval/triage_eval/run_eval.py", "--split", "dev"]),
                      ("run_eval_etek_dev", ["eval/triage_eval/run_eval.py", "--split", "etek_dev"]),
                      ("metamorphic", ["eval/triage_eval/metamorphic.py"])):  # fmt: skip
        out = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=ROOT, env=env)
        (d / f"{name}.md").write_text(out.stdout, encoding="utf-8")
    if a.compare:  # không ghi đè mốc đã đóng băng
        cmp = compare(res, json.loads(FROZEN.read_text(encoding="utf-8")))
        (d / "compare.md").write_text(cmp, encoding="utf-8")
        print(md, cmp, f"→ {d.relative_to(ROOT)}", sep="\n\n")
        return 0
    FROZEN.write_text(json.dumps({"meta": meta, "summary": summary, "items": res, "dir": d.name}, ensure_ascii=False),
                      encoding="utf-8")  # fmt: skip
    print(md)
    print(f"\n→ {d.relative_to(ROOT)} | mốc đóng băng: {FROZEN.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
