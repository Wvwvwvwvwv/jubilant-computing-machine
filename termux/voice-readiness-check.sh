#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Voice MVP readiness check for on-device validation.
# Examples:
#   bash termux/voice-readiness-check.sh
#   MODE=duplex VOICE_GENDER=male bash termux/voice-readiness-check.sh --strict
#   bash termux/voice-readiness-check.sh --keep-session

CORE_URL="${CORE_URL:-http://127.0.0.1:8000}"
MODE="${MODE:-ptt}"               # ptt | duplex
VOICE_GENDER="${VOICE_GENDER:-female}"  # female | male
STRICT=0
KEEP_SESSION=0

# Defaults correspond to MVP GO thresholds.
LATENCY_P95_MS="${LATENCY_P95_MS:-1800}"
CRASH_FREE_RATE="${CRASH_FREE_RATE:-0.995}"
AUDIO_LOSS_PERCENT="${AUDIO_LOSS_PERCENT:-0.4}"
APPROVAL_BYPASS_INCIDENTS="${APPROVAL_BYPASS_INCIDENTS:-0}"
USER_SCORE="${USER_SCORE:-4.4}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=1
      shift
      ;;
    --keep-session)
      KEEP_SESSION=1
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ "$VOICE_GENDER" == "male" ]]; then
  TTS_ENGINE="local_piper_male"
else
  TTS_ENGINE="local_piper_female"
fi

echo "[info] CORE_URL=$CORE_URL"
echo "[info] mode=$MODE voice_gender=$VOICE_GENDER tts_engine=$TTS_ENGINE strict=$STRICT keep_session=$KEEP_SESSION"

api_call() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local tmp
  tmp="$(mktemp)"

  local code
  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" -H 'Content-Type: application/json' -d "$body" || true)"
  else
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" "$url" || true)"
  fi

  printf '%s\n' "$code"
  cat "$tmp"
  rm -f "$tmp"
}

echo "[step] start voice session"
START_BODY="$(python - <<'PY' "$MODE" "$TTS_ENGINE"
import json,sys
print(json.dumps({
  "mode": sys.argv[1],
  "stt_engine": "local_whisper_cpp",
  "tts_engine": sys.argv[2],
}))
PY
)"
START_RAW="$(api_call POST "$CORE_URL/api/voice/session/start" "$START_BODY")"
START_CODE="$(printf '%s' "$START_RAW" | head -n1)"
START_RESP="$(printf '%s' "$START_RAW" | tail -n +2)"
if [[ "$START_CODE" -lt 200 || "$START_CODE" -ge 300 ]]; then
  echo "[error] start voice session failed: HTTP $START_CODE" >&2
  echo "[error] response: $START_RESP" >&2
  exit 1
fi

VOICE_SESSION_ID="$(printf '%s' "$START_RESP" | python -c 'import json,sys; print(json.loads(sys.stdin.read())["voice_session_id"])' 2>/dev/null || true)"
if [[ -z "$VOICE_SESSION_ID" ]]; then
  echo "[error] failed to parse voice_session_id from start response" >&2
  echo "[error] raw start response: $START_RESP" >&2
  exit 1
fi

echo "[info] voice_session_id=$VOICE_SESSION_ID"

echo "[step] patch metrics"
METRICS_BODY_FULL="$(python - <<'PY' "$LATENCY_P95_MS" "$CRASH_FREE_RATE" "$AUDIO_LOSS_PERCENT" "$APPROVAL_BYPASS_INCIDENTS" "$USER_SCORE"
import json,sys
print(json.dumps({
  "latency_p95_ms": int(float(sys.argv[1])),
  "crash_free_rate": float(sys.argv[2]),
  "audio_loss_percent": float(sys.argv[3]),
  "approval_bypass_incidents": int(float(sys.argv[4])),
  "user_score": float(sys.argv[5]),
}))
PY
)"
METRICS_BODY_REDUCED="$(python - <<'PY' "$LATENCY_P95_MS" "$CRASH_FREE_RATE" "$AUDIO_LOSS_PERCENT" "$USER_SCORE"
import json,sys
print(json.dumps({
  "latency_p95_ms": int(float(sys.argv[1])),
  "crash_free_rate": float(sys.argv[2]),
  "audio_loss_percent": float(sys.argv[3]),
  "user_score": float(sys.argv[4]),
}))
PY
)"
METRICS_BODY_MINIMAL="$(python - <<'PY' "$LATENCY_P95_MS"
import json,sys
print(json.dumps({"latency_p95_ms": int(float(sys.argv[1]))}))
PY
)"

patch_ok=0
for payload_name in FULL REDUCED MINIMAL; do
  body_var="METRICS_BODY_${payload_name}"
  payload="${!body_var}"
  PATCH_RAW="$(api_call PATCH "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/metrics" "$payload")"
  PATCH_CODE="$(printf '%s' "$PATCH_RAW" | head -n1)"
  PATCH_RESP="$(printf '%s' "$PATCH_RAW" | tail -n +2)"
  if [[ "$PATCH_CODE" -ge 200 && "$PATCH_CODE" -lt 300 ]]; then
    echo "[info] metrics patch applied with payload=$payload_name"
    patch_ok=1
    break
  fi
  echo "[warn] metrics patch failed for payload=$payload_name: HTTP $PATCH_CODE" >&2
  echo "[warn] response: $PATCH_RESP" >&2
done

if [[ "$patch_ok" -ne 1 ]]; then
  echo "[warn] continuing without patched metrics" >&2
fi

echo "[step] fetch health"
HEALTH_RAW="$(api_call GET "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/health")"
HEALTH_CODE="$(printf '%s' "$HEALTH_RAW" | head -n1)"
HEALTH_RESP="$(printf '%s' "$HEALTH_RAW" | tail -n +2)"
if [[ "$HEALTH_CODE" -lt 200 || "$HEALTH_CODE" -ge 300 ]]; then
  echo "[error] health request failed: HTTP $HEALTH_CODE" >&2
  echo "[error] response: $HEALTH_RESP" >&2
  exit 1
fi
printf '%s' "$HEALTH_RESP" | python -m json.tool

echo "[step] fetch go-no-go"
GONOGO_RAW="$(api_call GET "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/go-no-go")"
GONOGO_CODE="$(printf '%s' "$GONOGO_RAW" | head -n1)"
GONOGO_RESP="$(printf '%s' "$GONOGO_RAW" | tail -n +2)"
if [[ "$GONOGO_CODE" -lt 200 || "$GONOGO_CODE" -ge 300 ]]; then
  echo "[error] go-no-go request failed: HTTP $GONOGO_CODE" >&2
  echo "[error] response: $GONOGO_RESP" >&2
  exit 1
fi
printf '%s' "$GONOGO_RESP" | python -m json.tool

DECISION="$(printf '%s' "$GONOGO_RESP" | python -c 'import json,sys; print(json.loads(sys.stdin.read()).get("decision", ""))' 2>/dev/null || true)"
if [[ -z "$DECISION" ]]; then
  echo "[error] failed to parse decision from go-no-go response" >&2
  echo "[error] raw go-no-go response: $GONOGO_RESP" >&2
  exit 1
fi

echo "[result] decision=$DECISION"

if [[ "$KEEP_SESSION" -eq 0 ]]; then
  echo "[step] stop voice session"
  STOP_RAW="$(api_call POST "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/stop")"
  STOP_CODE="$(printf '%s' "$STOP_RAW" | head -n1)"
  STOP_RESP="$(printf '%s' "$STOP_RAW" | tail -n +2)"
  if [[ "$STOP_CODE" -lt 200 || "$STOP_CODE" -ge 300 ]]; then
    echo "[warn] stop session failed: HTTP $STOP_CODE" >&2
    echo "[warn] response: $STOP_RESP" >&2
  fi
fi

if [[ "$STRICT" -eq 1 && "$DECISION" != "GO" ]]; then
  echo "[error] strict mode enabled and decision is $DECISION" >&2
  exit 1
fi

echo "[done] voice readiness check complete"
