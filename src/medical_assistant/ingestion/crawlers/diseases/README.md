# Vinmec disease crawler

Run from `D:\AI in Action\LogAgent\P-124` with the project virtual environment:

```cmd
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --discover
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --resume
```

Discovery merges Vinmec's `sitemap/diseases-vi-1.xml` with the A–Z index starting at `https://www.vinmec.com/vie/benh/`, then writes `data/crawled/diseases/urls_crawl.txt` and `discovery_summary.json`. The sitemap is important: Vinmec currently advertises some `/vie/tra-cuu-benh/page_N` links that return no disease URLs. Inspect `sitemap_url_count`, `complete_traversal`, and `anomalies`; an empty page anomaly does not invalidate sitemap URLs, but a sitemap fetch error does mean discovery may be incomplete.

The crawler checks robots.txt, waits 2 seconds between requests by default, and writes each successful record immediately to `processed/jsonl/vinmec_diseases_vi.jsonl`. It also writes `errors/failed_urls.jsonl` and `checkpoints/vi_state.json`. On completion it rebuilds `processed/json/vinmec_diseases_vi.json` and `vinmec_diseases_all.*`. Raw HTML is saved under `raw/vi` by default.

Useful commands:

```cmd
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --max-diseases 5 --resume
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --retry-failed
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --rebuild
.venv\Scripts\python.exe -m src.medical_assistant.ingestion.crawlers.diseases --fresh
```

`--resume` is the default behavior; existing successful URLs are skipped. `--fresh` archives primary JSONL and failure log before a new run. The records preserve Vinmec's source text and section headings. They do **not** classify severity, infer symptoms from a patient's text, or recommend specialties; those require a separately validated clinical mapping and safety workflow.
