from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import retrieval as retrieval_router
from backend.core.services.retrieval_jobs import RetrievalJobState


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
    app.state.retrieval_job_state = RetrievalJobState()
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


def test_index_job_lifecycle_create_get_list():
    client = make_client()

    created = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "book_123", "process_now": True},
    )
    assert created.status_code == 200
    cdata = created.json()
    assert cdata["job_id"].startswith("rj_")
    assert cdata["status"] == "completed"
    assert cdata["attempts"] == 1

    fetched = client.get(f"/api/retrieval/jobs/{cdata['job_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["source_ref"] == "book_123"

    listed = client.get("/api/retrieval/jobs", params={"limit": 10, "status": "completed"})
    assert listed.status_code == 200
    ldata = listed.json()
    assert ldata["count"] == 1
    assert ldata["items"][0]["job_id"] == cdata["job_id"]


def test_index_job_process_now_false_returns_queued():
    client = make_client()

    created = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "book_queued", "process_now": False},
    )
    assert created.status_code == 200
    cdata = created.json()
    assert cdata["status"] == "queued"
    assert cdata["attempts"] == 0



def test_process_index_job_endpoint_transitions_to_completed():
    client = make_client()

    created = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "book_manual", "process_now": False},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    processed = client.post(f"/api/retrieval/jobs/{job_id}/process", json={})
    assert processed.status_code == 200
    pdata = processed.json()
    assert pdata["status"] == "completed"
    assert pdata["attempts"] == 1


def test_process_index_job_endpoint_can_mark_failed():
    client = make_client()

    created = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "book_fail", "process_now": False},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    processed = client.post(f"/api/retrieval/jobs/{job_id}/process", json={"fail_reason": "parse error"})
    assert processed.status_code == 200
    pdata = processed.json()
    assert pdata["status"] == "failed"
    assert pdata["error"] == "parse error"


def test_get_index_job_returns_404_for_unknown_id():
    client = make_client()
    response = client.get("/api/retrieval/jobs/rj_missing")
    assert response.status_code == 404
    assert "index job not found" in response.json()["detail"]


def test_process_index_job_returns_404_for_unknown_id():
    client = make_client()
    response = client.post("/api/retrieval/jobs/rj_missing/process", json={})
    assert response.status_code == 404


def test_worker_metrics_endpoint_returns_counters():
    client = make_client()

    created_ok = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "m_ok", "process_now": True},
    )
    assert created_ok.status_code == 200

    created_fail = client.post(
        "/api/retrieval/index",
        json={"source_type": "book", "source_ref": "m_fail", "process_now": False},
    )
    assert created_fail.status_code == 200
    job_id = created_fail.json()["job_id"]

    failed = client.post(f"/api/retrieval/jobs/{job_id}/process", json={"fail_reason": "boom"})
    assert failed.status_code == 200

    metrics = client.get("/api/retrieval/worker-metrics")
    assert metrics.status_code == 200
    data = metrics.json()
    assert data["processed_total"] >= 2
    assert data["failed_total"] >= 1
    assert data["completed"] >= 1
    assert data["failed"] >= 1
