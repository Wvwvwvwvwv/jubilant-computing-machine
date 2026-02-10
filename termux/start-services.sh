#!/data/data/com.termux/files/usr/bin/bash
# Запуск всех сервисов Roampal Android

set -e

PROJECT_ROOT="$HOME/roampal-android"

echo "🚀 Запуск Roampal Android Services"
echo "==================================="

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

# 1. Запуск KoboldCpp
start_service "koboldcpp" "cd $PROJECT_ROOT && ./termux/start-kobold.sh"
echo "⏳ Ожидание запуска KoboldCpp (30 сек)..."
sleep 30

# 2. Запуск Embeddings Service
start_service "embeddings" "cd $PROJECT_ROOT/backend/embeddings && python main.py"
sleep 5

# 3. Запуск Core API
start_service "core" "cd $PROJECT_ROOT/backend/core && python main.py"
sleep 5

# 4. Запуск Frontend
start_service "frontend" "cd $PROJECT_ROOT/frontend && npm run dev -- --host"

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
