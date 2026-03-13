#!/data/data/com.termux/files/usr/bin/bash
# Запуск всех сервисов Roampal Android

set -e

PROJECT_ROOT="$HOME/roampal-android"

echo "🚀 Запуск Roampal Android Services"
echo "==================================="

# Сначала мягко останавливаем возможные старые процессы,
# чтобы избежать дубликатов (особенно kobold/core после падений deploy/smoke).
if [ -f "$PROJECT_ROOT/termux/stop-services.sh" ]; then
    bash "$PROJECT_ROOT/termux/stop-services.sh" >/dev/null 2>&1 || true
fi

# Проверка установки
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "❌ Проект не найден. Запустите setup.sh"
    exit 1
fi

# Функция для запуска в фоне с логами
start_service() {
    local name=$1
    local cmd=$2
    local log="$PROJECT_ROOT/logs/$name.log"

    mkdir -p "$PROJECT_ROOT/logs"

    echo "▶️  Запуск $name..."
    nohup bash -c "$cmd" > "$log" 2>&1 &
    echo $! > "$PROJECT_ROOT/logs/$name.pid"
    echo "   PID: $(cat $PROJECT_ROOT/logs/$name.pid)"
}

wait_http() {
    local url=$1
    local attempts=${2:-20}
    local sleep_s=${3:-1}

    for _ in $(seq 1 "$attempts"); do
        if curl -fsS -m 3 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep "$sleep_s"
    done

    return 1
}

free_frontend_port() {
    # Закрываем старые процессы frontend перед запуском, чтобы strictPort не падал
    if [ -f "$PROJECT_ROOT/logs/frontend.pid" ]; then
        kill "$(cat "$PROJECT_ROOT/logs/frontend.pid")" 2>/dev/null || true
        rm -f "$PROJECT_ROOT/logs/frontend.pid"
    fi
    pkill -f "frontend/node_modules/.bin/vite" 2>/dev/null || true
}

# 1. Запуск KoboldCpp
start_service "koboldcpp" "cd $PROJECT_ROOT && bash termux/start-kobold.sh"
echo "⏳ Ожидание запуска KoboldCpp (30 сек)..."
sleep 30

# 2. Запуск Embeddings Service
start_service "embeddings" "cd $PROJECT_ROOT/backend/embeddings && python main.py"
sleep 5

# 3. Запуск Core API
start_service "core" "cd $PROJECT_ROOT && python -m backend.core.main"
sleep 5

# 4. Запуск Frontend
free_frontend_port
start_service "frontend" "cd $PROJECT_ROOT/frontend && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"

if ! wait_http "http://127.0.0.1:5173" 20 1; then
    echo "⚠️ Frontend не поднялся на :5173, пробую запасной запуск с 0.0.0.0..."
    if [ -f "$PROJECT_ROOT/logs/frontend.pid" ]; then
        kill "$(cat "$PROJECT_ROOT/logs/frontend.pid")" 2>/dev/null || true
    fi
    start_service "frontend" "cd $PROJECT_ROOT/frontend && npm run dev -- --host"
    sleep 3
fi

echo ""
echo "✅ Все сервисы запущены!"
echo ""
echo "📊 Статус:"
echo "  KoboldCpp:  http://localhost:5001"
echo "  Core API:   http://localhost:8000"
echo "  Embeddings: http://localhost:8001"
echo "  Frontend:   http://localhost:5173"
echo ""
echo "📝 Логи: $PROJECT_ROOT/logs/"
echo ""
echo "Для остановки: ./termux/stop-services.sh"
