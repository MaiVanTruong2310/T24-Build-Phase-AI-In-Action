"""Đồng bộ file KB dự phòng `data/datalake/normalized/diseases_triaged.jsonl` theo bảng Supabase `disease_triage`.

File này được dùng khi không kết nối được Supabase (CI, chạy offline). Sau mỗi migration sửa `disease_triage`
cần chạy lại script để CI/offline và production dùng cùng một bộ luật:

    python scripts/export_disease_triage_jsonl.py            # ghi file
    python scripts/export_disease_triage_jsonl.py --check    # chỉ báo khác biệt, exit 1 nếu lệch
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TARGET = ROOT / "data" / "datalake" / "normalized" / "diseases_triaged.jsonl"


def to_record(row: dict) -> dict:
    """Cùng cấu trúc mà ClinicalTriageService đọc từ file (DiseaseTriageRecord)."""
    return {
        "disease_key": row["disease_key"],
        "name": row["name"],
        "primary_specialty_code": row.get("primary_specialty_code") or "NOI_KHOA",
        "primary_specialty_name": row.get("primary_specialty_name") or "Nội khoa",
        "acuity": {
            "ats_level": row["ats_level"],
            "urgency_tier": row["urgency_tier"],
            "max_booking_days": row["max_booking_days"],
            "action_directive": row.get("action_directive") or "",
        },
        "symptom_hierarchy": {
            "red_flags": row.get("red_flags") or [],
            "warning_signs": row.get("warning_signs") or [],
            "typical_or_mild": row.get("typical_or_mild") or [],
        },
        "syndrome_combinations": row.get("syndrome_combinations") or [],
        "probing_questions": row.get("probing_questions") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Chỉ so sánh, không ghi file")
    args = parser.parse_args()

    from src.medical_assistant.db.supabase_client import get_supabase_client

    client = get_supabase_client()
    if client is None:
        print("Chưa cấu hình SUPABASE_URL/SUPABASE_KEY.", file=sys.stderr)
        return 2
    rows = client.select("disease_triage", params={"limit": 5000})
    remote = {r["disease_key"]: to_record(r) for r in rows}

    local: dict[str, dict] = {}
    if TARGET.exists():
        with TARGET.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    local[rec["disease_key"]] = rec

    changed = [k for k in remote if k in local and remote[k] != local[k]]
    added = [k for k in remote if k not in local]
    removed = [k for k in local if k not in remote]
    print(f"Supabase: {len(remote)} bệnh | file: {len(local)} | đổi: {len(changed)} | thêm: {len(added)} | bỏ: {len(removed)}")
    if args.check:
        return 1 if (changed or added or removed) else 0

    # Giữ thứ tự cũ để diff dễ đọc; bệnh mới nối cuối.
    order = [k for k in local if k in remote] + added
    with TARGET.open("w", encoding="utf-8", newline="\n") as f:
        for key in order:
            f.write(json.dumps(remote[key], ensure_ascii=False) + "\n")
    print(f"Đã ghi {len(order)} bệnh vào {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
