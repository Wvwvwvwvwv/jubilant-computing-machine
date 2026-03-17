from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import books as books_router
from backend.core.services.retrieval_jobs import RetrievalJobState


def make_client(tmp_path, with_retrieval_jobs: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(books_router.router, prefix="/api/books")
    app.state.retrieval_job_state = RetrievalJobState() if with_retrieval_jobs else None
    books_router.BOOKS_DIR = tmp_path / "books"
    books_router.BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    return TestClient(app)


def test_upload_book_enqueues_retrieval_job_when_state_present(tmp_path):
    client = make_client(tmp_path, with_retrieval_jobs=True)

    response = client.post(
        "/api/books/upload",
        files={"file": ("notes.txt", b"hello retrieval", "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "uploaded"
    assert data["retrieval_job_id"].startswith("rj_")

    job = client.app.state.retrieval_job_state.get_job(data["retrieval_job_id"])
    assert job is not None
    assert job.source_type == "book"
    assert job.source_ref == data["id"]


def test_upload_book_without_retrieval_state_returns_null_job_id(tmp_path):
    client = make_client(tmp_path, with_retrieval_jobs=False)

    response = client.post(
        "/api/books/upload",
        files={"file": ("notes.txt", b"hello retrieval", "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "uploaded"
    assert data["retrieval_job_id"] is None
