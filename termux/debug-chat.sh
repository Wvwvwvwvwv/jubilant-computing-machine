#!/data/data/com.termux/files/usr/bin/bash
# Быстрая отладка чата на телефоне (Core + Kobold + запрос /api/chat)

set -u
PROJECT_ROOT="${HOME}/roampal-android"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "❌ Не найден проект: $PROJECT_ROOT"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "==== Versions ===="
python --version || true
node --version || true

echo

echo "==== Health ===="
echo "> core /health"
curl -sS -m 6 http://127.0.0.1:8000/health || true
echo
echo "> kobold /api/v1/model"
curl -sS -m 6 http://127.0.0.1:5001/api/v1/model || true
echo

echo

echo "==== Chat API check (no-memory) ===="
CHAT_PAYLOAD='{"messages":[{"role":"user","content":"Привет! Ответь одним словом"}],"use_memory":false,"max_tokens":64,"temperature":0.2}'

echo "> POST /api/chat/"
curl -i -sS -m 20 \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/chat/ \
  -d "$CHAT_PAYLOAD"
echo

echo

echo "==== Last core logs ===="
tail -n 120 "$PROJECT_ROOT/logs/core.log" 2>/dev/null || true

echo

echo "==== Last kobold logs ===="
tail -n 120 "$PROJECT_ROOT/logs/koboldcpp.log" 2>/dev/null || true
