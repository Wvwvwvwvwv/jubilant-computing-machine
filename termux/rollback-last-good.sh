#!/data/data/com.termux/files/usr/bin/bash
# Быстрый откат на последний успешный deploy-checkpoint

set -euo pipefail

TARGET_DIR="$HOME/roampal-android"
CHECKPOINT_FILE="$TARGET_DIR/.last_known_good_sha"

if [ ! -d "$TARGET_DIR/.git" ]; then
  echo "❌ Repo not found: $TARGET_DIR"
  exit 1
fi

if [ ! -f "$CHECKPOINT_FILE" ]; then
  echo "❌ Checkpoint file not found: $CHECKPOINT_FILE"
  echo "Подсказка: сначала выполните успешный deploy (termux/deploy.sh work)."
  exit 1
fi

SHA=$(cat "$CHECKPOINT_FILE")

cd "$TARGET_DIR"
echo "🛑 Stopping services..."
bash termux/stop-services.sh || true

echo "🔄 Rolling back to $SHA"
git fetch --all --prune
git checkout "$SHA"
git reset --hard "$SHA"

echo "🚀 Starting services..."
bash termux/start-services.sh

echo "🧪 Running full smoke..."
bash termux/full-smoke.sh

echo "✅ Rollback complete: $SHA"
