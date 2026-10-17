# Vinmec hospitals and clinics crawler

This is a shallow crawler. It reads the Vietnamese and English listing pages
only; it does not request individual facility detail pages.

Run from the repository root:

```powershell
python -m src.medical_assistant.ingestion.crawlers.hospitals
```

Optional commands:

```powershell
python -m src.medical_assistant.ingestion.crawlers.hospitals --language vi
python -m src.medical_assistant.ingestion.crawlers.hospitals --language en
python -m src.medical_assistant.ingestion.crawlers.hospitals --no-raw
```

Output layout:

```text
data/crawled/hospitals/
├── raw/
│   ├── vi/hospitals.html
│   └── en/hospitals.html
└── processed/
    ├── json/
    │   ├── vinmec_hospitals_vi.json
    │   ├── vinmec_hospitals_en.json
    │   ├── vinmec_hospitals_all.json
    │   └── crawl_summary.json
    └── jsonl/
        ├── vinmec_hospitals_vi.jsonl
        ├── vinmec_hospitals_en.jsonl
        └── vinmec_hospitals_all.jsonl
```

Each record contains the facility key, language, name, type, address, displayed
and normalized hotline, detail URL, listing source URL, and crawl timestamp.
These structured records are intended for later database upserts; no RAG
document is generated for this dataset.

