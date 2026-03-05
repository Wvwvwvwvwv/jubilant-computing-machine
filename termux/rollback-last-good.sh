#!/data/data/com.termux/files/usr/bin/bash
# Быстрый откат на последний успешный deploy-checkpoint

set -euo pipefail

TARGET_DIR="$HOME/roampal-android"
CHECKPOINT_FILE="$TARGET_DIR/.last_known_good_sha"
PINNED_TAG_FILE="$TARGET_DIR/termux/pinned-safe-tag"

MODE="${1:-auto}"

print_help() {
  cat <<'EOF'
Usage:
  bash termux/rollback-last-good.sh [auto|pinned]

Modes:
  auto    Use .last_known_good_sha if present, otherwise fallback to pinned tag.
  pinned  Force rollback to pinned tag from termux/pinned-safe-tag.
EOF
}

case "$MODE" in
  -h|--help|help)
    print_help
    exit 0
    ;;
  auto|pinned)
    ;;
  *)
    echo "❌ Unknown mode: $MODE"
    print_help
    exit 2
    ;;
esac

if [ ! -d "$TARGET_DIR/.git" ]; then
  echo "❌ Repo not found: $TARGET_DIR"
  exit 1
fi

if [ "$MODE" = "pinned" ]; then
  if [ ! -f "$PINNED_TAG_FILE" ]; then
    echo "❌ Pinned tag file not found: $PINNED_TAG_FILE"
    exit 1
  fi
  PINNED_TAG=$(cat "$PINNED_TAG_FILE")
  SHA="$PINNED_TAG"
elif [ -f "$CHECKPOINT_FILE" ]; then
  SHA=$(cat "$CHECKPOINT_FILE")
else
  if [ ! -f "$PINNED_TAG_FILE" ]; then
    echo "❌ Checkpoint file not found: $CHECKPOINT_FILE"
    echo "❌ Pinned tag file not found: $PINNED_TAG_FILE"
    echo "Подсказка: сначала выполните успешный deploy (termux/deploy.sh work)."
    exit 1
  fi
  PINNED_TAG=$(cat "$PINNED_TAG_FILE")
  SHA="$PINNED_TAG"
  echo "ℹ️ Checkpoint not found, using pinned tag: $PINNED_TAG"
fi

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
