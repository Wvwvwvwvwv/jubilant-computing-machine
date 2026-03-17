from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import online as online_router


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(online_router.router, prefix="/api/online")
    return TestClient(app)


def test_online_health_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_ONLINE_TOOLS", raising=False)
    client = make_client()
    response = client.get("/api/online/health")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_online_search_returns_403_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_ONLINE_TOOLS", "0")
    client = make_client()
    response = client.post("/api/online/search", json={"query": "test"})
    assert response.status_code == 403


def test_online_search_works_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_ONLINE_TOOLS", "1")

    async def fake_search(query: str, limit: int = 5):
        return [{"title": "T", "snippet": f"S:{query}", "url": "https://example.com"}]

    monkeypatch.setattr(online_router, "web_search", fake_search)
    client = make_client()
    response = client.post("/api/online/search", json={"query": "python", "limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["results"][0]["snippet"] == "S:python"


def test_online_download_works_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_ONLINE_TOOLS", "1")

    async def fake_download(url: str, filename: str | None = None):
        return {"path": "/tmp/tool.sh", "filename": filename or "tool.sh", "size_bytes": 123}

    monkeypatch.setattr(online_router, "download_to_local", fake_download)
    client = make_client()
    response = client.post("/api/online/download", json={"url": "https://example.com/tool.sh", "filename": "tool.sh"})
    assert response.status_code == 200
    assert response.json()["size_bytes"] == 123
