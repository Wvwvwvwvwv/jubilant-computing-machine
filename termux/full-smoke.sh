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

echo "[6/6] Tasks smoke (planner + policy + terminal)"
# Planner routing: python prefix should be reflected in task_started payload.
PLANNER_CREATE=$(curl -fsS -X POST "$CORE_URL/api/tasks/" \
  -H 'Content-Type: application/json' \
  -d '{"goal":"python: print(2+2)","max_attempts":2,"approval_required":false}')
PLANNER_ID=$(printf '%s' "$PLANNER_CREATE" | python -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')
PLANNER_RUN=$(curl -fsS -X POST "$CORE_URL/api/tasks/$PLANNER_ID/run")
printf '%s' "$PLANNER_RUN" | python -c 'import json,sys; data=json.load(sys.stdin); started=[e for e in data.get("events",[]) if e.get("kind")=="task_started"]; assert started, data; payload=started[-1].get("payload",{}); assert payload.get("language")=="python", payload; assert payload.get("tool")=="sandbox.execute", payload'

# Terminal rerun should emit task_skip.
PLANNER_RERUN=$(curl -fsS -X POST "$CORE_URL/api/tasks/$PLANNER_ID/run")
printf '%s' "$PLANNER_RERUN" | python -c 'import json,sys; data=json.load(sys.stdin); assert any(e.get("kind")=="task_skip" for e in data.get("events",[])), data'

# Approval-gated flow.
DANGER_CREATE=$(curl -fsS -X POST "$CORE_URL/api/tasks/" \
  -H 'Content-Type: application/json' \
  -d '{"goal":"rm -rf /tmp/demo","max_attempts":2,"approval_required":false}')
DANGER_ID=$(printf '%s' "$DANGER_CREATE" | python -c 'import json,sys; print(json.load(sys.stdin)["task_id"])')
DANGER_RUN=$(curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/run")
printf '%s' "$DANGER_RUN" | python -c 'import json,sys; data=json.load(sys.stdin); assert data.get("status") == "NEEDS_APPROVAL", data'

# Approve + drift should invalidate approval.
curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/approve" >/dev/null

python - <<PY
import sqlite3
from pathlib import Path
root = Path.home() / "roampal-android"
db = root / "backend" / "core" / "logs" / "tasks.db"
conn = sqlite3.connect(db)
conn.execute("update tasks set goal=? where task_id=?", ("rm -rf /tmp/demo_drifted", "$DANGER_ID"))
conn.commit()
print("drift injected for", "$DANGER_ID")
PY

DANGER_INVALIDATED=$(curl -fsS -X POST "$CORE_URL/api/tasks/$DANGER_ID/run")
printf '%s' "$DANGER_INVALIDATED" | python -c 'import json,sys; data=json.load(sys.stdin); assert data.get("status") == "NEEDS_APPROVAL", data; assert any(e.get("kind")=="task_approval_invalidated" for e in data.get("events",[])), data'

echo "✅ Full smoke completed successfully"
