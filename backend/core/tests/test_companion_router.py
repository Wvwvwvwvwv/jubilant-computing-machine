from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import companion as companion_router
from backend.core.services.companion_memory import CompanionMemory
from backend.core.services.companion_state import CompanionState


def make_client(tmp_path) -> TestClient:
    app = FastAPI()
    app.include_router(companion_router.router, prefix="/api/companion")
    app.state.companion_state = CompanionState()
    memory = CompanionMemory()
    memory.db_path = tmp_path / "companion.db"
    memory._init_db()
    memory._ensure_default_profile()
    app.state.companion_memory = memory
    return TestClient(app)


def test_companion_session_default_shape(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/companion/session")
    assert response.status_code == 200
    data = response.json()
    assert data["reasoning_mode"] == "stable"
    assert data["challenge_mode"] == "balanced"
    assert data["initiative_mode"] == "adaptive"
    assert data["voice_mode"] == "off"


def test_companion_session_patch_updates_modes(tmp_path):
    client = make_client(tmp_path)

    response = client.patch(
        "/api/companion/session",
        json={
            "reasoning_mode": "wild",
            "challenge_mode": "strict",
            "initiative_mode": "proactive",
            "voice_mode": "ptt",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reasoning_mode"] == "wild"
    assert data["challenge_mode"] == "strict"
    assert data["initiative_mode"] == "proactive"
    assert data["voice_mode"] == "ptt"


def test_last_response_trace_is_none_by_default(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/companion/last-response-trace")
    assert response.status_code == 200
    assert response.json() is None


def test_relationship_profile_patch_and_facts_lifecycle(tmp_path):
    client = make_client(tmp_path)

    profile = client.get("/api/companion/relationship-profile")
    assert profile.status_code == 200
    assert profile.json()["style"]["verbosity"] == "medium"

    patched = client.patch(
        "/api/companion/relationship-profile",
        json={"style": {"verbosity": "high"}, "debate_preferences": {"strictness": "strict"}},
    )
    assert patched.status_code == 200
    pdata = patched.json()
    assert pdata["style"]["verbosity"] == "high"
    assert pdata["debate_preferences"]["strictness"] == "strict"

    created = client.post(
        "/api/companion/relationship-facts",
        json={
            "fact": "Пользователь любит сначала риски",
            "source": {"type": "chat_message", "ref_id": "msg_1"},
            "confidence": 0.8,
            "ttl_days": 90,
        },
    )
    assert created.status_code == 200
    fact = created.json()
    assert fact["status"] == "active"

    listed = client.get("/api/companion/relationship-facts", params={"query": "риски", "limit": 10})
    assert listed.status_code == 200
    ldata = listed.json()
    assert ldata["count"] == 1
    fact_id = ldata["items"][0]["fact_id"]

    invalidated = client.post(f"/api/companion/relationship-facts/{fact_id}/invalidate")
    assert invalidated.status_code == 200
    assert invalidated.json()["status"] == "invalidated"

    listed_after = client.get("/api/companion/relationship-facts", params={"query": "риски", "limit": 10})
    assert listed_after.status_code == 200
    assert listed_after.json()["count"] == 0
