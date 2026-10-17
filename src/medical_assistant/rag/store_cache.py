"""Singleton cache and Hybrid RAG retrieval store combining Vector (Chroma) + FTS (BM25)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from src.medical_assistant.config import get_settings
from src.medical_assistant.rag.service import Passage, RagStore

logger = logging.getLogger(__name__)


class HybridRagStore:
    """Hybrid Retrieval combining ChromaDB Vector Search + SQLite FTS5 Keyword Search."""

    def __init__(self) -> None:
        self.fts_store = RagStore()
        self.chroma_store = None

        settings = get_settings()
        chroma_dir = Path(settings.chroma_persist_dir)
        if chroma_dir.exists():
            try:
                from src.medical_assistant.rag.chroma_store import ChromaRagStore

                c_store = ChromaRagStore()
                if c_store.count > 0:
                    self.chroma_store = c_store
                    logger.info("HybridRagStore initialized with %d vector documents in ChromaDB.", c_store.count)
            except Exception as exc:
                logger.warning("Failed to initialize ChromaRagStore, using FTS only: %s", exc)

    @property
    def connection(self):
        """Delegate SQLite connection to underlying fts_store for backward compatibility."""
        return self.fts_store.connection

    def matching_entity(self, query: str) -> tuple[str, str] | None:
        """Delegate exact entity matching to fts_store."""
        return self.fts_store.matching_entity(query)

    def search(
        self,
        query: str,
        limit: int = 6,
        categories: set[str] | None = None,
    ) -> list[Passage]:
        """Hybrid search combining semantic vector search and lexical FTS."""
        vector_passages: list[Passage] = []
        if self.chroma_store is not None:
            try:
                vector_passages = self.chroma_store.search(query, limit=limit, categories=categories)
            except Exception as exc:
                logger.warning("Chroma vector search failed, continuing with FTS: %s", exc)

        try:
            fts_passages = self.fts_store.search(query, limit=limit, categories=categories)
        except Exception:
            fts_passages = []

        # Merge with priority to semantic matches + deduplicate by source_url
        merged: list[Passage] = []
        seen_urls: set[str] = set()

        for passage in vector_passages:
            if passage.source_url not in seen_urls:
                seen_urls.add(passage.source_url)
                merged.append(passage)
                if len(merged) >= limit:
                    return merged

        for passage in fts_passages:
            if passage.source_url not in seen_urls:
                seen_urls.add(passage.source_url)
                merged.append(passage)
                if len(merged) >= limit:
                    return merged

        return merged


@lru_cache(maxsize=1)
def get_global_rag_store() -> HybridRagStore:
    return HybridRagStore()
