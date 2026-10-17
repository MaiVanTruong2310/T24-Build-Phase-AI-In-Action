"""Tách 132 tình huống + đáp án ATS từ ETEK (Emergency Triage Education Kit, 2nd ed.) thành JSONL.

Nguồn: based on Commonwealth of Australia (Department of Health and Aged Care) material, CC BY 4.0.
  python eval/triage_eval/import_etek.py "context_agent/emergency_triage_education_kit_-_second_edition.docx"
Ra: eval/triage_eval/data/etek_source_en.jsonl (bản gốc tiếng Anh, chưa dịch, nhãn của chuyên gia).
"""

from __future__ import annotations

import html
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

OUT = Path(__file__).parent / "data" / "etek_source_en.jsonl"
# Lý do chấm dựa vào số đo tại phòng cấp cứu → bệnh nhân chat không tự báo được; chấm riêng.
VITALS_RE = re.compile(
    r"spo2|sats?\b|saturation|gcs|blood pressure|\bbp\b|systolic|heart rate|\bhr\b|tachycard|bradycard|"
    r"respiratory rate|resp(?:iratory)? rate|haemodynamic|hemodynamic|perfusion|capillary refill|bgl|glucose|"
    r"temperature of|\d+\s*(?:mmhg|bpm|breaths)",
    re.IGNORECASE,
)


def docx_lines(path: Path) -> list[str]:
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    text = html.unescape(re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n")))
    return [line.strip() for line in text.split("\n")]


def parse(lines: list[str]) -> list[dict]:
    answers_at = max(i for i, line in enumerate(lines) if line == "Answers")
    scenarios: dict[int, str] = {}
    for i, line in enumerate(lines[:answers_at]):
        m = re.fullmatch(r"Scenario (\d{1,3})", line)
        if m:
            body = []
            for nxt in lines[i + 1 :]:
                if nxt.startswith("Triage category?"):
                    break
                if nxt:
                    body.append(nxt)
            scenarios[int(m.group(1))] = " ".join(body)

    answers: dict[int, tuple[int, str]] = {}
    i = answers_at + 1
    while i < len(lines) - 2:
        if re.fullmatch(r"\d{1,3}", lines[i]) and re.fullmatch(r"[1-5]", lines[i + 1]):
            sid = int(lines[i])
            if sid in answers:
                break
            answers[sid] = (int(lines[i + 1]), lines[i + 2])
            i += 3
        else:
            i += 1

    rows = []
    for sid in sorted(scenarios):
        ats, rationale = answers[sid]
        rows.append(
            {
                "id": f"ETEK-{sid:03d}",
                "source": "ETEK 2nd ed. ch.10 (CC BY 4.0)",
                "scenario_en": scenarios[sid],
                "gold_ats": ats,
                "rationale_en": rationale,
                "vitals_dependent": bool(VITALS_RE.search(rationale)),
                "label_status": "expert_source",
            }
        )
    return rows


def main() -> int:
    rows = parse(docx_lines(Path(sys.argv[1])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} tình huống → {OUT}")
    print("ATS:", sorted(Counter(r["gold_ats"] for r in rows).items()))
    print("Phụ thuộc số đo sinh hiệu:", sum(r["vitals_dependent"] for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
