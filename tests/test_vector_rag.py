"""Unit tests for ChromaDB Vector Store and HybridRagStore."""

from src.medical_assistant.rag.store_cache import get_global_rag_store


def test_hybrid_rag_store_initialization():
    store = get_global_rag_store()
    assert store is not None
    assert hasattr(store, "search")
    assert hasattr(store, "matching_entity")


def test_vector_search_specialty_retrieval():
    store = get_global_rag_store()
    passages = store.search("tôi bị đau ngực khó thở", limit=3)
    assert len(passages) > 0
    # Should contain relevant clinical passages with source URL
    assert all(hasattr(p, "text") for p in passages)
    assert all(hasattr(p, "source_url") for p in passages)
    assert all(hasattr(p, "title") for p in passages)
    assert all(len(p.source_url) > 0 for p in passages)


def test_vector_search_with_category_filter():
    store = get_global_rag_store()
    passages = store.search("khám tai mũi họng", limit=3, categories={"specialty"})
    assert len(passages) > 0
    for p in passages:
        assert p.category == "specialty"
