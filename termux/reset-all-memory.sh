#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Full memory reset helper.
# Usage:
#   bash termux/reset-all-memory.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_MEMORY_DIR="${HOME}/roampal-android/data/memory"
COMPANION_DB="${ROOT_DIR}/backend/core/logs/companion.db"

printf '[info] root=%s\n' "$ROOT_DIR"
printf '[info] removing memory dir: %s\n' "$DATA_MEMORY_DIR"
rm -rf "$DATA_MEMORY_DIR"
mkdir -p "$DATA_MEMORY_DIR"

if [[ -f "$COMPANION_DB" ]]; then
  printf '[info] removing companion db: %s\n' "$COMPANION_DB"
  rm -f "$COMPANION_DB"
else
  printf '[info] companion db not found: %s\n' "$COMPANION_DB"
fi

printf '[done] full memory reset completed\n'
printf '[hint] restart core service to reinitialize memory backends\n'
