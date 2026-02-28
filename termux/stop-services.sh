#!/data/data/com.termux/files/usr/bin/bash
# Остановка всех сервисов

set -euo pipefail

PROJECT_ROOT="$HOME/roampal-android"
PID_DIR="$PROJECT_ROOT/logs"

echo "🛑 Остановка сервисов..."

stop_pid() {
    local pid="$1"
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 1
        kill -9 "$pid" 2>/dev/null || true
    fi
}

kill_pattern() {
    local pattern="$1"
    pkill -f "$pattern" 2>/dev/null || true
    sleep 1
    pgrep -f "$pattern" 2>/dev/null | while read -r pid; do
        stop_pid "$pid"
    done
}

for pidfile in "$PID_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
        name=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Остановка $name (PID: $pid)"
            stop_pid "$pid"
        fi
        rm -f "$pidfile"
    fi
done

kill_pattern "koboldcpp.py"
kill_pattern "backend/embeddings.*python main.py"
kill_pattern "backend/core.*python main.py"
kill_pattern "uvicorn.*8000"
kill_pattern "uvicorn.*8001"
kill_pattern "frontend/node_modules/.bin/vite"
kill_pattern "node .*vite"

sleep 1
echo "✅ Все сервисы остановлены"
