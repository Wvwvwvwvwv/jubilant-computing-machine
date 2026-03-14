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
START_RESP="$(curl -fsS -X POST "$CORE_URL/api/voice/session/start" -H 'Content-Type: application/json' -d "$START_BODY")"
VOICE_SESSION_ID="$(printf '%s' "$START_RESP" | python -c 'import json,sys; print(json.loads(sys.stdin.read())["voice_session_id"])' 2>/dev/null || true)"
if [[ -z "$VOICE_SESSION_ID" ]]; then
  echo "[error] failed to parse voice_session_id from start response" >&2
  echo "[error] raw start response: $START_RESP" >&2
  exit 1
fi

echo "[info] voice_session_id=$VOICE_SESSION_ID"

echo "[step] patch metrics"
METRICS_BODY="$(python - <<'PY' "$LATENCY_P95_MS" "$CRASH_FREE_RATE" "$AUDIO_LOSS_PERCENT" "$APPROVAL_BYPASS_INCIDENTS" "$USER_SCORE"
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
curl -fsS -X PATCH "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/metrics" -H 'Content-Type: application/json' -d "$METRICS_BODY" >/dev/null

echo "[step] fetch health"
HEALTH_RESP="$(curl -fsS "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/health")"
printf '%s' "$HEALTH_RESP" | python -m json.tool

echo "[step] fetch go-no-go"
GONOGO_RESP="$(curl -fsS "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/go-no-go")"
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
  curl -fsS -X POST "$CORE_URL/api/voice/session/$VOICE_SESSION_ID/stop" >/dev/null || true
fi

if [[ "$STRICT" -eq 1 && "$DECISION" != "GO" ]]; then
  echo "[error] strict mode enabled and decision is $DECISION" >&2
  exit 1
fi

echo "[done] voice readiness check complete"
