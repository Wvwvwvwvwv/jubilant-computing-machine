#!/data/data/com.termux/files/usr/bin/bash
# Полный smoke-прогон сервисов Roampal Android

set -euo pipefail

PROJECT_ROOT="$HOME/roampal-android"
CORE_URL="http://127.0.0.1:8000"
EMBED_URL="http://127.0.0.1:8001"
KOBOLD_URL="http://127.0.0.1:5001"
FRONT_URL="http://127.0.0.1:5173"

cd "$PROJECT_ROOT"

echo "===== Roampal full smoke ====="

echo "[1/6] Restart services"
bash termux/stop-services.sh || true
bash termux/start-services.sh

echo "[2/6] Health checks"
curl -fsS "$CORE_URL/health" >/dev/null
curl -fsS "$EMBED_URL/health" >/dev/null
curl -fsS "$KOBOLD_URL/api/v1/model" >/dev/null
curl -fsS "$FRONT_URL" >/dev/null

echo "[3/6] Chat smoke"
CHAT_RESP=$(curl -fsS -X POST "$CORE_URL/api/chat/" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Ответь одним словом: ok"}],"use_memory":false,"max_tokens":32,"temperature":0.1}')
printf '%s' "$CHAT_RESP" | python -c 'import json,sys; data=json.load(sys.stdin); assert "response" in data, data'

echo "[4/6] Memory smoke"
MEM_ADD=$(curl -fsS -X POST "$CORE_URL/api/memory/add" \
  -H 'Content-Type: application/json' \
  -d '{"content":"smoke memory item","metadata":{"type":"memory","source":"full-smoke"}}')
MEM_ID=$(printf '%s' "$MEM_ADD" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
[ -n "$MEM_ID" ]
curl -fsS -X POST "$CORE_URL/api/memory/search" \
  -H 'Content-Type: application/json' \
  -d '{"query":"smoke memory","limit":5}' >/dev/null

echo "[5/6] Sandbox smoke"
curl -fsS -X POST "$CORE_URL/api/sandbox/execute" \
  -H 'Content-Type: application/json' \
  -d '{"code":"echo sandbox_ok","language":"bash","timeout":10}' \
  | python -c 'import json,sys; data=json.load(sys.stdin); assert data.get("exit_code")==0, data'

echo "[6/6] Tasks smoke"
SAFE_CREATE=$(curl -fsS -X POST "$CORE_URL/api/tasks/" \
  -H 'Content-Type: application/json' \
  -d '{"goal":"echo tasks_ok","max_attempts":2,"approval_required":false}')
SAFE_ID=$(printf '%s' "$SAFE_CREATE" | python -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')
SAFE_RUN=$(curl -fsS -X POST "$CORE_URL/api/tasks/$SAFE_ID/run")
printf '%s' "$SAFE_RUN" | python -c 'import json,sys; data=json.load(sys.stdin); assert data.get("status") in {"SUCCESS","RETRYING","FAILED","NEEDS_APPROVAL"}, data'

DANGER_CREATE=$(curl -fsS -X POST "$CORE_URL/api/tasks/" \
  -H 'Content-Type: application/json' \
  -d '{"goal":"rm -rf /tmp/demo","max_attempts":2,"approval_required":false}')
DANGER_ID=$(printf '%s' "$DANGER_CREATE" | python -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')
DANGER_RUN=$(curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/run")
printf '%s' "$DANGER_RUN" | python -c 'import json,sys; data=json.load(sys.stdin); assert data.get("status") == "NEEDS_APPROVAL", data'

curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/approve" >/dev/null
curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/run" >/dev/null

echo "✅ Full smoke completed successfully"
