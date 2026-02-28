#!/data/data/com.termux/files/usr/bin/bash
# Быстрый фикс типичных проблем + диагностика

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔧 Applying quick fixes..."
chmod +x "$PROJECT_ROOT"/termux/*.sh || true

if [ -d "$PROJECT_ROOT/frontend" ]; then
  echo "📦 Frontend deps check..."
  (cd "$PROJECT_ROOT/frontend" && npm install --silent)
fi

echo "🩺 Running diagnostics..."
bash "$PROJECT_ROOT/termux/diagnose.sh"
