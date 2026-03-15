from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import retrieval as retrieval_router


class FakeMemoryEngine:
    async def search(self, query: str, limit: int = 10):
        return [{"id": "legacy_1", "content": f"legacy:{query}", "score": 0.9}]


class FakeMultimodalRetriever:
    async def search(self, query: str, limit: int = 10):
        return [{"id": "mm_1", "content": f"mm:{query}", "score": 0.95}]


def make_client(multimodal_retriever=None) -> TestClient:
    app = FastAPI()
    app.include_router(retrieval_router.router, prefix="/api/retrieval")
    app.state.memory_engine = FakeMemoryEngine()
    app.state.multimodal_retriever = multimodal_retriever
    return TestClient(app)


def test_retrieval_health_reports_flag_and_injection(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "1")
    client = make_client(multimodal_retriever=FakeMultimodalRetriever())

    response = client.get("/api/retrieval/health")
    assert response.status_code == 200
    data = response.json()
    assert data["multimodal_flag"] is True
    assert data["multimodal_injected"] is True


def test_retrieval_search_uses_legacy_by_default(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "0")
    client = make_client(multimodal_retriever=FakeMultimodalRetriever())

    response = client.post("/api/retrieval/search", json={"query": "hello", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "legacy"
    assert data["count"] == 1
    assert data["results"][0]["id"] == "legacy_1"


def test_retrieval_search_uses_multimodal_when_enabled(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_RAG_ENABLED", "1")
    client = make_client(multimodal_retriever=FakeMultimodalRetriever())

    response = client.post("/api/retrieval/search", json={"query": "hello", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "multimodal"
    assert data["count"] == 1
    assert data["results"][0]["id"] == "mm_1"
