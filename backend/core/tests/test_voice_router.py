from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import voice as voice_router
from backend.core.services.voice_state import VoiceState


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(voice_router.router, prefix="/api/voice")
    app.state.voice_state = VoiceState()
    return TestClient(app)


def test_voice_session_start_health_stop_flow():
    client = make_client()

    started = client.post(
        "/api/voice/session/start",
        json={"mode": "ptt", "stt_engine": "local_whisper_cpp", "tts_engine": "local_piper"},
    )
    assert started.status_code == 200
    sdata = started.json()
    assert sdata["status"] == "ready"
    voice_session_id = sdata["voice_session_id"]

    health = client.get(f"/api/voice/session/{voice_session_id}/health")
    assert health.status_code == 200
    hdata = health.json()
    assert hdata["status"] == "healthy"
    assert hdata["latency_p95_ms"] == 1700

    stopped = client.post(f"/api/voice/session/{voice_session_id}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"

    health_after = client.get(f"/api/voice/session/{voice_session_id}/health")
    assert health_after.status_code == 200
    assert health_after.json()["status"] == "stopped"


def test_voice_session_start_invalid_mode_returns_400():
    client = make_client()
    bad = client.post("/api/voice/session/start", json={"mode": "unknown"})
    assert bad.status_code == 400


def test_voice_session_missing_returns_404():
    client = make_client()
    response = client.get("/api/voice/session/vs_missing/health")
    assert response.status_code == 404
