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


def test_initiative_proposals_lifecycle_and_rate_limit(tmp_path):
    client = make_client(tmp_path)

    # tighten profile limit for deterministic rate-limit test
    patched = client.patch(
        "/api/companion/relationship-profile",
        json={"initiative_preferences": {"max_unsolicited_per_hour": 1}},
    )
    assert patched.status_code == 200

    first = client.post(
        "/api/companion/proposals",
        json={
            "text": "Предлагаю ввести ежедневный health-check",
            "reason": "Снизит риск незаметной деградации",
            "expected_value": "Быстрее обнаружим сбои",
            "risk_level": "low",
            "stop_condition": "Если 7 дней подряд без инцидентов",
            "unsolicited": True,
        },
    )
    assert first.status_code == 200
    proposal_id = first.json()["proposal_id"]

    second = client.post(
        "/api/companion/proposals",
        json={
            "text": "Второе unsolicited-предложение",
            "reason": "Проверка лимита",
            "expected_value": "Должно заблокироваться",
            "risk_level": "low",
            "stop_condition": "Немедленно",
            "unsolicited": True,
        },
    )
    assert second.status_code == 400
    assert "rate limit" in second.json()["detail"]

    listed = client.get("/api/companion/proposals", params={"status": "open", "limit": 10})
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    accepted = client.post(f"/api/companion/proposals/{proposal_id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    dismissed = client.post(f"/api/companion/proposals/{proposal_id}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"


    events = client.get(f'/api/companion/proposals/{proposal_id}/events', params={'limit': 10})
    assert events.status_code == 200
    edata = events.json()
    assert edata['count'] >= 3
    kinds = [x['event_kind'] for x in edata['items']]
    assert 'created' in kinds
    assert 'status_accepted' in kinds
    assert 'status_dismissed' in kinds


def test_suggest_proposal_respects_initiative_mode_and_creates_item(tmp_path):
    client = make_client(tmp_path)

    # off mode must block suggestion
    blocked = client.patch('/api/companion/session', json={'initiative_mode': 'off'})
    assert blocked.status_code == 200

    denied = client.post(
        '/api/companion/proposals/suggest',
        json={'topic': 'план миграции схемы', 'context': 'prod schema update'},
    )
    assert denied.status_code == 400
    assert 'initiative mode is off' in denied.json()['detail']

    # proactive mode should generate unsolicited proposal
    enabled = client.patch('/api/companion/session', json={'initiative_mode': 'proactive', 'challenge_mode': 'strict'})
    assert enabled.status_code == 200

    suggested = client.post(
        '/api/companion/proposals/suggest',
        json={'topic': 'план миграции схемы', 'context': 'prod schema update'},
    )
    assert suggested.status_code == 200
    pdata = suggested.json()
    assert pdata['unsolicited'] is True
    assert pdata['risk_level'] in {'medium', 'high'}

    listed = client.get('/api/companion/proposals', params={'status': 'open', 'limit': 10})
    assert listed.status_code == 200
    assert listed.json()['count'] >= 1


def test_proposal_events_not_found_returns_404(tmp_path):
    client = make_client(tmp_path)
    response = client.get('/api/companion/proposals/pr_missing/events')
    assert response.status_code == 404


def test_response_traces_history_endpoint(tmp_path):
    client = make_client(tmp_path)

    # seed traces directly through state service
    app = client.app
    app.state.companion_state.update_session(reasoning_mode="stable", challenge_mode="balanced")
    app.state.companion_state.set_last_trace(
        response_id="resp_1",
        relationship_used=["rf_1"],
        uncertainty_markers=["insufficient_data"],
        counter_position_used=True,
        confidence=0.7,
    )
    app.state.companion_state.update_session(reasoning_mode="wild", challenge_mode="strict")
    app.state.companion_state.set_last_trace(
        response_id="resp_2",
        relationship_used=["rf_2"],
        uncertainty_markers=["hypothesis_present"],
        counter_position_used=True,
        confidence=0.6,
    )

    last = client.get('/api/companion/last-response-trace')
    assert last.status_code == 200
    assert last.json()['response_id'] == 'resp_2'
    assert last.json()['retrieval_backend'] == 'legacy'

    history = client.get('/api/companion/response-traces', params={'limit': 10})
    assert history.status_code == 200
    data = history.json()
    assert data['count'] == 2
    assert data['items'][0]['response_id'] == 'resp_1'
    assert data['items'][1]['response_id'] == 'resp_2'
    assert data['items'][0]['retrieval_backend'] == 'legacy'
    assert data['items'][1]['retrieval_backend'] == 'legacy'
