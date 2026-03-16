#!/usr/bin/env bash
set -euo pipefail

# Verify Roampal model stack stays local-only by checking service health
# and active network sockets while triggering a chat request.

HOST_CORE="${HOST_CORE:-http://127.0.0.1:8000}"
HOST_EMBEDDINGS="${HOST_EMBEDDINGS:-http://127.0.0.1:8001}"
HOST_KOBOLD="${HOST_KOBOLD:-http://127.0.0.1:5001}"
CHAT_PROMPT="${CHAT_PROMPT:-Привет}"
TIMEOUT_S="${TIMEOUT_S:-45}"
OUT_DIR="${OUT_DIR:-logs}"
STRICT="${STRICT:-0}"

mkdir -p "$OUT_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
SOCKET_LOG="$OUT_DIR/net-sockets-$TS.log"
REPORT_JSON="$OUT_DIR/net-leak-report-$TS.json"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[error] required command missing: $1" >&2
    exit 127
  fi
}

need_cmd curl
need_cmd python

check_endpoint() {
  local name="$1"
  local url="$2"
  if curl -fsS --max-time 5 "$url" >/dev/null; then
    echo "[ok] $name endpoint reachable: $url"
  else
    echo "[warn] $name endpoint is not reachable: $url"
  fi
}

echo "[step] endpoint preflight"
check_endpoint "core" "$HOST_CORE/health"
check_endpoint "embeddings" "$HOST_EMBEDDINGS/health"
check_endpoint "kobold" "$HOST_KOBOLD/api/v1/model"

echo "[step] trigger chat request and capture sockets"
CHAT_PAYLOAD=$(python - <<'PY'
import json, os
prompt = os.environ.get("CHAT_PROMPT", "Привет")
print(json.dumps({
    "messages": [{"role": "user", "content": prompt}],
    "use_memory": False,
    "max_tokens": 96,
    "temperature": 0.2,
}, ensure_ascii=False))
PY
)

( timeout "$TIMEOUT_S" curl -sS -X POST "$HOST_CORE/api/chat/" \
    -H 'Content-Type: application/json' \
    -d "$CHAT_PAYLOAD" >/dev/null ) &
REQ_PID=$!

# Give request a short head start and sample sockets.
sleep 1
SOCKET_TOOL=""
if command -v ss >/dev/null 2>&1; then
  SOCKET_TOOL="ss"
  ss -tpn > "$SOCKET_LOG" || true
elif command -v netstat >/dev/null 2>&1; then
  SOCKET_TOOL="netstat"
  netstat -tnp > "$SOCKET_LOG" || true
else
  SOCKET_TOOL="none"
  echo "[warn] neither ss nor netstat is available; writing empty socket snapshot"
  : > "$SOCKET_LOG"
fi
wait "$REQ_PID" || true

echo "[step] analyze socket snapshot"
python - "$SOCKET_LOG" "$REPORT_JSON" "$SOCKET_TOOL" <<'PY'
import json
import re
import sys
from pathlib import Path

socket_log = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore').splitlines()
report_file = Path(sys.argv[2])
socket_tool = sys.argv[3]

local_patterns = (
    '127.0.0.1:',
    '[::1]:',
    'localhost:',
)

service_ports = (':5001', ':8000', ':8001', ':5173')
service_lines = [line for line in socket_log if any(p in line for p in service_ports)]
external_lines = [
    line for line in service_lines
    if not any(p in line for p in local_patterns)
]

# Best-effort process filter for relevant services
proc_lines = [
    line for line in service_lines
    if re.search(r'(python|uvicorn|node|kobold)', line, flags=re.IGNORECASE)
]

status = "pass" if len(external_lines) == 0 else "suspicious"
if socket_tool == "none":
    status = "unknown"

result = {
    "socket_tool": socket_tool,
    "service_socket_lines": len(service_lines),
    "service_process_lines": len(proc_lines),
    "external_service_lines": len(external_lines),
    "external_examples": external_lines[:10],
    "status": status,
}

report_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
PY

STATUS=$(python - "$REPORT_JSON" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8'))['status'])
PY
)

if [[ "$STATUS" != "pass" ]]; then
  if [[ "$STATUS" == "unknown" ]]; then
    echo "[warn] socket snapshot unavailable; cannot prove local-only traffic. See: $REPORT_JSON"
  else
    echo "[warn] suspicious non-local sockets detected. See: $SOCKET_LOG and $REPORT_JSON"
  fi
  if [[ "$STRICT" == "1" ]]; then
    exit 2
  fi
else
  echo "[ok] no external sockets detected for core/model ports"
fi

echo "[done] report: $REPORT_JSON"
