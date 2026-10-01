"""Assemble reproducible production data artifacts under ``data/datalake``."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from src.medical_assistant.ingestion.crawlers.diseases.build_rag_documents import main as build_disease_rag
from src.medical_assistant.ingestion.crawlers.diseases.build_specialty_facilities import (
    main as build_specialty_facilities,
)
from src.medical_assistant.ingestion.crawlers.diseases.build_symptom_routes import main as build_symptom_routes
from src.medical_assistant.ingestion.crawlers.services.build_rag_documents import main as build_service_rag

ROOT = Path(__file__).resolve().parents[3]
CRAWLED = ROOT / "data" / "crawled"
REFERENCE = ROOT / "data" / "reference"
DATALAKE = ROOT / "data" / "datalake"

ARTIFACTS = {
    CRAWLED / "doctors" / "processed" / "jsonl" / "vinmec_professionals_all.jsonl": DATALAKE
    / "normalized"
    / "doctors.jsonl",
    CRAWLED / "specialties" / "processed" / "jsonl" / "vinmec_specialties_all.jsonl": DATALAKE
    / "normalized"
    / "specialties.jsonl",
    CRAWLED / "hospitals" / "processed" / "jsonl" / "vinmec_hospitals_all.jsonl": DATALAKE
    / "normalized"
    / "hospitals.jsonl",
    CRAWLED / "diseases" / "processed" / "jsonl" / "vinmec_diseases_all.jsonl": DATALAKE
    / "normalized"
    / "diseases.jsonl",
    CRAWLED / "services" / "processed" / "jsonl" / "vinmec_services_all.jsonl": DATALAKE
    / "normalized"
    / "services.jsonl",
    CRAWLED / "doctors" / "rag" / "documents.jsonl": DATALAKE / "rag" / "doctors.jsonl",
    CRAWLED / "specialties" / "rag" / "documents.jsonl": DATALAKE / "rag" / "specialties.jsonl",
    CRAWLED / "services" / "rag" / "documents.jsonl": DATALAKE / "rag" / "services.jsonl",
}

for name in (
    "booking_policy",
    "doctors",
    "facilities",
    "services",
    "specialties",
    "symptom_specialty_mapping",
):
    ARTIFACTS[REFERENCE / "service_policy" / f"{name}.jsonl"] = DATALAKE / "service_policy" / f"{name}.jsonl"


def _line_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig") as source:
        return sum(1 for line in source if line.strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    build_service_rag([])
    build_disease_rag([])
    build_symptom_routes([])
    build_specialty_facilities([])
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "built_at": datetime.now(UTC).isoformat(),
        "artifacts": [],
    }
    for source, target in ARTIFACTS.items():
        if not source.is_file():
            raise FileNotFoundError(f"Missing production source artifact: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    targets = [
        *ARTIFACTS.values(),
        DATALAKE / "rag" / "disease_education.jsonl",
        DATALAKE / "rag" / "symptom_specialty_mapping.jsonl",
        DATALAKE / "rag" / "specialty_facilities.jsonl",
    ]
    for target in targets:
        manifest["artifacts"].append(
            {
                "path": target.relative_to(DATALAKE).as_posix(),
                "records": _line_count(target),
                "bytes": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )
    manifest_path = DATALAKE / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"artifacts: {len(targets)}")
    print(f"saved: {manifest_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
