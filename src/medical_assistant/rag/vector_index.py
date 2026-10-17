"""Dựng/bổ sung chỉ mục ChromaDB từ các file JSONL nguồn trong data/datalake/rag/.

Thư mục Chroma không nằm trong git (data/ bị ignore) và Railway không có volume, nên mỗi lần deploy server
khởi động với Chroma rỗng → chỉ còn tìm kiếm FTS. `ensure_vector_index()` được gọi nền lúc khởi động để
dựng lại từ nguồn đi kèm code (chỉ embed phần còn thiếu, lần sau không tốn gì).
Dùng chung cho CLI `scripts/build_vector_store.py`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.medical_assistant.config import get_settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_FILES = (
    PROJECT_ROOT / "data" / "datalake" / "rag" / "specialties.jsonl",
    PROJECT_ROOT / "data" / "datalake" / "rag" / "disease_education.jsonl",
    PROJECT_ROOT / "data" / "datalake" / "rag" / "services.jsonl",
)


def load_records(files: tuple[Path, ...] = DEFAULT_SOURCE_FILES) -> list[dict]:
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
                name = str(metadata.get("name") or "Unknown")
                records.append(
                    {
                        "id": chunk_id,
                        "text": text,
                        "metadata": {
                            "name": name,
                            "title": name,
                            "source_url": str(metadata.get("source_url") or ""),
                            "category": str(metadata.get("category") or "specialty"),
                            "section": str(metadata.get("section") or ""),
                            "language": str(metadata.get("language") or "vi"),
                        },
                    }
                )

    logger.info("Total searchable chunks loaded: %d", len(records))
    return records


def build_vector_store(rebuild: bool = False, batch_size: int = 30) -> int:
    """Embed và nạp các đoạn còn thiếu vào Chroma. Trả về số đoạn vừa nạp thêm."""
    from src.medical_assistant.rag.chroma_store import ChromaRagStore
    from src.medical_assistant.rag.embeddings import GeminiEmbeddings

    persist_dir = Path(get_settings().chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = GeminiEmbeddings()
    store = ChromaRagStore(persist_dir=persist_dir, embeddings=embeddings)

    if rebuild and store.count > 0:
        logger.info("Rebuild requested: Clearing existing collection...")
        store.client.delete_collection(name=store.collection.name)
        store.collection = store.client.get_or_create_collection(name=store.collection.name)

    existing_ids: set[str] = set()
    if not rebuild and store.count > 0:
        existing_ids = set(store.collection.get().get("ids", []))
        logger.info("Found %d records already indexed in ChromaDB.", len(existing_ids))

    records = load_records()
    pending = [r for r in records if r["id"] not in existing_ids]
    if not pending:
        logger.info("All %d records are already indexed in ChromaDB.", len(records))
        return 0

    logger.info(
        "Embedding and indexing %d pending documents into ChromaDB (batch_size=%d)...", len(pending), batch_size
    )
    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        vectors = embeddings.embed_documents([item["text"] for item in batch], batch_size=batch_size)
        store.collection.add(
            ids=[item["id"] for item in batch],
            embeddings=vectors,
            documents=[item["text"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
        )

    logger.info("Indexed %d records into ChromaDB at %s (total %d)", len(pending), persist_dir, store.count)
    return len(pending)


def ensure_vector_index() -> int:
    """Gọi lúc khởi động (luồng nền): dựng phần chỉ mục còn thiếu rồi làm mới store RAG đang cache.

    Không bao giờ ném lỗi: thiếu khóa Gemini / lỗi mạng thì giữ nguyên tìm kiếm FTS như trước.
    """
    settings = get_settings()
    if not settings.google_ai_api_key:
        logger.info("Vector index skipped: GOOGLE_AI_API_KEY is not configured (FTS search only).")
        return 0
    try:
        added = build_vector_store()
    except Exception as exc:  # chỉ mục vector là phần bổ trợ, không được làm hỏng app
        logger.warning("Vector index build failed, keeping FTS-only search: %s", exc)
        return 0
    if added:
        from src.medical_assistant.rag.store_cache import get_global_rag_store

        get_global_rag_store.cache_clear()  # store cũ được dựng khi Chroma còn rỗng
    return added
