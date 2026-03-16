#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${PYTHONPATH:-.}"

TARGET_TEST="backend/core/tests/test_full_system_check.py"
LOG_DIR="${FULL_CHECK_LOG_DIR:-logs}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/full-end-to-end-check-$TS.log"
SUMMARY_FILE="$LOG_DIR/full-end-to-end-check-$TS.summary.txt"
JSON_FILE="$LOG_DIR/full-end-to-end-check-$TS.json"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[info] full check started at $(date -Is)"
echo "[info] repo=$ROOT_DIR"
echo "[info] log_file=$LOG_FILE"

PY_COMPILE_STATUS="not_run"
PYTEST_STATUS="not_run"
PYTEST_CMD=""

ensure_test_deps_current_python() {
  python - <<'PY'
import importlib.util
import sys
mods = ["pytest", "aiofiles", "multipart"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    sys.exit(1)
sys.exit(0)
PY
}

ensure_test_deps_poetry() {
  poetry run python - <<'PY'
import importlib.util
import sys
mods = ["pytest", "aiofiles", "multipart"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    sys.exit(1)
sys.exit(0)
PY
}

run_pytest() {
  if command -v poetry >/dev/null 2>&1; then
    if ! ensure_test_deps_poetry >/dev/null 2>&1; then
      echo "[warn] installing minimal test deps in Poetry environment..."
      poetry run python -m pip install -q pytest python-multipart aiofiles
    fi
    PYTEST_CMD="poetry run python -m pytest -q $TARGET_TEST"
    poetry run python -m pytest -q "$TARGET_TEST"
    return
  fi

  if ! ensure_test_deps_current_python >/dev/null 2>&1; then
    echo "[warn] installing minimal test deps in current Python..."
    python -m pip install -q pytest python-multipart aiofiles
  fi

  if command -v pytest >/dev/null 2>&1; then
    PYTEST_CMD="pytest -q $TARGET_TEST"
    pytest -q "$TARGET_TEST"
    return
  fi

  PYTEST_CMD="python -m pytest -q $TARGET_TEST"
  python -m pytest -q "$TARGET_TEST"
}

if python -m py_compile \
  backend/core/main.py \
  backend/core/routers/chat.py \
  backend/core/routers/retrieval.py \
  backend/core/routers/voice.py; then
  PY_COMPILE_STATUS="pass"
else
  PY_COMPILE_STATUS="fail"
fi

if [[ "$PY_COMPILE_STATUS" == "pass" ]]; then
  if run_pytest; then
    PYTEST_STATUS="pass"
  else
    PYTEST_STATUS="fail"
  fi
else
  PYTEST_STATUS="skipped"
fi

OVERALL_STATUS="pass"
if [[ "$PY_COMPILE_STATUS" != "pass" || "$PYTEST_STATUS" != "pass" ]]; then
  OVERALL_STATUS="fail"
fi

cat > "$SUMMARY_FILE" <<SUMMARY
full_end_to_end_check: $OVERALL_STATUS
timestamp: $TS
repo: $ROOT_DIR
log_file: $LOG_FILE
json_file: $JSON_FILE
steps:
  - py_compile: $PY_COMPILE_STATUS
  - pytest: $PYTEST_STATUS
pytest_command: ${PYTEST_CMD:-unknown}
SUMMARY

python - "$JSON_FILE" "$TS" "$ROOT_DIR" "$LOG_FILE" "$PY_COMPILE_STATUS" "$PYTEST_STATUS" "$OVERALL_STATUS" "$PYTEST_CMD" <<'PY'
import json
import sys

out, ts, repo, log_file, py_compile_status, pytest_status, overall_status, pytest_cmd = sys.argv[1:]
payload = {
    "timestamp": ts,
    "repo": repo,
    "log_file": log_file,
    "steps": {
        "py_compile": py_compile_status,
        "pytest": pytest_status,
    },
    "pytest_command": pytest_cmd,
    "status": overall_status,
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
PY

echo "[result] status=$OVERALL_STATUS"
echo "[result] summary_file=$SUMMARY_FILE"
echo "[result] json_file=$JSON_FILE"

if [[ "$OVERALL_STATUS" != "pass" ]]; then
  exit 1
fi
