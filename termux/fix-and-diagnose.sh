#!/data/data/com.termux/files/usr/bin/bash
# Быстрый ремонт и диагностика Roampal Android в Termux

set -euo pipefail

PROJECT_ROOT="${HOME}/roampal-android"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "❌ Проект не найден: $PROJECT_ROOT"
  echo "Сначала запустите: bash termux/setup.sh"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "🛠️  [1/4] Обновляю локальный репозиторий"
git fetch --all --prune || true
git pull --ff-only || true

echo "🛠️  [2/4] Проверяю исполняемость скриптов"
chmod +x termux/*.sh || true

echo "🛠️  [3/4] Перезапускаю сервисы"
bash termux/stop-services.sh || true
bash termux/start-services.sh || true

echo "🛠️  [4/4] Собираю диагностику"
bash termux/diagnose.sh
