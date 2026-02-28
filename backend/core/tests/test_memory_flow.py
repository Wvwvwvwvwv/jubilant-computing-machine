from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from routers import books, chat
from services.memory_engine import MemoryEngine


def _new_client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(books, "BOOKS_DIR", tmp_path / "books")
    books.BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)
    engine = MemoryEngine()
    engine.chroma_available = False
    engine.collection = None
    app.state.memory_engine = engine
    return client, engine


def test_memory_crud_stats_and_search(tmp_path, monkeypatch):
    client, _ = _new_client(tmp_path, monkeypatch)

    add = client.post("/api/memory/add", json={"content": "Roampal memory testing", "metadata": {"source": "test"}})
    assert add.status_code == 200
    memory_id = add.json()["id"]

    search = client.post("/api/memory/search", json={"query": "memory", "limit": 5})
    assert search.status_code == 200
    body = search.json()
    assert body["count"] >= 1
    assert any(item["id"] == memory_id for item in body["results"])

    stats = client.get("/api/memory/stats")
    assert stats.status_code == 200
    assert stats.json()["backend"] == "in_memory"
    assert stats.json()["total_items"] >= 1

    delete = client.delete(f"/api/memory/{memory_id}")
    assert delete.status_code == 200


def test_books_upload_list_content_delete_and_memory_query(tmp_path, monkeypatch):
    client, _ = _new_client(tmp_path, monkeypatch)

    text = "Neural books are useful for memory retrieval in chat"
    files = {"file": ("book.txt", text.encode("utf-8"), "text/plain")}
    upload = client.post("/api/books/upload", files=files)
    assert upload.status_code == 200
    book_id = upload.json()["id"]

    listed = client.get("/api/books/list")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    content = client.get(f"/api/books/{book_id}/content")
    assert content.status_code == 200
    assert text in content.json()["content"]

    add_memory = client.post("/api/memory/add", json={"content": content.json()["content"], "metadata": {"book_id": book_id}})
    assert add_memory.status_code == 200

    search = client.post("/api/memory/search", json={"query": "retrieval chat", "limit": 3})
    assert search.status_code == 200
    assert search.json()["count"] >= 1

    deleted = client.delete(f"/api/books/{book_id}")
    assert deleted.status_code == 200


def test_chat_memory_context_feedback_and_interaction_cleanup(tmp_path, monkeypatch):
    client, engine = _new_client(tmp_path, monkeypatch)

    client.post("/api/memory/add", json={"content": "Context about Paris as capital", "metadata": {"type": "memory"}})

    async def fake_generate(messages, max_tokens, temperature):
        merged = "\n".join(f"{m.get('role')}:{m.get('content')}" for m in messages)
        assert "system:Релевантный контекст из памяти" in merged
        return "Paris is the capital of France"

    monkeypatch.setattr(chat.kobold, "generate", fake_generate)

    response = client.post(
        "/api/chat/",
        json={
            "messages": [{"role": "user", "content": "What is the capital?"}],
            "use_memory": True,
            "max_tokens": 64,
            "temperature": 0.2,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["context_items"] >= 1
    assert payload["interaction_id"]

    interaction_id = payload["interaction_id"]

    for _ in range(2):
        fb = client.post("/api/chat/feedback", params={"interaction_id": interaction_id, "helpful": False})
        assert fb.status_code == 200

    # After enough negative feedback interaction should be cleaned up
    assert interaction_id not in engine.in_memory_store


def test_chat_empty_messages_returns_400(tmp_path, monkeypatch):
    client, _ = _new_client(tmp_path, monkeypatch)

    response = client.post("/api/chat/", json={"messages": [], "use_memory": False})
    assert response.status_code == 400
    assert "messages must not be empty" in response.json()["detail"]
