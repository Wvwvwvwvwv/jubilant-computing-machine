from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.routers import chat as chat_router
from backend.core.routers.chat import (
    ChatMessage,
    build_memory_context_block,
    build_memory_context_items,
    build_companion_behavior_message,
    build_relationship_memory_message,
    _insertion_index_before_last_user,
    _online_search_triggered,
    build_online_context,
    serialize_messages,
    trim_chat_history,
)
from backend.core.services.companion_state import CompanionState
from backend.core.services.task_runner import TaskRunner


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


def test_build_memory_context_items_returns_countable_filtered_list():
    items = build_memory_context_items(
        [
            {"content": "Q: Привет"},
            {"content": "Q: Привет"},
            {"content": "System: Answer to previous"},
            {"content": "Факт 2"},
        ],
        limit=3,
    )
    assert items == ["Q: Привет", "Факт 2"]


def test_insertion_index_before_last_user_finds_latest_user_turn():
    messages = [
        ChatMessage(role="system", content="s"),
        ChatMessage(role="assistant", content="a1"),
        ChatMessage(role="user", content="u1"),
        ChatMessage(role="assistant", content="a2"),
    ]
    assert _insertion_index_before_last_user(messages) == 2


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
    assert trace.retrieval_backend == "legacy"
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


def test_online_search_triggered_prefixes():
    assert _online_search_triggered("web: latest ai news") is True
    assert _online_search_triggered("search: python httpx") is True
    assert _online_search_triggered("привет") is False


def test_build_online_context_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_ONLINE_TOOLS", "0")

    async def fake_web_search(query: str, limit: int = 3):
        return [{"title": "t", "snippet": "s", "url": "u"}]

    monkeypatch.setattr(chat_router, "web_search", fake_web_search)

    import asyncio
    result = asyncio.run(build_online_context("web: test"))
    assert result == ""


def test_build_online_context_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_ONLINE_TOOLS", "1")

    async def fake_web_search(query: str, limit: int = 3):
        assert query == "weather moscow"
        return [{"title": "Result", "snippet": "Now", "url": "https://example.com"}]

    monkeypatch.setattr(chat_router, "web_search", fake_web_search)

    import asyncio
    result = asyncio.run(build_online_context("web: weather moscow"))
    assert "Result" in result
    assert "https://example.com" in result


def test_chat_autonomy_auto_mode_executes_actionable_query(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.state.memory_engine = FakeMemoryEngine()
    app.state.companion_state = CompanionState()
    app.state.companion_memory = FakeCompanionMemory()
    app.state.task_runner = TaskRunner()

    async def fake_generate(messages, max_tokens=512, temperature=0.7):
        return "Готово"

    async def fake_execute(request):
        class Result:
            exit_code = 0
            stdout = "installed"
            stderr = ""

        return Result()

    async def fake_plan(goal: str):
        class Plan:
            tool = "sandbox.execute"
            language = "bash"
            code = "echo installed"
            timeout = 30

        return Plan()

    monkeypatch.setattr(chat_router.kobold, "generate", fake_generate)
    monkeypatch.setattr(chat_router, "execute_code", fake_execute)
    monkeypatch.setattr(chat_router.task_planner, "build_plan", fake_plan)

    client = TestClient(app)
    response = client.post(
        "/api/chat/",
        json={"messages": [{"role": "user", "content": "Установи python 3.13"}], "use_memory": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["autonomous"]["triggered"] is True
    assert body["autonomous"]["status"] == "SUCCESS"
    assert body["autonomous"]["stdout"] == "installed"


def test_chat_autonomy_can_be_disabled_per_request(monkeypatch):
    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.state.memory_engine = FakeMemoryEngine()
    app.state.companion_state = CompanionState()
    app.state.companion_memory = FakeCompanionMemory()
    app.state.task_runner = TaskRunner()

    async def fake_generate(messages, max_tokens=512, temperature=0.7):
        return "Только текст"

    async def fake_execute(request):
        raise AssertionError("must not execute when autonomous_mode=off")

    monkeypatch.setattr(chat_router.kobold, "generate", fake_generate)
    monkeypatch.setattr(chat_router, "execute_code", fake_execute)

    client = TestClient(app)
    response = client.post(
        "/api/chat/",
        json={
            "messages": [{"role": "user", "content": "Установи python 3.13"}],
            "use_memory": False,
            "autonomous_mode": "off",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body.get("autonomous") is None
