#!/data/data/com.termux/files/usr/bin/bash
# Попытка автоматического исправления и сбор диагностики для Roampal Android

set -euo pipefail

PROJECT_ROOT="${HOME}/roampal-android"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "❌ Проект не найден: $PROJECT_ROOT"
  echo "Сначала запустите: bash termux/setup.sh"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "🛠️  Шаг 1/4: права на запуск скриптов"
chmod +x termux/*.sh || true

echo "🧹 Шаг 2/4: остановка старых сервисов"
bash termux/stop-services.sh || true

echo "🚀 Шаг 3/4: запуск сервисов"
bash termux/start-services.sh

echo "🔎 Шаг 4/4: диагностика"
bash termux/diagnose.sh

echo "✅ Готово: логи в $PROJECT_ROOT/logs"
