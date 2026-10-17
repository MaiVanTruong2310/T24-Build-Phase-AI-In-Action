"""Chạy bộ test hội thoại từ bench.db, chấm assertion từng lượt, lưu lịch sử vào results.db.

Mô phỏng đúng đường đi production của 1 lượt chat (src/medical_assistant/api/routes.py::run_turn):
  1. Cổng zero-token: triage_service.evaluate_symptoms(tin nhắn) → cấp cứu thì trả hướng dẫn, KHÔNG gọi graph.
  2. Ngược lại gọi LangGraph với input = {checkpoint lượt trước (STATE_FIELDS)} + {tin nhắn, hồ sơ}.
Mặc định offline (LLM vô hiệu → luồng dự phòng tất định), mọi lệnh GHI Supabase bị chặn.

  python eval/conversation_bench/run_bench.py                         # seed, split dev
  python eval/conversation_bench/run_bench.py --origin all --category memory
  python eval/conversation_bench/run_bench.py --ids MEM-CORR-001,EMR-ACC-001
  python eval/conversation_bench/run_bench.py --split test --confirm-test   # chỉ ở mốc release
  RUN_LIVE_LLM=1 python eval/conversation_bench/run_bench.py --live         # LLM thật, tốn token
Exit code 1 nếu có assertion critical trượt hoặc ca lỗi chạy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / "eval" / "compliance_eval"), str(ROOT / "eval" / "triage_eval")]

from assertions import grade  # noqa: E402
from schema import Case  # noqa: E402

DB = HERE / "bench.db"
RESULTS = HERE / "results.db"
REPORTS = ROOT / "reports" / "conversation_bench"
TURN_TIMEOUT_S = 180
SNAPSHOT_KEYS = (
    "is_emergency",
    "ats_level",
    "workflow_status",
    "suggested_department_code",
    "suggested_department_name",
    "booking_for",
    "proxy_patient",
    "awaiting_field",
    "pending_question",
    "recommended_doctor_id",
    "doctor_name",
    "preferred_date",
    "preferred_period",
    "selected_slot",
    "intent_route",
    "route_destination",
)
RESULTS_DDL = """
CREATE TABLE IF NOT EXISTS runs(
  run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, git_sha TEXT, git_dirty INTEGER, mode TEXT,
  dataset_hash TEXT, filters_json TEXT, n_cases INTEGER, n_passed INTEGER, n_critical_failed INTEGER,
  n_errors INTEGER, db_writes_blocked INTEGER
);
CREATE TABLE IF NOT EXISTS turn_metrics(
  run_id TEXT, case_id TEXT, turn INTEGER, gate_fired INTEGER, latency_ms REAL, gate_ms REAL, graph_ms REAL,
  llm_calls INTEGER, input_tokens INTEGER, output_tokens INTEGER, cached_tokens INTEGER, reasoning_tokens INTEGER,
  cost_usd REAL, response_chars INTEGER, route TEXT, critic_status TEXT, reflection_count INTEGER,
  steps_json TEXT, PRIMARY KEY(run_id, case_id, turn)
);
CREATE TABLE IF NOT EXISTS results(
  run_id TEXT, case_id TEXT, passed INTEGER, critical_failed INTEGER, error TEXT, elapsed_ms REAL,
  turns_json TEXT, assertions_json TEXT, PRIMARY KEY(run_id, case_id)
);
"""


# ---------------------------------------------------------------- tải ca
def load_cases(db: Path, a: argparse.Namespace) -> tuple[list[Case], str]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    where, args = ["split = ?"], [a.split]
    if a.origin != "all":
        where.append("origin = ?")
        args.append(a.origin)
    if a.category:
        where.append(f"category IN ({','.join('?' * len(a.category))})")
        args += a.category
    if a.transform:
        where.append("transform = ?")
        args.append(a.transform)
    if a.reviewed_only:
        where.append("review_status = 'reviewed'")
    if a.ids:
        where = [f"(id IN ({','.join('?' * len(a.ids))}) OR parent_id IN ({','.join('?' * len(a.ids))}))"]
        args = [*a.ids, *a.ids]
        if a.origin != "all":
            where.append("origin = ?")
            args.append(a.origin)
    rows = con.execute(f"SELECT * FROM cases WHERE {' AND '.join(where)} ORDER BY id", args).fetchall()
    cases = []
    for r in rows[: a.limit or None]:
        turns = [t[0] for t in con.execute("SELECT content FROM turns WHERE case_id=? ORDER BY idx", (r["id"],))]
        exps = [
            {
                k: v
                for k, v in {
                    "turn": e["turn"],
                    "kind": e["kind"],
                    "op": e["op"],
                    "path": e["path"],
                    "value": json.loads(e["value_json"]),
                    "critical": bool(e["critical"]),
                    "why": e["why"],
                }.items()
            }
            for e in con.execute("SELECT * FROM expectations WHERE case_id=? ORDER BY seq", (r["id"],))
        ]
        cases.append(
            Case.model_validate(
                {
                    "id": r["id"],
                    "category": r["category"],
                    "subcategory": r["subcategory"],
                    "split": r["split"],
                    "title": r["title"],
                    "rationale": r["rationale"],
                    "context": json.loads(r["context_json"]),
                    "turns": turns,
                    "expectations": exps,
                    "tags": json.loads(r["tags_json"]),
                    "source": r["source"],
                    "review_status": r["review_status"],
                    "annotator": r["annotator"],
                    "annotator2": r["annotator2"],
                    "origin": r["origin"],
                    "parent_id": r["parent_id"],
                    "transform": r["transform"],
                }
            )
        )
    dataset_hash = json.loads(con.execute("SELECT value FROM meta WHERE key='dataset_hash'").fetchone()[0])
    con.close()
    return cases, dataset_hash


# ---------------------------------------------------------------- chạy 1 ca
def turn_payload(case: Case, text: str, session_id: str) -> dict:
    """Giống chat_agent_input + prepare_turn của API (hồ sơ nạp lại mỗi lượt khi đã đăng nhập)."""
    p: dict = {"query": text, "session_id": session_id, "enable_citation": False}
    ctx = case.context
    if ctx.authenticated and ctx.profile:
        prof = {k: v for k, v in ctx.profile.model_dump().items() if v}
        p.update(
            patient_profile=prof,
            patient_name=prof.get("name"),
            patient_phone=prof.get("phone"),
            patient_dob=prof.get("date_of_birth"),
            patient_gender=prof.get("gender"),
            is_authenticated=True,
            user_id=f"bench-user-{case.id}",
        )
    else:
        p.update(is_authenticated=False, user_id=None, patient_health_record=None)
    p.update(patient_memory_profile=[], active_open_loops=[])
    return p


def snapshot(state: dict) -> dict:
    snap = {k: state.get(k) for k in SNAPSHOT_KEYS if state.get(k) not in (None, "", [], {})}
    docs = state.get("last_listed_doctors") or []
    if docs:
        snap["last_listed_doctors"] = [
            {k: d.get(k) for k in ("id", "name", "full_name") if d.get(k)} for d in docs if isinstance(d, dict)
        ]
    return snap


def turn_metrics(state: dict, total_ms: float, gate_ms: float, fired: bool, timings: dict, usage: list[dict]) -> dict:
    """Số đo 1 lượt. Token/chi phí lấy từ usage THẬT của provider (llm_usage_sink), quy giá bằng TokenCounter
    của app → khớp telemetry production. Offline (không gọi LLM) thì token = 0."""
    from src.medical_assistant.domain.token_counter import get_token_counter

    cost = get_token_counter().apply_provider_usage({}, usage) if usage else {}
    meta = state.get("metadata") or {}
    return {
        "latency_ms": round(total_ms, 1),
        "gate_ms": round(gate_ms, 2),
        "graph_ms": 0.0 if fired else round(total_ms - gate_ms, 1),  # cổng chặn → graph không chạy
        "steps_ms": {k: round(v, 1) for k, v in sorted(timings.items())},  # node:<tên>, db:*, cpu:*
        "llm_calls": len(usage),
        "input_tokens": sum(u.get("input_tokens", 0) for u in usage),
        "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "cached_tokens": sum(u.get("cache_read", 0) for u in usage),
        "reasoning_tokens": sum(u.get("reasoning", 0) for u in usage),
        "cost_usd": cost.get("estimated_cost_usd", 0.0),
        "response_chars": len(state.get("response") or ""),
        "route": state.get("intent_route"),
        "critic_status": state.get("critic_status"),
        "reflection_count": state.get("reflection_count") or 0,
        "dlp_leak": bool(meta.get("dlp_leakage_detected")),
    }


async def run_case(agent, triage, state_fields: set, case: Case, run_id: str) -> tuple[list[dict], str | None]:
    session_id = f"bench-{run_id[:8]}-{case.id}"
    config = {"configurable": {"thread_id": session_id}}
    carry: dict = {}
    results: list[dict] = []
    from src.medical_assistant.domain.schemas import ChatRequest
    from src.medical_assistant.infrastructure.llm import llm_usage_sink
    from src.medical_assistant.infrastructure.turn_timing import turn_timings

    for raw in case.turns:
        # Giống API: ChatRequest chuẩn hóa message (bỏ ký tự vô hình, homoglyph, chữ tách dấu chấm) trước mọi bước
        text = ChatRequest.model_validate({"message": raw}).message
        payload = {**carry, **turn_payload(case, text, session_id), "error": None}
        # Giống routes.run_turn: mỗi lượt một dict thời gian + một list usage, node/LLM ghi vào (chia sẻ tham chiếu)
        timings: dict[str, float] = {}
        usage: list[dict] = []
        turn_timings.set(timings)
        llm_usage_sink.set(usage)
        t0 = time.perf_counter()
        try:
            gate = triage.evaluate_symptoms(text)
            gate_ms = (time.perf_counter() - t0) * 1000
            # Giống before_turn: khớp MƠ HỒ không chặn, để agent khôi phục dấu / hỏi xác nhận
            if getattr(gate, "is_emergency", False) and getattr(gate, "match_confidence", "") != "ambiguous":
                state = {
                    **payload,
                    "is_emergency": True,
                    "ats_level": gate.ats_level.value,
                    "max_booking_days": 0,
                    "urgency_tier": gate.urgency_tier.value,
                    "workflow_status": "EMERGENCY",
                    "emergency_warning": gate.patient_guidance,
                    "response": gate.patient_guidance,
                }
                fired = True
            else:
                state = await asyncio.wait_for(agent.ainvoke(payload, config=config), TURN_TIMEOUT_S)
                fired = False
        except Exception as exc:  # lỗi lượt → các lượt sau không chạy, assertion của chúng tính trượt
            return results, f"lượt {len(results) + 1}: {type(exc).__name__}: {str(exc)[:300]}"
        total_ms = (time.perf_counter() - t0) * 1000
        results.append(
            {
                "user_text": text,
                "response": state.get("response") or "",
                "state": state,
                "gate_fired": fired,
                "metrics": turn_metrics(state, total_ms, gate_ms, fired, timings, usage),
            }
        )
        carry = {k: state[k] for k in state_fields if k in state}
    return results, None


# ---------------------------------------------------------------- báo cáo
def fmt(k: int, n: int) -> str:
    from run_eval import fmt as _fmt  # tỉ lệ + CI95 Wilson, dùng chung các eval khác

    return _fmt(k, n)


def pct(values: list[float], q: float) -> float:
    """Phân vị nearest-rank (không nội suy) → tái lập, dễ kiểm tay."""
    if not values:
        return 0.0
    v = sorted(values)
    return v[max(0, min(len(v) - 1, math.ceil(q / 100 * len(v)) - 1))]


def perf_summary(rows: list[dict]) -> dict:
    turns = [(r, i, t["metrics"]) for r in rows for i, t in enumerate(r["turns"], 1) if t.get("metrics")]
    lat = [m["latency_ms"] for _, _, m in turns]
    steps: dict[str, list[float]] = defaultdict(list)
    for _, _, m in turns:
        for k, v in m["steps_ms"].items():
            steps[k].append(v)
    total = lambda key: sum(m[key] for _, _, m in turns)  # noqa: E731
    n_conv = len(rows) or 1
    return {
        "turns": len(turns),
        "latency_ms": {q: pct(lat, q) for q in (50, 90, 95, 99)} | {"max": max(lat, default=0.0)},
        "gate_fired_turns": sum(1 for r, i, _ in turns if r["turns"][i - 1]["gate_fired"]),
        "llm_calls": total("llm_calls"),
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "cached_tokens": total("cached_tokens"),
        "reasoning_tokens": total("reasoning_tokens"),
        "cost_usd": round(total("cost_usd"), 6),
        "cost_per_1k_conversations_usd": round(total("cost_usd") / n_conv * 1000, 4),
        "reflections": total("reflection_count"),
        "steps_p95_ms": {k: pct(v, 95) for k, v in sorted(steps.items(), key=lambda x: -pct(x[1], 95))[:10]},
        "slowest": [
            {"id": r["id"], "turn": i, "latency_ms": m["latency_ms"]}
            for r, i, m in sorted(turns, key=lambda x: -x[2]["latency_ms"])[:5]
        ],
    }


def perf_section(rows: list[dict], live: bool) -> list[str]:
    s = perf_summary(rows)
    q = s["latency_ms"]
    out = [
        "",
        "## Hiệu năng và chi phí",
        "",
        f"- Lượt: {s['turns']} (cổng zero-token chặn: {s['gate_fired_turns']}) | "
        f"độ trễ/lượt p50 {q[50]:.0f} ms · p90 {q[90]:.0f} · p95 {q[95]:.0f} · p99 {q[99]:.0f} · max {q['max']:.0f}",
        f"- LLM: {s['llm_calls']} lần gọi | token vào {s['input_tokens']} (cache {s['cached_tokens']}) · "
        f"ra {s['output_tokens']} (reasoning {s['reasoning_tokens']}) | reflexion: {s['reflections']}",
        f"- Chi phí ước tính: ${s['cost_usd']:.4f} | ${s['cost_per_1k_conversations_usd']:.2f} / 1.000 hội thoại "
        "(giá TokenCounter của app)",
    ]
    if not live:
        out.append("- _Offline: LLM bị vô hiệu → token/chi phí = 0; độ trễ chỉ phản ánh luật + I/O đọc DB._")
    out += ["", "| Nhóm | Lượt | p50 ms | p95 ms | Token TB/hội thoại | $/hội thoại |", "|---|---|---|---|---|---|"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["category"]].append(r)
    for g, rs in sorted(groups.items()):
        ms = [t["metrics"] for r in rs for t in r["turns"] if t.get("metrics")]
        lat = [m["latency_ms"] for m in ms]
        tok = sum(m["input_tokens"] + m["output_tokens"] for m in ms) / len(rs)
        cost = sum(m["cost_usd"] for m in ms) / len(rs)
        out.append(f"| {g} | {len(ms)} | {pct(lat, 50):.0f} | {pct(lat, 95):.0f} | {tok:.0f} | {cost:.5f} |")
    out += ["", "| Bước (p95, top 10) | ms |", "|---|---|"]
    out += [f"| `{k}` | {v:.0f} |" for k, v in s["steps_p95_ms"].items()]
    out += [
        "",
        "Lượt chậm nhất: " + ", ".join(f"{x['id']}#{x['turn']} ({x['latency_ms']:.0f} ms)" for x in s["slowest"]),
    ]
    return out


def report(rows: list[dict], meta: dict) -> str:
    lines = [
        "# Conversation bench",
        f"- run `{meta['run_id'][:8]}` | git {meta['git_sha']}{' (dirty)' if meta['git_dirty'] else ''} | "
        f"{meta['mode']} | dataset {meta['dataset_hash']} | {meta['started_at']} UTC",
        f"- Bộ lọc: {meta['filters']} | ghi DB bị chặn: {meta['blocked']}",
        f"- Ca: {len(rows)} | lỗi chạy: {sum(1 for r in rows if r['error'])}",
        "",
        "> Ca `draft_unreviewed` (AI soạn, chưa có người chuyên môn duyệt) chỉ là tín hiệu tham khảo, "
        "không phải điểm chính thức.",
        "",
    ]
    for label, pool in (
        ("Đã duyệt (chính thức)", [r for r in rows if r["review_status"] == "reviewed"]),
        ("Chưa duyệt (tham khảo)", [r for r in rows if r["review_status"] != "reviewed"]),
    ):
        if not pool:
            continue
        lines += [f"## {label}", "", "| Nhóm | Ca đạt toàn bộ | Assertion đạt | Critical trượt |", "|---|---|---|---|"]
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in pool:
            groups[r["category"]].append(r)
        for g in sorted(groups):
            rs = groups[g]
            asr = [x for r in rs for x in r["assertions"]]
            lines.append(
                f"| {g} | {fmt(sum(r['passed'] for r in rs), len(rs))} | "
                f"{fmt(sum(x['passed'] for x in asr), len(asr))} | {sum(r['critical_failed'] for r in rs)} |"
            )
        asr = [x for r in pool for x in r["assertions"]]
        lines.append(
            f"| **Tổng** | {fmt(sum(r['passed'] for r in pool), len(pool))} | "
            f"{fmt(sum(x['passed'] for x in asr), len(asr))} | {sum(r['critical_failed'] for r in pool)} |"
        )
        lines.append("")
    # Theo loại assertion
    kinds: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        for x in r["assertions"]:
            kinds[x["kind"]].append(x["passed"])
    lines += ["## Theo loại assertion", "", "| Loại | Đạt |", "|---|---|"]
    lines += [f"| {k} | {fmt(sum(v), len(v))} |" for k, v in sorted(kinds.items())]
    # Độ bền biến thể: seed đạt mà biến thể trượt
    by_id = {r["id"]: r for r in rows}
    variants = [r for r in rows if r["parent_id"] and r["parent_id"] in by_id]
    if variants:
        lines += [
            "",
            "## Độ bền trước biến đổi bề mặt (chỉ tính khi seed gốc ĐẠT)",
            "",
            "| Biến đổi | Biến thể vẫn đạt |",
            "|---|---|",
        ]
        tr: dict[str, list[bool]] = defaultdict(list)
        for v in variants:
            if by_id[v["parent_id"]]["passed"]:
                tr[v["transform"]].append(v["passed"])
        lines += [f"| {t} | {fmt(sum(v), len(v))} |" for t, v in sorted(tr.items())]
    lines += perf_section(rows, meta["mode"] == "live")
    # Chi tiết lỗi
    lines += ["", "## Assertion trượt", ""]
    for r in sorted(rows, key=lambda r: (not r["critical_failed"], r["id"])):
        if r["error"]:
            lines.append(f"- **[{r['id']}] LỖI CHẠY**: {r['error']}")
        for x in r["assertions"]:
            if not x["passed"]:
                flag = "🔴 CRITICAL " if x["critical"] else ""
                lines.append(f"- {flag}[{r['id']}] lượt {x['turn']} `{x['kind']}`: {x['detail']} — _{x['why']}_")
    return "\n".join(lines)


# ---------------------------------------------------------------- main
async def main_async(cases: list[Case], live: bool, run_id: str) -> tuple[list[dict], int]:
    from run_compliance import block_db_writes, offline_patches  # dùng chung cơ chế offline + chặn ghi

    blocked: list[str] = []
    out = []
    with ExitStack() as stack:
        if not live:
            offline_patches(stack)
        block_db_writes(stack, blocked)
        from src.medical_assistant.agent.graph import agent
        from src.medical_assistant.domain.triage_service import get_triage_service

        try:
            from src.services.chat_history import STATE_FIELDS
        except Exception:  # pragma: no cover - fallback khi import DB model lỗi
            from src.medical_assistant.agent.state import AgentState

            STATE_FIELDS = set(AgentState.__annotations__) - {"query", "response", "error"}  # noqa: N806
        triage = get_triage_service()
        for i, case in enumerate(cases, 1):
            t0 = time.perf_counter()
            turns, error = await run_case(agent, triage, set(STATE_FIELDS), case, run_id)
            graded = grade(case, turns)
            passed = not error and all(x["passed"] for x in graded)
            crit = any(not x["passed"] and x["critical"] for x in graded)
            out.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "subcategory": case.subcategory,
                    "origin": case.origin,
                    "parent_id": case.parent_id,
                    "transform": case.transform,
                    "review_status": case.review_status,
                    "passed": passed,
                    "critical_failed": crit,
                    "error": error,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "turns": [
                        {
                            "user": t["user_text"],
                            "response": t["response"],
                            "gate_fired": t["gate_fired"],
                            "state": snapshot(t["state"]),
                            "metrics": t["metrics"],
                        }
                        for t in turns
                    ],
                    "assertions": [{k: v for k, v in x.items() if k != "spec"} for x in graded],
                }
            )
            mark = "OK " if passed else ("CRIT" if crit else "FAIL")
            print(f"[{i}/{len(cases)}] {mark} {case.id}" + (f"  ({error})" if error else ""), flush=True)
    return out, len(blocked)


def git_info() -> tuple[str, bool]:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, cwd=ROOT
    )
    return sha.stdout.strip(), bool(dirty.stdout.strip())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 không in được tiếng Việt
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--confirm-test", action="store_true", help="bắt buộc khi chạy split test (bộ khóa)")
    ap.add_argument("--origin", choices=("seed", "variant", "all"), default="seed")
    ap.add_argument("--category", type=lambda s: s.split(","), default=None)
    ap.add_argument("--transform", default=None)
    ap.add_argument("--ids", type=lambda s: s.split(","), default=None)
    ap.add_argument("--reviewed-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--live", action="store_true", help="LLM thật (cần RUN_LIVE_LLM=1)")
    a = ap.parse_args()
    if a.split == "test" and not a.confirm_test:
        print("split test là bộ khóa: thêm --confirm-test (chỉ chạy ở mốc release, ghi lại số lần chạy).")
        return 2
    if a.live and os.getenv("RUN_LIVE_LLM", "").lower() not in ("1", "true", "yes"):
        print("--live cần RUN_LIVE_LLM=1 (tốn token, cần được cho phép).")
        return 2
    if not Path(a.db).exists():
        print(f"Chưa có {a.db}: chạy build_db.py trước.")
        return 2
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
    os.environ.setdefault("LANGSMITH_TRACING", "false")
    cases, dataset_hash = load_cases(Path(a.db), a)
    if not cases:
        print("Không có ca khớp bộ lọc.")
        return 2
    run_id = uuid.uuid4().hex
    started = datetime.now(UTC)
    rows, blocked = asyncio.run(main_async(cases, a.live, run_id))
    sha, dirty = git_info()
    filters = {k: v for k, v in vars(a).items() if k not in ("db", "results", "confirm_test") and v}
    meta = {
        "run_id": run_id,
        "git_sha": sha,
        "git_dirty": dirty,
        "mode": "live" if a.live else "offline",
        "dataset_hash": dataset_hash,
        "started_at": f"{started:%Y-%m-%d %H:%M}",
        "filters": filters,
        "blocked": blocked,
    }
    meta["perf"] = perf_summary(rows)
    md = report(rows, meta)
    con = sqlite3.connect(a.results)
    con.executescript(RESULTS_DDL)
    if "metrics_json" not in {c[1] for c in con.execute("PRAGMA table_info(runs)")}:
        con.execute("ALTER TABLE runs ADD COLUMN metrics_json TEXT")
    con.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            run_id,
            started.isoformat(),
            datetime.now(UTC).isoformat(),
            sha,
            int(dirty),
            meta["mode"],
            dataset_hash,
            json.dumps(filters, ensure_ascii=False),
            len(rows),
            sum(r["passed"] for r in rows),
            sum(r["critical_failed"] for r in rows),
            sum(1 for r in rows if r["error"]),
            blocked,
            json.dumps(perf_summary(rows), ensure_ascii=False),
        ),
    )
    con.executemany(
        "INSERT INTO turn_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                run_id,
                r["id"],
                i,
                int(t["gate_fired"]),
                m["latency_ms"],
                m["gate_ms"],
                m["graph_ms"],
                m["llm_calls"],
                m["input_tokens"],
                m["output_tokens"],
                m["cached_tokens"],
                m["reasoning_tokens"],
                m["cost_usd"],
                m["response_chars"],
                m["route"],
                m["critic_status"],
                m["reflection_count"],
                json.dumps(m["steps_ms"]),
            )
            for r in rows
            for i, t in enumerate(r["turns"], 1)
            if (m := t.get("metrics"))
        ],
    )
    con.executemany(
        "INSERT INTO results VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                run_id,
                r["id"],
                int(r["passed"]),
                int(r["critical_failed"]),
                r["error"],
                r["elapsed_ms"],
                json.dumps(r["turns"], ensure_ascii=False, default=str),
                json.dumps(r["assertions"], ensure_ascii=False, default=str),
            )
            for r in rows
        ],
    )
    con.commit()
    con.close()
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y%m%d_%H%M%S")
    (REPORTS / f"bench_{stamp}.md").write_text(md, encoding="utf-8")
    (REPORTS / f"bench_{stamp}.json").write_text(
        json.dumps({"meta": meta, "results": rows}, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    print(md)
    hard = any(r["critical_failed"] or r["error"] for r in rows)
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
