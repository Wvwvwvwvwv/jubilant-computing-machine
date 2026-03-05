#!/data/data/com.termux/files/usr/bin/bash
# Полностью автоматическое развертывание/обновление Roampal Android в Termux.

set -euo pipefail

REPO_URL="https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git"
TARGET_DIR="$HOME/roampal-android"
BRANCH="${1:-work}"
RUN_SMOKE="${RUN_SMOKE:-1}"
CHECKPOINT_FILE="$TARGET_DIR/.last_known_good_sha"

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

log "Roampal deploy started (branch=$BRANCH)"

if [ ! -d "$TARGET_DIR/.git" ]; then
  log "Repository not found, cloning fresh copy..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

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

if [ "$RUN_SMOKE" = "1" ] && [ -f "termux/full-smoke.sh" ]; then
  log "Running full smoke checks..."
  bash termux/full-smoke.sh
else
  log "Smoke checks skipped (RUN_SMOKE=$RUN_SMOKE)."
fi

GOOD_SHA=$(git rev-parse HEAD)
echo "$GOOD_SHA" > "$CHECKPOINT_FILE"
log "Checkpoint updated: $CHECKPOINT_FILE -> $GOOD_SHA"

log "Deploy completed successfully"
log "Core: http://127.0.0.1:8000 | Frontend: http://127.0.0.1:5173"
