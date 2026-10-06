"""Compiler script: Biên dịch dữ liệu thô (Datalake/SQL) thành Compiled Wiki Markdown (Karpathy LLM Wiki Pattern)."""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATALAKE_DIR = PROJECT_ROOT / "data" / "datalake"
OUTPUT_DIR = PROJECT_ROOT / "data" / "compiled_wiki"


def compile_wiki():
    fac_out = OUTPUT_DIR / "facilities"
    spec_out = OUTPUT_DIR / "specialties"
    fac_out.mkdir(parents=True, exist_ok=True)
    spec_out.mkdir(parents=True, exist_ok=True)

    hospitals_file = DATALAKE_DIR / "normalized" / "hospitals.jsonl"
    count = 0
    if hospitals_file.exists():
        with open(hospitals_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                hosp = json.loads(line)
                name = hosp.get("name", "")
                if not name:
                    continue
                # Tạo file slug
                slug = name.lower().replace(" ", "_").replace("đ", "d").replace("-", "_")
                slug = "".join(c for c in slug if c.isalnum() or c == "_")
                file_path = fac_out / f"{slug}.md"
                if not file_path.exists():
                    md_content = f"""# {name}

## 1. Thông Tin Cơ Bản
- **Địa chỉ:** {hosp.get("address", "Hệ thống Vinmec")}
- **Hotline:** {hosp.get("phone", "1900 23 23 89")}
- **Thời gian làm việc:** Thứ 2 – Thứ 6 (08:00 – 17:00), Cấp cứu 24/7.

## 2. Giới Thiệu
{hosp.get("description", "Cơ sở khám chữa bệnh chất lượng cao tiêu chuẩn quốc tế thuộc Hệ thống Y tế Vinmec.")}
"""
                    file_path.write_text(md_content, encoding="utf-8")
                    count += 1

    print(f"Compilation finished. Generated {count} new compiled wiki pages in {OUTPUT_DIR}")


if __name__ == "__main__":
    compile_wiki()
