"""Build and optionally apply verified doctor-to-facility relationships.

Dry run is the default. Use ``--apply`` to upsert the generated rows through the
configured PostgreSQL connection. Existing relationships are never deleted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.medical_assistant.db.supabase_client import get_supabase_client
from src.config import Settings
from src.medical_assistant.domain.facility_linking import (
    canonical_facilities,
    extract_workplaces_from_record,
    facility_key,
    match_facility,
    workplace_department,
)

CRAWL_PATH = ROOT / "data" / "crawled" / "doctors" / "processed" / "jsonl" / "vinmec_professionals_vi.jsonl"

DEFAULT_REPORT = ROOT / "data" / "generated" / "doctor_facility_link_plan.json"
DEFAULT_SQL = ROOT / "scripts" / "supabase" / "migrations" / "20261003000000_link_all_doctors_to_facilities.sql"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _crawl_record_for_doctor(
    doctor: dict[str, Any], crawl_rows: list[dict[str, Any]], unique_names: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any] | None, str]:
    match = re.fullmatch(r"doc-vinmec-(\d+)", str(doctor.get("external_id") or ""))
    if match:
        index = int(match.group(1)) - 1
        if 0 <= index < len(crawl_rows):
            record = crawl_rows[index]
            if str(record.get("name") or "").strip() == str(doctor.get("full_name") or "").strip():
                return record, "external_sequence_and_name"
    record = unique_names.get(str(doctor.get("full_name") or "").strip())
    return (record, "unique_name") if record else (None, "no_unambiguous_crawl_record")


def build_plan(client: Any | None = None) -> dict[str, Any]:
    client = client or get_supabase_client()
    crawl_rows = read_jsonl(CRAWL_PATH)
    doctors = client.select(
        "doctors",
        params={"select": "id,external_id,full_name", "order": "external_id.asc", "limit": 5000},
    )
    facility_rows = client.select(
        "facilities",
        params={"select": "id,code,name,address,status", "limit": 500},
    )
    facilities = canonical_facilities(facility_rows)

    # Also map canonical key -> list of duplicate/English facility rows
    key_to_all_facilities: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in facility_rows:
        key = facility_key(row.get("name")) or facility_key(row.get("code"))
        if key:
            key_to_all_facilities[key].append(row)

    names: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in crawl_rows:
        names[str(row.get("name") or "").strip()].append(row)
    unique_names = {name: rows[0] for name, rows in names.items() if name and len(rows) == 1}

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    matched_doctors: set[str] = set()
    doctor_match_methods: dict[str, int] = defaultdict(int)

    for doctor in doctors:
        record, method = _crawl_record_for_doctor(doctor, crawl_rows, unique_names)
        doctor_match_methods[method] += 1
        if not record:
            issues.append({
                "type": method,
                "doctor_id": doctor.get("id"),
                "external_id": doctor.get("external_id"),
                "doctor_name": doctor.get("full_name"),
            })
            continue

        workplaces = extract_workplaces_from_record(record)
        mapped_any = False

        for workplace in workplaces:
            facility = match_facility(workplace, facilities)
            if not facility:
                issues.append({
                    "type": "unmapped_workplace",
                    "doctor_id": doctor["id"],
                    "external_id": doctor.get("external_id"),
                    "doctor_name": doctor.get("full_name"),
                    "workplace": workplace,
                })
                continue

            mapped_any = True
            key = facility_key(workplace)
            all_target_facilities = key_to_all_facilities.get(key, [facility]) if key else [facility]

            for target_fac in all_target_facilities:
                g_key = (str(doctor["id"]), str(target_fac["id"]))
                item = grouped.setdefault(g_key, {
                    "doctor_id": str(doctor["id"]),
                    "facility_id": str(target_fac["id"]),
                    "department": None,
                    "room": "",
                    "status": "active",
                    "doctor_name": doctor.get("full_name"),
                    "facility_name": target_fac.get("name"),
                    "is_canonical": target_fac["id"] == facility["id"],
                    "source_workplaces": [],
                    "departments": [],
                })
                item["source_workplaces"].append(workplace)
                department = workplace_department(workplace)
                if department and department not in item["departments"]:
                    item["departments"].append(department)

        if mapped_any:
            matched_doctors.add(str(doctor["id"]))
        else:
            issues.append({
                "type": "missing_workplace",
                "doctor_id": doctor["id"],
                "external_id": doctor.get("external_id"),
                "doctor_name": doctor.get("full_name"),
            })

    links = sorted(grouped.values(), key=lambda row: (str(row["doctor_name"]), str(row["facility_name"])))
    for row in links:
        dept = " | ".join(row.pop("departments")) or None
        if dept and len(dept) > 160:
            dept = dept[:157] + "..."
        row["department"] = dept

    canonical_links = [l for l in links if l.get("is_canonical")]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "upsert_all_facilities",
        "stats": {
            "crawl_records": len(crawl_rows),
            "database_doctors": len(doctors),
            "database_facilities": len(facility_rows),
            "canonical_facilities": len(facilities),
            "linked_doctors": len(matched_doctors),
            "unlinked_doctors": len(doctors) - len(matched_doctors),
            "canonical_relationships": len(canonical_links),
            "total_relationships_including_en_alias": len(links),
            "issues": len(issues),
            "doctor_match_methods": dict(sorted(doctor_match_methods.items())),
        },
        "links": links,
        "issues": issues,
    }


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def render_sql(plan: dict[str, Any]) -> str:
    values = []
    for row in plan["links"]:
        values.append(
            "(" + ", ".join(
                _sql_literal(row.get(field))
                for field in ("doctor_id", "facility_id", "department", "room", "status")
            ) + ")"
        )
    return "\n".join([
        "-- Generated by scripts/link_doctors_to_facilities.py; upsert only, no deletes.",
        "BEGIN;",
        "",
        "-- 1. Hide duplicate English facility records and mock test records from public dropdowns",
        "UPDATE public.facilities",
        "SET status = 'inactive'",
        "WHERE code LIKE 'VINMEC_%' OR code = 'COS-01';",
        "",
        "-- 2. Upsert comprehensive doctor-facility relationships",
        "INSERT INTO public.doctor_facilities (doctor_id, facility_id, department, room, status)",
        "VALUES",
        ",\n".join(values),
        "ON CONFLICT (doctor_id, facility_id) DO UPDATE SET",
        "  department = EXCLUDED.department,",
        "  room = EXCLUDED.room,",
        "  status = EXCLUDED.status;",
        "",
        "-- 3. Orphan verification",
        "DO $validation$",
        "BEGIN",
        "  IF EXISTS (",
        "    SELECT 1 FROM public.doctor_facilities df",
        "    LEFT JOIN public.doctors d ON d.id = df.doctor_id",
        "    LEFT JOIN public.facilities f ON f.id = df.facility_id",
        "    WHERE d.id IS NULL OR f.id IS NULL",
        "  ) THEN",
        "    RAISE EXCEPTION 'doctor_facilities contains orphan relationships';",
        "  END IF;",
        "END $validation$;",
        "",
        "COMMIT;",
        "",
    ])


def apply_plan(plan: dict[str, Any], database_url: str) -> dict[str, int]:
    rows = [
        (row["doctor_id"], row["facility_id"], row.get("department"), row.get("room") or "", row["status"])
        for row in plan["links"]
    ]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            # 1. Update duplicate English and mock facilities to inactive
            cursor.execute(
                """
                UPDATE public.facilities
                SET status = 'inactive'
                WHERE code LIKE 'VINMEC_%' OR code = 'COS-01'
                """
            )
            deactivated = cursor.rowcount

            # 2. Upsert links
            cursor.executemany(
                """
                INSERT INTO public.doctor_facilities
                    (doctor_id, facility_id, department, room, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doctor_id, facility_id) DO UPDATE SET
                    department = EXCLUDED.department,
                    room = EXCLUDED.room,
                    status = EXCLUDED.status
                """,
                rows,
            )
            cursor.execute("SELECT count(*) FROM public.doctor_facilities")
            total = int(cursor.fetchone()[0])

            # 3. Check orphans
            cursor.execute(
                """
                SELECT count(*)
                FROM public.doctor_facilities df
                LEFT JOIN public.doctors d ON d.id = df.doctor_id
                LEFT JOIN public.facilities f ON f.id = df.facility_id
                WHERE d.id IS NULL OR f.id IS NULL
                """
            )
            orphans = int(cursor.fetchone()[0])
            if orphans > 0:
                raise RuntimeError(f"Detected {orphans} orphan records in doctor_facilities")

        connection.commit()
    return {"deactivated_facilities": deactivated, "upserted": len(rows), "database_total": total, "orphans": orphans}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Upsert verified links into Supabase PostgreSQL")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--sql-output", type=Path, default=DEFAULT_SQL)
    args = parser.parse_args()

    print("Building doctor-facility linking plan...")
    plan = build_plan()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote plan report to: {args.output}")

    sql_content = render_sql(plan)
    args.sql_output.parent.mkdir(parents=True, exist_ok=True)
    args.sql_output.write_text(sql_content, encoding="utf-8")
    print(f"Wrote SQL migration to: {args.sql_output}")

    stats = plan["stats"]
    print("\n--- Plan Summary ---")
    print(f"Total database doctors: {stats['database_doctors']}")
    print(f"Linked doctors: {stats['linked_doctors']} / {stats['database_doctors']} ({stats['linked_doctors']/stats['database_doctors']*100:.1f}%)")
    print(f"Unlinked doctors: {stats['unlinked_doctors']}")
    print(f"Canonical relationships: {stats['canonical_relationships']}")
    print(f"Total relationships (including EN alias): {stats['total_relationships_including_en_alias']}")
    print(f"Issues: {stats['issues']}")

    if args.apply:
        settings = Settings()
        if not settings.database_url:
            print("ERROR: DATABASE_URL is not set in environment or .env", file=sys.stderr)
            return 1
        print("\nApplying plan to Supabase PostgreSQL database...")
        res = apply_plan(plan, settings.database_url)
        print("Application successful!")
        print(f"  Deactivated duplicate facilities: {res['deactivated_facilities']}")
        print(f"  Upserted relationships: {res['upserted']}")
        print(f"  Total doctor_facilities in DB: {res['database_total']}")
        print(f"  Orphans: {res['orphans']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
