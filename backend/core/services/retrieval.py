import os
from typing import Any

from backend.core.services.memory_engine import MemoryEngine


TRUE_VALUES = {"1", "true", "yes", "on"}


class LegacyMemoryRetriever:
    """Adapter over MemoryEngine for week-1 retrieval abstraction."""

    def __init__(self, memory_engine: MemoryEngine):
        self._memory_engine = memory_engine

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self._memory_engine.search(query, limit=limit)


class NullMultimodalRetriever:
    """Placeholder multimodal retriever until RAG pipeline is wired."""

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return []


def multimodal_rag_enabled() -> bool:
    raw = os.getenv("MULTIMODAL_RAG_ENABLED", "0")
    return raw.strip().lower() in TRUE_VALUES


async def search_with_backend(
    memory_engine: MemoryEngine,
    query_text: str,
    limit: int = 10,
    multimodal_retriever: Any = None,
) -> tuple[list[dict[str, Any]], str]:
    """Resolve active retrieval backend and execute search."""

    if multimodal_rag_enabled() and multimodal_retriever is not None and hasattr(multimodal_retriever, "search"):
        return await multimodal_retriever.search(query_text, limit=limit), "multimodal"

    legacy_retriever = LegacyMemoryRetriever(memory_engine)
    return await legacy_retriever.search(query_text, limit=limit), "legacy"
