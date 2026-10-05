# Local vector database

The application uses ChromaDB in `data/chroma/` (collection `vinmec_medical_rag`).
Git includes the integration and indexing script, but excludes the generated database and `.env`.
Cloning the repository does not download an existing vector index.

## Create an index on another machine

1. Install dependencies from `requirements.txt` in your Python environment.
2. Configure `GOOGLE_AI_API_KEY` in your local `.env`. Optionally configure
   `CHROMA_PERSIST_DIR` (default: `./data/chroma`).
3. From the repository root, run:

```shell
python scripts/build_vector_store.py
```

This calls the Gemini embedding API and may consume API quota. The script skips IDs
already indexed. Use `--rebuild` only when you intend to delete and recreate the collection.

The default sources are:

- `data/datalake/rag/specialties.jsonl` (tracked in Git).
- `data/datalake/rag/disease_education.jsonl` (local, ignored by Git).
- `data/datalake/rag/services.jsonl` (local, ignored by Git).

Missing sources are skipped. A fresh clone can build the specialty index; reproducing
the complete local index requires supplying the same optional source files separately.
Restart the backend after indexing so the cached RAG store can discover the index.

## Move the existing index

Stop the backend before copying the complete `data/chroma/` directory to the destination.
Copying only `chroma.sqlite3` does not include all Chroma index files.
Use compatible ChromaDB versions, keep the same embedding model, and configure the API
key on the destination for query embeddings. Store the directory on persistent storage
when deploying. GitHub push uploads code; it does not migrate a database or deploy the app.
