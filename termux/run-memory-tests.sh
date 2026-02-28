#!/data/data/com.termux/files/usr/bin/bash
# Запуск memory-тестов в Termux

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FALLBACK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-${HOME}/roampal-android}"
TEST_FILE="backend/core/tests/test_memory_flow.py"

if [ ! -d "$PROJECT_ROOT" ] || [ ! -f "$PROJECT_ROOT/$TEST_FILE" ]; then
  PROJECT_ROOT="$FALLBACK_ROOT"
fi

if [ ! -f "$PROJECT_ROOT/$TEST_FILE" ]; then
  echo "❌ Не найден файл тестов: $TEST_FILE"
  echo "Проверьте PROJECT_ROOT или ветку"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "==== Memory tests runner ===="
echo "> project: $PROJECT_ROOT"

echo "> git sync"
if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
  git pull --ff-only || true
else
  git fetch --all --prune || true
fi

echo "> preflight: chat regression guards"
PYTHONPATH=backend/core python - <<'PY'
import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from routers.chat import chat, ChatRequest, ChatMessage, kobold


class DummyMemory:
    async def search(self, *_args, **_kwargs):
        return [{"id": "m1", "content": "ctx"}]

    async def add_interaction(self, **_kwargs):
        return "iid"


captured = {}


async def fake_generate(messages, max_tokens, temperature):
    captured["messages"] = messages
    return "ok"


kobold.generate = fake_generate
req_obj = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(memory_engine=DummyMemory())))
result = asyncio.run(chat(ChatRequest(messages=[ChatMessage(role="user", content="hi")], use_memory=True), req_obj))

assert result.interaction_id == "iid"
assert isinstance(captured["messages"][0], dict), "Chat messages must be serialized to dict before kobold.generate"

try:
    asyncio.run(chat(ChatRequest(messages=[], use_memory=False), req_obj))
except HTTPException as exc:
    assert exc.status_code == 400
else:
    raise AssertionError("Empty messages must return HTTP 400")

print("preflight ok")
PY

if ! python -m pytest --version >/dev/null 2>&1; then
  echo "⚠️ pytest не найден, устанавливаю через pip"
  python -m pip install pytest
fi

echo "> PYTHONPATH=backend/core python -m pytest -q $TEST_FILE"
PYTHONPATH=backend/core python -m pytest -q "$TEST_FILE"

echo "✅ Memory-тесты завершены"
