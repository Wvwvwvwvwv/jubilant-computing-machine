#!/data/data/com.termux/files/usr/bin/bash
# Проверка критичных фиксов чата и загрузки книг

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KOBOLD_TARGET="$PROJECT_ROOT/backend/core/services/kobold_client.py"
BOOKS_TARGET="$PROJECT_ROOT/backend/core/routers/books.py"

if [ ! -f "$KOBOLD_TARGET" ]; then
  echo "❌ Не найден $KOBOLD_TARGET"
  exit 1
fi

if ! grep -q "def _msg_field" "$KOBOLD_TARGET"; then
  echo "❌ Критичный chat-fix отсутствует: нет _msg_field в kobold_client.py"
  echo "   Выполните: git fetch origin --prune && git checkout main && git reset --hard origin/main"
  exit 1
fi

if ! grep -q "self._msg_field(msg, \"role\"" "$KOBOLD_TARGET"; then
  echo "❌ Критичный chat-fix отсутствует: _format_messages не использует _msg_field"
  echo "   Выполните: git fetch origin --prune && git checkout main && git reset --hard origin/main"
  exit 1
fi

if [ ! -f "$BOOKS_TARGET" ]; then
  echo "❌ Не найден $BOOKS_TARGET"
  exit 1
fi

if ! grep -q "ALLOWED_EXTENSIONS" "$BOOKS_TARGET" || ! grep -q "\.html" "$BOOKS_TARGET" || ! grep -q "\.fb2" "$BOOKS_TARGET" || ! grep -q "\.pdf" "$BOOKS_TARGET"; then
  echo "❌ Критичный books-fix отсутствует: multi-format upload (.html/.fb2/.pdf) не найден"
  echo "   Выполните: git fetch origin --prune && git checkout main && git reset --hard origin/main"
  exit 1
fi

echo "✅ Verification passed (chat-fix + books multi-format)"
