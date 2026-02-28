#!/data/data/com.termux/files/usr/bin/bash
# Полный прогон: сервисы + чат + память + логи

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FALLBACK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-${HOME}/roampal-android}"
LOG_DIR="$PROJECT_ROOT/logs"

if [ ! -d "$PROJECT_ROOT" ] || [ ! -d "$PROJECT_ROOT/termux" ]; then
  PROJECT_ROOT="$FALLBACK_ROOT"
  LOG_DIR="$PROJECT_ROOT/logs"
fi

if [ ! -d "$PROJECT_ROOT/termux" ]; then
  echo "❌ Не найден каталог termux в PROJECT_ROOT: $PROJECT_ROOT"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "==== Full smoke ===="
echo "> project: $PROJECT_ROOT"
echo "> chmod +x termux/*.sh"
chmod +x termux/*.sh

echo "> stop-services (best effort)"
bash termux/stop-services.sh || true

echo "> start-services"
bash termux/start-services.sh

echo
echo "==== Health checks ===="
echo "> core"
curl -fsS -m 12 http://127.0.0.1:8000/health
echo
echo "> embeddings"
curl -fsS -m 12 http://127.0.0.1:8001/health
echo
echo "> kobold"
curl -fsS -m 12 http://127.0.0.1:5001/api/v1/model
echo
echo "> frontend"
curl -fsS -m 12 http://127.0.0.1:5173 >/dev/null

echo
echo "==== Chat API checks ===="
echo "> no-memory"
curl -i -sS -m 30 \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/chat/ \
  -d '{"messages":[{"role":"user","content":"Привет, ответь одним словом"}],"use_memory":false,"max_tokens":64,"temperature":0.2}'

echo
echo "> with-memory"
curl -i -sS -m 30 \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:8000/api/chat/ \
  -d '{"messages":[{"role":"user","content":"Запомни: столица Франции Париж"}],"use_memory":true,"max_tokens":64,"temperature":0.2}'

echo
echo "==== Memory tests ===="
bash termux/run-memory-tests.sh

echo
echo "==== Diagnostics + logs ===="
bash termux/diagnose.sh || true

echo
echo "> tail core"
tail -n 120 "$LOG_DIR/core.log" 2>/dev/null || true
echo "> tail embeddings"
tail -n 120 "$LOG_DIR/embeddings.log" 2>/dev/null || true
echo "> tail kobold"
tail -n 120 "$LOG_DIR/koboldcpp.log" 2>/dev/null || true
echo "> tail frontend"
tail -n 120 "$LOG_DIR/frontend.log" 2>/dev/null || true

echo
echo "✅ Full smoke completed"
