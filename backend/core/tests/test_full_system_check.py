from fastapi.testclient import TestClient

from backend.core.main import app


def test_full_system_check_smoke_flow():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        chat = client.post(
            "/api/chat/",
            json={
                "messages": [{"role": "user", "content": "Привет"}],
                "use_memory": False,
                "max_tokens": 32,
                "temperature": 0.2,
            },
        )
        assert chat.status_code in {200, 500, 503}

        retrieval_health = client.get("/api/retrieval/health")
        assert retrieval_health.status_code == 200

        index_job = client.post(
            "/api/retrieval/index",
            json={"source_type": "manual", "source_ref": "smoke", "process_now": False},
        )
        assert index_job.status_code == 200

        worker_metrics = client.get("/api/retrieval/worker-metrics")
        assert worker_metrics.status_code == 200

        voice_start = client.post(
            "/api/voice/session/start",
            json={"mode": "ptt", "tts_engine": "local_piper_female"},
        )
        assert voice_start.status_code == 200
