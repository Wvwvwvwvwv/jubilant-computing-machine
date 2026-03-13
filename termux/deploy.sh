#!/data/data/com.termux/files/usr/bin/bash
# Полностью автоматическое развертывание/обновление Roampal Android в Termux.

set -euo pipefail

REPO_URL="https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git"
TARGET_DIR="$HOME/roampal-android"
BRANCH="${1:-work}"
RUN_SMOKE="${RUN_SMOKE:-1}"
LAST_GOOD_FILE="$TARGET_DIR/.last_good_commit"
LEGACY_LAST_GOOD_FILE="$TARGET_DIR/.last_known_good_sha"
CURRENT_BASELINE=""
DEPLOY_FAILED=1

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

rollback_last_good() {
  if [ "$DEPLOY_FAILED" -eq 0 ]; then
    return
  fi

  if [ ! -f "$LAST_GOOD_FILE" ] && [ -f "$LEGACY_LAST_GOOD_FILE" ]; then
    cp "$LEGACY_LAST_GOOD_FILE" "$LAST_GOOD_FILE" 2>/dev/null || true
  fi

  if [ ! -f "$LAST_GOOD_FILE" ]; then
    log "Deploy failed and no $LAST_GOOD_FILE found; manual recovery required."
    return
  fi

  local last_good
  last_good="$(cat "$LAST_GOOD_FILE" 2>/dev/null || true)"
  if [ -z "$last_good" ]; then
    log "Deploy failed and last good commit is empty; manual recovery required."
    return
  fi

  log "Deploy failed. Rolling back to last known good commit: $last_good"
  git reset --hard "$last_good" || return
  bash termux/start-services.sh || true
  log "Rollback attempted. Run: bash termux/diagnose.sh"
}

trap rollback_last_good EXIT

preflight_tasks_schema() {
  python - <<'PY'
from pathlib import Path
import sqlite3

root = Path.home() / 'roampal-android'
db = root / 'backend' / 'core' / 'logs' / 'tasks.db'
if not db.exists():
    print('preflight: tasks.db not found (ok on fresh install)')
    raise SystemExit(0)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cols = {row['name'] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
required = {
    'task_id', 'goal', 'status', 'attempt', 'max_attempts',
    'approval_required', 'approved', 'approval_fingerprint', 'approved_fingerprint'
}
missing = sorted(required - cols)
if missing:
    raise SystemExit(f'preflight failed: tasks schema missing columns: {missing}')

tasks_count = conn.execute('select count(*) from tasks').fetchone()[0]
events_count = conn.execute('select count(*) from task_events').fetchone()[0]
print(f'preflight: tasks schema ok (tasks={tasks_count}, events={events_count})')
PY
}

log "Roampal deploy started (branch=$BRANCH)"

if [ ! -d "$TARGET_DIR/.git" ]; then
  log "Repository not found, cloning fresh copy..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

if git rev-parse --verify HEAD >/dev/null 2>&1; then
  CURRENT_BASELINE="$(git rev-parse HEAD)"
fi

if [ -f "$LAST_GOOD_FILE" ]; then
  log "Last good commit: $(cat "$LAST_GOOD_FILE" 2>/dev/null || echo unknown)"
elif [ -f "$LEGACY_LAST_GOOD_FILE" ]; then
  cp "$LEGACY_LAST_GOOD_FILE" "$LAST_GOOD_FILE" 2>/dev/null || true
  log "Last good commit (legacy): $(cat "$LEGACY_LAST_GOOD_FILE" 2>/dev/null || echo unknown)"
fi

# Остановить сервисы до обновления кода/зависимостей.
if [ -f "termux/stop-services.sh" ]; then
  log "Stopping running services..."
  bash termux/stop-services.sh || true
fi

log "Syncing git state..."
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"
git fetch --all --prune
git checkout "$BRANCH"
# reset --hard решает типичный Termux кейс с diverged history после force-push на work.
git reset --hard "origin/$BRANCH"

log "Running setup..."
bash termux/setup.sh

log "Starting services..."
bash termux/start-services.sh

log "Running preflight checks..."
preflight_tasks_schema

if [ "$RUN_SMOKE" = "1" ] && [ -f "termux/full-smoke.sh" ]; then
  log "Running full smoke checks..."
  bash termux/full-smoke.sh
else
  log "Smoke checks skipped (RUN_SMOKE=$RUN_SMOKE)."
fi

# Deploy success from this point.
DEPLOY_FAILED=0
CURRENT_BASELINE="$(git rev-parse HEAD)"
printf '%s\n' "$CURRENT_BASELINE" > "$LAST_GOOD_FILE"
printf '%s\n' "$CURRENT_BASELINE" > "$LEGACY_LAST_GOOD_FILE"
log "Recorded last good commit: $CURRENT_BASELINE"

log "Deploy completed successfully"
log "Core: http://127.0.0.1:8000 | Frontend: http://127.0.0.1:5173"
