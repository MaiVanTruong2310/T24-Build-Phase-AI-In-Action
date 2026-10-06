"""Script to index JSONL medical records into local ChromaDB vector store."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.medical_assistant.config import get_settings
from src.medical_assistant.rag.chroma_store import ChromaRagStore
from src.medical_assistant.rag.embeddings import GeminiEmbeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SOURCE_FILES = (
    PROJECT_ROOT / "data" / "datalake" / "rag" / "specialties.jsonl",
    PROJECT_ROOT / "data" / "datalake" / "rag" / "disease_education.jsonl",
    PROJECT_ROOT / "data" / "datalake" / "rag" / "services.jsonl",
)


def load_records(files: tuple[Path, ...]) -> list[dict]:
    records: list[dict] = []
    seen_ids: set[str] = set()

    for path in files:
        if not path.is_file():
            logger.info("File not found, skipping: %s", path)
            continue

        logger.info("Reading source: %s", path)
        with path.open(encoding="utf-8-sig") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                chunk_id = str(data.get("chunk_id") or f"{path.stem}-{line_no}")
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)

                text = str(data.get("text") or "").strip()
                if not text:
                    continue

                metadata = data.get("metadata") or {}
                category = str(metadata.get("category") or "specialty")
                name = str(metadata.get("name") or "Unknown")
                source_url = str(metadata.get("source_url") or "")
                section = str(metadata.get("section") or "")
                language = str(metadata.get("language") or "vi")

                records.append({
                    "id": chunk_id,
                    "text": text,
                    "metadata": {
                        "name": name,
                        "title": name,
                        "source_url": source_url,
                        "category": category,
                        "section": section,
                        "language": language,
                    },
                })

    logger.info("Total searchable chunks loaded: %d", len(records))
    return records


def build_vector_store(rebuild: bool = False, batch_size: int = 30) -> None:
    settings = get_settings()
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = GeminiEmbeddings()
    store = ChromaRagStore(persist_dir=persist_dir, embeddings=embeddings)

    if rebuild and store.count > 0:
        logger.info("Rebuild requested: Clearing existing collection...")
        store.client.delete_collection(name=store.collection.name)
        store.collection = store.client.get_or_create_collection(name=store.collection.name)

    existing_ids = set()
    if not rebuild and store.count > 0:
        # Fetch existing IDs in batches of 1000
        existing_data = store.collection.get()
        existing_ids = set(existing_data.get("ids", []))
        logger.info("Found %d records already indexed in ChromaDB.", len(existing_ids))

    records = load_records(DEFAULT_SOURCE_FILES)
    if not records:
        logger.warning("No records found to index.")
        return

    # Filter out already indexed records
    pending_records = [r for r in records if r["id"] not in existing_ids]
    if not pending_records:
        logger.info("All %d records are already indexed in ChromaDB! Nothing to do.", len(records))
        return

    total = len(pending_records)
    logger.info("Embedding and indexing %d pending documents into ChromaDB (batch_size=%d)...", total, batch_size)

    for i in range(0, total, batch_size):
        batch = pending_records[i : i + batch_size]
        texts = [item["text"] for item in batch]
        ids = [item["id"] for item in batch]
        metadatas = [item["metadata"] for item in batch]

        logger.info("Generating embeddings for batch %d..%d / %d", i + 1, min(i + batch_size, total), total)
        vectors = embeddings.embed_documents(texts, batch_size=batch_size)

        store.collection.add(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

    logger.info("Successfully indexed %d records into ChromaDB at %s", store.count, persist_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index medical records into ChromaDB vector store")
    parser.add_argument("--rebuild", action="store_true", help="Clear and rebuild index from scratch")
    parser.add_argument("--batch-size", type=int, default=30, help="Batch size for embeddings")
    args = parser.parse_args()

    build_vector_store(rebuild=args.rebuild, batch_size=args.batch_size)
