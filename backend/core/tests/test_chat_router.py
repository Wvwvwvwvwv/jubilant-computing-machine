from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import chat as chat_router
from backend.core.routers.chat import (
    ChatMessage,
    build_memory_context_block,
    build_companion_behavior_message,
    build_relationship_memory_message,
    serialize_messages,
    trim_chat_history,
)
from backend.core.services.companion_state import CompanionState


class FakeMemoryEngine:
    async def search(self, query: str, limit: int = 5):
        return []

    async def add_interaction(self, query: str, response: str, context_used):
        return "interaction_1"

    async def record_outcome(self, interaction_id: str, helpful: bool):
        return None


class FakeCompanionMemory:
    def list_facts(self, query: str = "", limit: int = 20):
        return [
            type("Fact", (), {"fact_id": "rf_1", "fact": "Пользователь любит сначала риски"})(),
            type("Fact", (), {"fact_id": "rf_2", "fact": "Предпочитает краткие выводы"})(),
        ]


def test_serialize_messages_with_pydantic_v2_models():
    msgs = [ChatMessage(role="user", content="hello")]
    data = serialize_messages(msgs)
    assert data == [{"role": "user", "content": "hello"}]


def test_serialize_messages_with_pydantic_v1_like_objects():
    class LegacyMsg:
        def __init__(self, role: str, content: str):
            self.role = role
            self.content = content

        def dict(self):
            return {"role": self.role, "content": self.content}

    msgs = [LegacyMsg(role="assistant", content="ok")]
    data = serialize_messages(msgs)  # type: ignore[arg-type]
    assert data == [{"role": "assistant", "content": "ok"}]


def test_build_companion_behavior_message_reflects_modes():
    state = CompanionState()
    stable_msg = build_companion_behavior_message(state.get_session())
    assert "Режим STABLE" in stable_msg.content

    state.update_session(reasoning_mode="wild", challenge_mode="strict")
    wild_msg = build_companion_behavior_message(state.get_session())
    assert "Режим WILD" in wild_msg.content
    assert "контрпозицию" in wild_msg.content


def test_build_relationship_memory_message_contains_fact_ids():
    msg = build_relationship_memory_message(
        [
            {"fact_id": "rf_1", "fact": "A"},
            {"fact_id": "rf_2", "fact": "B"},
        ]
    )
    assert "[Fact rf_1]" in msg.content
    assert "[Fact rf_2]" in msg.content


def test_build_memory_context_block_deduplicates_and_filters_noise():
    block = build_memory_context_block(
        [
            {"content": "smoke memory item"},
            {"content": "Q: Расскажи о себе"},
            {"content": "Q:   Расскажи   о   себе"},
            {"content": "System: Answer to previous"},
            {"content": "Полезный факт"},
        ],
        limit=3,
    )
    assert "smoke memory item" not in block
    assert "System: Answer to" not in block
    assert block.count("Расскажи о себе") == 1
    assert "Полезный факт" in block


def test_trim_chat_history_preserves_system_and_keeps_recent_non_system():
    messages = [ChatMessage(role="system", content="policy")] + [
        ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(20)
    ]
    trimmed = trim_chat_history(messages, max_messages=6)
    assert trimmed[0].role == "system"
    non_system = [m for m in trimmed if m.role != "system"]
    assert len(non_system) == 6
    assert non_system[-1].content == "m19"


def test_chat_endpoint_writes_trace_and_injects_policy_and_relationship(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.state.memory_engine = FakeMemoryEngine()
    app.state.companion_state = CompanionState()
    app.state.companion_state.update_session(reasoning_mode="wild", challenge_mode="balanced")
    app.state.companion_memory = FakeCompanionMemory()

    captured = {}

    async def fake_generate(messages, max_tokens=512, temperature=0.7):
        captured["messages"] = messages
        return "Возможно это гипотеза, недостаточно данных для уверенности."

    monkeypatch.setattr(chat_router.kobold, "generate", fake_generate)

    client = TestClient(app)
    response = client.post(
        "/api/chat/",
        json={
            "messages": [{"role": "user", "content": "Сделай анализ"}],
            "use_memory": False,
            "max_tokens": 64,
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    assert response.json()["memory_used"] is False

    # companion policy should be injected as first system message
    first_msg = captured["messages"][0]
    assert first_msg["role"] == "system"
    assert "Политика поведения companion" in first_msg["content"]

    # relationship memory message should be injected next
    second_msg = captured["messages"][1]
    assert second_msg["role"] == "system"
    assert "Память отношений" in second_msg["content"]
    assert "rf_1" in second_msg["content"]

    trace = app.state.companion_state.get_last_trace()
    assert trace is not None
    assert trace.reasoning_mode == "wild"
    assert trace.challenge_mode == "balanced"
    assert "insufficient_data" in trace.uncertainty_markers
    assert trace.counter_position_used is True
    assert trace.relationship_used == ["rf_1", "rf_2"]


def test_chat_endpoint_works_without_trailing_slash(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.state.memory_engine = FakeMemoryEngine()
    app.state.companion_state = CompanionState()
    app.state.companion_memory = FakeCompanionMemory()

    async def fake_generate(messages, max_tokens=512, temperature=0.7):
        return "ok"

    monkeypatch.setattr(chat_router.kobold, "generate", fake_generate)

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "ping"}], "use_memory": False},
        follow_redirects=False,
    )
    assert response.status_code == 200
