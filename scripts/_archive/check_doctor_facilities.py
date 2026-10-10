import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import text
from src.db.session import get_session_factory

# Load crawled data
crawled_map = {}
with open("data/crawled/doctors/processed/jsonl/vinmec_professionals_vi.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        name = item.get("name")
        workplace = item.get("sections", {}).get("Nơi làm việc", [])
        if not workplace:
            workplace = item.get("workplace", [])
        crawled_map[name] = workplace

print(f"Total crawled profiles: {len(crawled_map)}")


async def check():
    factory = get_session_factory()
    async with factory() as session:
        db_docs = (
            await session.execute(
                text("""
            SELECT d.id, d.full_name, f.name, f.id
            FROM doctors d
            LEFT JOIN doctor_facilities df ON df.doctor_id = d.id
            LEFT JOIN facilities f ON f.id = df.facility_id
        """)
            )
        ).all()

        matches = 0
        mismatches = 0
        no_links = 0
        not_in_crawled = 0

        for doc_id, full_name, fac_name, fac_id in db_docs:
            if not fac_name:
                no_links += 1
                continue
            crawled_places = crawled_map.get(full_name, [])
            if not crawled_places:
                not_in_crawled += 1
                continue

            matched = any(fac_name.lower() in cp.lower() or cp.lower() in fac_name.lower() for cp in crawled_places)
            if matched:
                matches += 1
            else:
                mismatches += 1
                if mismatches <= 15:
                    print(f"MISMATCH: Doctor '{full_name}': DB='{fac_name}' vs Crawled={crawled_places}")

        print(f"\nSummary -> Matches: {matches}, Mismatches: {mismatches}, No Links: {no_links}, Not in crawl: {not_in_crawled}")


asyncio.run(check())
