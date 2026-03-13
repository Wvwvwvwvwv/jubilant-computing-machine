from backend.core.routers.chat import ChatMessage, serialize_messages


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
