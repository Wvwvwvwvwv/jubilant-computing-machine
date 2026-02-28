#!/data/data/com.termux/files/usr/bin/bash
# Остановка всех сервисов

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/logs"

echo "🛑 Остановка сервисов..."

for pidfile in "$PID_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
        name=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile")

        if kill -0 "$pid" 2>/dev/null; then
            echo "  Остановка $name (PID: $pid)"
            kill "$pid" 2>/dev/null || true
        fi

        rm -f "$pidfile"
    fi
done

# Дополнительная зачистка процессов, которые могли быть запущены вручную
pkill -f "$PROJECT_ROOT/frontend/node_modules/.bin/vite" 2>/dev/null || true
pkill -f "$PROJECT_ROOT/frontend/node_modules/vite/bin/vite.js" 2>/dev/null || true

echo "✅ Все сервисы остановлены"
