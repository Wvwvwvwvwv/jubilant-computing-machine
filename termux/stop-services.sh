#!/data/data/com.termux/files/usr/bin/bash
# Остановка всех сервисов

PROJECT_ROOT="$HOME/roampal-android"
PID_DIR="$PROJECT_ROOT/logs"

echo "🛑 Остановка сервисов..."

for pidfile in "$PID_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
        name=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile")
        
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Остановка $name (PID: $pid)"
            kill "$pid"
        fi
        
        rm "$pidfile"
    fi
done

echo "✅ Все сервисы остановлены"
