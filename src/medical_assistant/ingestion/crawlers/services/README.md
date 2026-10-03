# Vinmec Online service crawler

Run from the repository root. Discovery uses the public sitemap as the source of
truth and the unfiltered `/vn/dich-vu` page as a cross-check. It does not request
the filter/sort URLs disallowed by `robots.txt`.

```powershell
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --discover
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --resume
```

Useful maintenance commands:

```powershell
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --max-services 5
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --retry-failed
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --rebuild
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.services --fresh
```

The crawler keeps sitemap/listing snapshots under `raw/vi/listings`, public API
responses under `raw/vi/services/<slug>`, its append-only source of truth under
`processed/jsonl`, rebuilt JSON representations under `processed/json`, RAG
chunks under `rag`, and durable progress/error information under `checkpoints`
and `errors`.
