from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import companion as companion_router
from backend.core.services.companion_state import CompanionState


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(companion_router.router, prefix="/api/companion")
    app.state.companion_state = CompanionState()
    return TestClient(app)


def test_companion_session_default_shape():
    client = make_client()

    response = client.get("/api/companion/session")
    assert response.status_code == 200
    data = response.json()
    assert data["reasoning_mode"] == "stable"
    assert data["challenge_mode"] == "balanced"
    assert data["initiative_mode"] == "adaptive"
    assert data["voice_mode"] == "off"


def test_companion_session_patch_updates_modes():
    client = make_client()

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


def test_last_response_trace_is_none_by_default():
    client = make_client()

    response = client.get("/api/companion/last-response-trace")
    assert response.status_code == 200
    assert response.json() is None
