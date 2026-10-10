"""Eval triage khách quan, tất định (không gọi LLM).

Đo cổng cấp cứu (ATS 1-2) và chọn chuyên khoa của ClinicalTriageService trên tập có nhãn độc lập.
  python eval/triage_eval/run_eval.py --split dev
  python eval/triage_eval/run_eval.py --split test --confirm-test   # chỉ chạy trước release
  python eval/triage_eval/run_eval.py --split dev --list-codes      # xem mã chuyên khoa hệ thống phát ra
Chỉ ca có label_status == "reviewed" được tính vào điểm chính thức; ca "draft_unreviewed" báo riêng.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DATA = Path(__file__).parent / "data"
GENERAL = {"TONG_QUAT", "Sức khỏe tổng quát", "General Health"}
# Nhãn gold được phép ghi bằng mã; hệ thống phát ra tên chuyên khoa → chuẩn hóa trước khi so.
SPECIALTY_ALIASES = {
    "TONG_QUAT": "Sức khỏe tổng quát",
    "XUONG_KHOP": "Chấn thương chỉnh hình - Y học thể thao",
    "TIM_MACH": "Trung tâm Tim mạch",
    "HO_HAP": "Nội hô hấp",
    "TIEU_HOA": "Tiêu hóa - Gan mật",
    "THAN_KINH": "Thần kinh",
    "TMH": "Tai - Mũi - Họng",
    "DI_UNG": "Miễn dịch - Dị ứng",
    "TIET_NIEU": "Thận - Tiết niệu",
    "SAN_PHU_KHOA": "Sản phụ khoa",
    "NHI": "Nhi khoa",
}
# ↑ càng cao càng tốt, ↓ càng thấp càng tốt (mặc định ↑)
DIRECTION = {"over_triage_rate": "↓", "fell_to_general_when_specific": "↓", "errors": "↓",
             "under_triage_disposition": "↓", "over_triage_disposition": "↓"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def fmt(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% (CI95 {100 * lo:.1f}-{100 * hi:.1f})" if n else "n/a (0 ca)"


def load(split: str) -> tuple[list[dict], str]:
    path = DATA / f"{split}.jsonl"
    raw = path.read_bytes()
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    for r in rows:
        r.setdefault("query", " | ".join(r.get("turns") or []))
        if r.get("gold_specialty"):
            r["gold_specialty"] = SPECIALTY_ALIASES.get(r["gold_specialty"], r["gold_specialty"])
    return rows, hashlib.sha256(raw).hexdigest()[:12]


def codes(result) -> list[str]:
    seen: list[str] = []
    for c in [*result.recommended_specialties, *result.candidate_specialties]:
        if c.name not in seen:
            seen.append(c.name)
    if result.suggested_specialty and result.suggested_specialty not in seen:
        seen.insert(0, result.suggested_specialty)
    return seen


def canon(name: str | None) -> str:
    """So chuyên khoa theo mã chuẩn để 'Hô hấp' == 'Nội hô hấp'."""
    from src.medical_assistant.domain.language_service import canonicalize_specialty_code

    return canonicalize_specialty_code(SPECIALTY_ALIASES.get(name or "", name or ""))


def kb_fingerprint(svc) -> str:
    """Luật nạp từ Supabase hoặc file cục bộ → ghi nguồn + hash để kết quả tái lập được."""
    dump = [d.model_dump(mode="json") for _, d in sorted(svc.diseases.items())]
    blob = json.dumps(dump, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{getattr(svc, 'kb_source', '?')}/{len(svc.diseases)} bệnh/{hashlib.sha256(blob).hexdigest()[:12]}"


def run(rows: list[dict]) -> tuple[list[dict], str]:
    from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService
    from src.medical_assistant.domain.triage_service import get_triage_service

    svc, fact_svc = get_triage_service(), ClinicalFactService()
    out = []
    for r in rows:
        try:
            # Giống analyze_node: tích lũy facts theo lượt → evaluate trên văn bản gộp → resolve_multi_symptom.
            turns = r.get("turns") or [r["query"]]
            facts: dict = {}
            for i, t in enumerate(turns, 1):
                facts = fact_svc.merge(facts, fact_svc.extract(t, turn_index=i))
            res = svc.resolve_multi_symptom(svc.evaluate_symptoms(" ".join(turns)), facts)
            out.append({**r, "pred_ats": res.ats_level.value, "pred_emergency": bool(res.is_emergency),
                        "pred_codes": codes(res), "pred_top1": res.suggested_specialty,
                        "pred_recommended": [c.name for c in res.recommended_specialties],
                        "pred_flags": list(res.triggered_red_flags or []), "error": None})
        except Exception as exc:  # lỗi tính là sai, không bỏ qua
            out.append({**r, "pred_ats": None, "pred_emergency": False, "pred_codes": [], "pred_top1": None,
                        "pred_recommended": [], "pred_flags": [], "error": str(exc)})
    return out, kb_fingerprint(svc)


def score(rs: list[dict]) -> dict:
    m: dict = {}
    pos = [r for r in rs if r["gold_ats"] <= 2]
    neg = [r for r in rs if r["gold_ats"] >= 3]
    m["emergency_recall"] = (sum(r["pred_emergency"] for r in pos), len(pos))
    m["over_triage_rate"] = (sum(r["pred_emergency"] for r in neg), len(neg))
    m["ats_exact"] = (sum(r["pred_ats"] == r["gold_ats"] for r in rs), len(rs))
    m["ats_within1"] = (sum(r["pred_ats"] is not None and abs(r["pred_ats"] - r["gold_ats"]) <= 1 for r in rs), len(rs))
    sp = [r for r in rs if r.get("gold_specialty") and r["gold_ats"] >= 3]
    m["specialty_top1_all"] = (sum(r["pred_top1"] == r["gold_specialty"] for r in sp), len(sp))
    m["specialty_top3_all"] = (sum(r["gold_specialty"] in r["pred_codes"][:3] for r in sp), len(sp))
    spec_only = [r for r in sp if r["gold_specialty"] not in GENERAL]
    m["specialty_top1_nongeneral"] = (sum(r["pred_top1"] == r["gold_specialty"] for r in spec_only), len(spec_only))
    m["fell_to_general_when_specific"] = (sum(r["pred_top1"] in GENERAL for r in spec_only), len(spec_only))
    # Đa chuyên khoa: gold_specialties là danh sách chuyên khoa phải có trong recommended_specialties.
    mu = [r for r in rs if r.get("gold_specialties") and not r["pred_emergency"]]
    rec_codes = {id(r): {canon(n) for n in r.get("pred_recommended") or []} for r in mu}
    m["multi_all_recommended"] = (sum({canon(g) for g in r["gold_specialties"]} <= rec_codes[id(r)] for r in mu), len(mu))
    m["multi_any_recommended"] = (sum(bool({canon(g) for g in r["gold_specialties"]} & rec_codes[id(r)]) for r in mu), len(mu))
    # Nhất quán: chuyên khoa chính (dùng để tìm lịch) phải nằm trong danh sách gợi ý hiển thị.
    shown = [r for r in rs if r.get("pred_recommended") and not r["pred_emergency"]]
    m["top1_in_recommended"] = (
        sum(canon(r["pred_top1"]) in {canon(n) for n in r["pred_recommended"]} for r in shown), len(shown))
    # Theo mức xử trí của chatbot (ATS 1-2 cấp cứu / 3 trong ngày / 4-5 đặt lịch): xếp thấp hơn thật = nguy hiểm.
    ok = [r for r in rs if r["pred_ats"] is not None]
    m["under_triage_disposition"] = (sum(disposition(r["pred_ats"]) > disposition(r["gold_ats"]) for r in ok), len(ok))
    m["over_triage_disposition"] = (sum(disposition(r["pred_ats"]) < disposition(r["gold_ats"]) for r in ok), len(ok))
    m["errors"] = (sum(1 for r in rs if r["error"]), len(rs))
    return m


def disposition(ats: int) -> int:
    """0 = cấp cứu (ATS 1-2), 1 = khám trong ngày (ATS 3), 2 = đặt lịch thường (ATS 4-5)."""
    return 0 if ats <= 2 else 1 if ats == 3 else 2


def weighted_kappa(rs: list[dict], k: int = 5) -> float | None:
    """Cohen's kappa trọng số bậc hai trên thang ATS 1-5 (chuẩn đo đồng thuận triage)."""
    pairs = [(r["gold_ats"] - 1, r["pred_ats"] - 1) for r in rs if r["pred_ats"] is not None]
    n = len(pairs)
    if n == 0:
        return None
    obs = [[0] * k for _ in range(k)]
    for g, p in pairs:
        obs[g][p] += 1
    rows_ = [sum(obs[i]) for i in range(k)]
    cols = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * rows_[i] * cols[j] / n for i in range(k) for j in range(k))
    return 1 - num / den if den else None


def confusion(rs: list[dict]) -> list[str]:
    m = Counter((r["gold_ats"], r["pred_ats"]) for r in rs if r["pred_ats"] is not None)
    out = ["| gold \\ pred | 1 | 2 | 3 | 4 | 5 |", "|---|---|---|---|---|---|"]
    out += [f"| **{g}** | " + " | ".join(str(m.get((g, p), "")) for p in range(1, 6)) + " |" for g in range(1, 6)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "etek_dev", "etek_test"], default="dev")
    ap.add_argument("--variant", choices=["patient", "full"], default="patient",
                    help="ETEK: patient = lời kể bệnh nhân (không sinh hiệu), full = dịch sát kèm sinh hiệu")
    ap.add_argument("--confirm-test", action="store_true", help="bắt buộc khi chạy tập test")
    ap.add_argument("--list-codes", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "reports" / "triage_eval"))
    a = ap.parse_args()
    if a.split.endswith("test") and not a.confirm_test:
        print("Tập test bị khóa: chỉ chạy trước release, thêm --confirm-test."); return 2
    rows, h = load(a.split)
    if a.variant == "full":
        rows = [{**r, "query": r.get("query_full", r["query"])} for r in rows]
    preds, kb = run(rows)
    if a.list_codes:
        print(sorted({c for p in preds for c in p["pred_codes"]})); return 0

    # Chính thức: nhãn người duyệt hoặc nhãn chuyên gia (ETEK). Bản lời bệnh nhân bỏ ca cần sinh hiệu
    # (bệnh nhân chat không tự đo được) → báo riêng ở phần tham khảo.
    def is_official(p: dict) -> bool:
        if p.get("label_status") not in {"reviewed", "expert_source_translated"}:
            return False
        return not (a.variant == "patient" and p.get("vitals_dependent"))

    official = [p for p in preds if is_official(p)]
    draft = [p for p in preds if not is_official(p)]
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    lines = [f"# Triage eval ({a.split}, {a.variant})", f"- git: {sha or 'n/a'} | dataset sha256: {h} | KB: {kb} | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             f"- Ca tính điểm chính thức: {len(official)} | ca tham khảo: {len(draft)}"]
    if a.split.startswith("etek"):
        lines.append("- Nguồn: based on Commonwealth of Australia (Department of Health and Aged Care) material, "
                     "ETEK 2nd ed., CC BY 4.0. Nhãn ATS của chuyên gia; bản tiếng Việt do AI dịch.")
    if len(official) < 100:
        lines.append("- ⚠️ Dưới 100 ca chính thức: kết quả chỉ mang tính tham khảo (CI rất rộng).")
    for title, group in (("CHÍNH THỨC", official), ("THAM KHẢO (nhãn nháp / ca cần sinh hiệu)", draft)):
        lines += ["", f"## {title}"]
        if not group:
            lines.append("Chưa có ca."); continue
        for k, (a_, b_) in score(group).items():
            if b_:  # bỏ chỉ số không áp dụng cho tập này
                lines.append(f"- {k} ({DIRECTION.get(k, '↑')}): {fmt(a_, b_)}")
        kappa = weighted_kappa(group)
        lines.append(f"- weighted_kappa_quadratic (↑): {kappa:.3f}" if kappa is not None else "- weighted_kappa: n/a")
        lines += ["", "Ma trận nhầm lẫn ATS:", *confusion(group)]
        by = defaultdict(list)
        for g in group:
            by[g.get("stratum", "?")].append(g)
        lines.append("\n| stratum | n | emergency recall | ATS exact | top1 chuyên khoa |\n|---|---|---|---|---|")
        for s, g in sorted(by.items()):
            sc = score(g)
            lines.append(f"| {s} | {len(g)} | {sc['emergency_recall'][0]}/{sc['emergency_recall'][1]} | {sc['ats_exact'][0]}/{sc['ats_exact'][1]} | {sc['specialty_top1_all'][0]}/{sc['specialty_top1_all'][1]} |")
        miss = [g for g in group if g["gold_ats"] <= 2 and not g["pred_emergency"]]
        lines.append(f"\nBỎ SÓT cấp cứu ({len(miss)}):" + "".join(f"\n- [{g['id']}] {g['query']} (pred ATS {g['pred_ats']})" for g in miss))
        over = [g for g in group if g["gold_ats"] >= 3 and g["pred_emergency"]]
        lines.append(f"\nBÁO ĐỘNG NHẦM ({len(over)}):" + "".join(
            f"\n- [{g['id']}] {g['query']} (pred ATS {g['pred_ats']}; {'; '.join(g['pred_flags'][:1])})" for g in over))
        wrong = Counter((g["gold_specialty"], g["pred_top1"]) for g in group if g.get("gold_specialty") and g["gold_ats"] >= 3 and g["pred_top1"] != g["gold_specialty"])
        lines.append("\nNhầm lẫn chuyên khoa (gold → pred): " + (", ".join(f"{x}→{y} ×{n}" for (x, y), n in wrong.most_common(10)) or "không"))
        multi_miss = [g for g in group if g.get("gold_specialties") and not g["pred_emergency"]
                      and not {canon(x) for x in g["gold_specialties"]} <= {canon(x) for x in g["pred_recommended"]}]
        lines.append(f"\nĐA CHUYÊN KHOA thiếu ({len(multi_miss)}):" + "".join(
            f"\n- [{g['id']}] {g['query']} | cần {g['gold_specialties']} | gợi ý {g['pred_recommended']} | top1 {g['pred_top1']}"
            for g in multi_miss))
        incons = [g for g in group if g.get("pred_recommended") and not g["pred_emergency"]
                  and canon(g["pred_top1"]) not in {canon(x) for x in g["pred_recommended"]}]
        lines.append(f"\nTOP1 lệch danh sách gợi ý ({len(incons)}):" + "".join(
            f"\n- [{g['id']}] {g['query']} | top1 {g['pred_top1']} | gợi ý {g['pred_recommended']}" for g in incons))
    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    stamp = f"{a.split}_{a.variant}_{datetime.now():%Y%m%d_%H%M%S}"
    (outdir / f"{stamp}.md").write_text("\n".join(lines), encoding="utf-8")
    (outdir / f"{stamp}.json").write_text(json.dumps(preds, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))
    rec = score(official)["emergency_recall"] if official else None
    return 1 if rec and rec[0] < rec[1] else 0  # gate: không được bỏ sót cấp cứu đã duyệt


if __name__ == "__main__":
    raise SystemExit(main())
