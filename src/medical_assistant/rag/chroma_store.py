"""ChromaDB Vector Store wrapper for Vinmec Medical Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb

from src.medical_assistant.config import get_settings
from src.medical_assistant.rag.embeddings import GeminiEmbeddings
from src.medical_assistant.rag.service import Passage

logger = logging.getLogger(__name__)

COLLECTION_NAME = "vinmec_medical_rag"


class ChromaRagStore:
    """Vector database retrieval using ChromaDB persistent client."""

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        embeddings: GeminiEmbeddings | None = None,
    ) -> None:
        settings = get_settings()
        self.persist_dir = str(persist_dir or settings.chroma_persist_dir)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
        self.embeddings = embeddings or GeminiEmbeddings()

    @property
    def count(self) -> int:
        """Return the number of vectorized passages in the collection."""
        return self.collection.count()

    def search(
        self,
        query: str,
        limit: int = 6,
        categories: set[str] | None = None,
    ) -> list[Passage]:
        """Search similar passages by embedding query and ranking by cosine distance."""
        if self.count == 0:
            return []

        try:
            query_vector = self.embeddings.embed_query(query)
        except Exception as exc:
            logger.warning("Failed to embed query for Chroma search: %s", exc)
            return []

        where_filter: dict[str, Any] | None = None
        if categories:
            cat_list = list(categories)
            if len(cat_list) == 1:
                where_filter = {"category": cat_list[0]}
            elif len(cat_list) > 1:
                where_filter = {"category": {"$in": cat_list}}

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": min(limit * 2, max(self.count, 1)),
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        try:
            raw_results = self.collection.query(**query_kwargs)
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []

        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]

        passages: list[Passage] = []
        seen_urls: set[str] = set()

        for doc, meta in zip(documents, metadatas):
            url = str(meta.get("source_url") or "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            passages.append(
                Passage(
                    text=doc,
                    source_url=url,
                    title=str(meta.get("name") or meta.get("title") or "Unknown"),
                    category=str(meta.get("category") or "specialty"),
                    language=str(meta.get("language") or "vi"),
                    section=str(meta.get("section") or ""),
                )
            )
            if len(passages) >= limit:
                break

        return passages
