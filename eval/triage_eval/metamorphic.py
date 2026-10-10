"""Kiểm thử biến đổi (metamorphic) cho triage: không cần nhãn, chỉ kiểm tra tính nhất quán.

  python eval/triage_eval/metamorphic.py            # chạy trên dev + etek_dev (không dùng tập test khóa)
Quan hệ kiểm tra:
  R1 bỏ dấu tiếng Việt       → không được hạ mức xử trí (cấp cứu / trong ngày / thường)
  R2 thêm câu không liên quan → ATS không đổi
  R3 đảo thứ tự các vế câu    → mức xử trí không đổi
  R4 thêm dấu hiệu nguy kịch  → bắt buộc thành cấp cứu (ATS 1-2)
Exit code 1 nếu có vi phạm nguy hiểm (R1 hạ mức, R4 không lên cấp cứu).
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DATA = Path(__file__).parent / "data"


def strip_accents(text: str) -> str:
    value = unicodedata.normalize("NFD", text)
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def disposition(ats: int) -> int:
    return 0 if ats <= 2 else 1 if ats == 3 else 2


def main() -> int:
    from src.medical_assistant.domain.triage_service import get_triage_service

    svc = get_triage_service()
    rows = []
    for split in ("dev", "etek_dev"):
        for line in (DATA / f"{split}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows.append((r["id"], r.get("query") or " ".join(r.get("turns") or [])))

    def ats(text: str) -> int:
        return svc.evaluate_symptoms(text).ats_level.value

    viol: dict[str, list[str]] = {"R1_lower": [], "R1_changed": [], "R2": [], "R3": [], "R4": []}
    for rid, q in rows:
        base = ats(q)
        a1 = ats(strip_accents(q))
        if disposition(a1) > disposition(base):
            viol["R1_lower"].append(f"[{rid}] {base}→{a1} | {q[:90]}")
        elif a1 != base:
            viol["R1_changed"].append(f"[{rid}] {base}→{a1}")
        a2 = ats(q.rstrip(" .") + ". À mà hôm nay trời mưa to quá.")
        if a2 != base:
            viol["R2"].append(f"[{rid}] {base}→{a2} | {q[:90]}")
        parts = [p.strip() for p in re.split(r"[,;]", q) if p.strip()]
        if len(parts) >= 2:
            a3 = ats(", ".join(reversed(parts)))
            if disposition(a3) != disposition(base):
                viol["R3"].append(f"[{rid}] {base}→{a3} | {q[:90]}")
        a4 = ats(q.rstrip(" .") + ". Giờ thì môi tím tái, gọi không tỉnh.")
        if a4 > 2:
            viol["R4"].append(f"[{rid}] →{a4} | {q[:90]}")

    n = len(rows)
    print(f"# Metamorphic triage ({n} câu từ dev + etek_dev)")
    labels = {
        "R1_lower": "R1 bỏ dấu làm HẠ mức xử trí (nguy hiểm)",
        "R1_changed": "R1 bỏ dấu làm đổi ATS (cùng mức xử trí)",
        "R2": "R2 thêm câu không liên quan làm đổi ATS",
        "R3": "R3 đảo thứ tự làm đổi mức xử trí",
        "R4": "R4 thêm dấu hiệu nguy kịch mà KHÔNG lên cấp cứu (nguy hiểm)",
    }
    for key, title in labels.items():
        print(f"\n## {title}: {len(viol[key])}/{n}")
        for item in viol[key][:15]:
            print(f"- {item}")
    return 1 if viol["R1_lower"] or viol["R4"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
