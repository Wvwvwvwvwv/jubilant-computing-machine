import asyncio
from types import SimpleNamespace

from backend.core.routers.chat import search_memory_context
from backend.core.services.retrieval import LegacyMemoryRetriever, multimodal_rag_enabled, search_with_backend


class FakeMemoryEngine:
    async def search(self, query: str, limit: int = 10):
        return [{"id": "legacy_1", "content": f"legacy:{query}", "score": 0.9}]


class FakeMultimodalRetriever:
    async def search(self, query: str, limit: int = 10):
        return [{"id": "mm_1", "content": f"mm:{query}", "score": 0.95}]


def test_multimodal_rag_enabled_env(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "1")
    assert multimodal_rag_enabled() is True

    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "true")
    assert multimodal_rag_enabled() is True

    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "0")
    assert multimodal_rag_enabled() is False


def test_legacy_memory_retriever_calls_memory_engine():
    retriever = LegacyMemoryRetriever(FakeMemoryEngine())
    result = asyncio.run(retriever.search("hello", limit=3))
    assert result[0]["content"] == "legacy:hello"


def test_search_memory_context_uses_legacy_when_flag_off(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "0")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(multimodal_retriever=FakeMultimodalRetriever())))

    result, backend = asyncio.run(search_memory_context(req, FakeMemoryEngine(), "plan", limit=5))

    assert backend == "legacy"
    assert result[0]["id"] == "legacy_1"


def test_search_memory_context_uses_multimodal_when_flag_on(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "1")
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(multimodal_retriever=FakeMultimodalRetriever())))

    result, backend = asyncio.run(search_memory_context(req, FakeMemoryEngine(), "plan", limit=5))

    assert backend == "multimodal"
    assert result[0]["id"] == "mm_1"


def test_search_with_backend_fallbacks_to_legacy_when_mm_missing(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "1")
    result, backend = asyncio.run(search_with_backend(FakeMemoryEngine(), "plan", limit=5, multimodal_retriever=None))
    assert backend == "legacy"
    assert result[0]["id"] == "legacy_1"
