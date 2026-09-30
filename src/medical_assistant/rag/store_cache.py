from functools import lru_cache

from src.medical_assistant.rag.service import RagStore


@lru_cache(maxsize=1)
def get_global_rag_store() -> RagStore:
    return RagStore()
