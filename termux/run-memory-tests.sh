#!/data/data/com.termux/files/usr/bin/bash
# Запуск memory-тестов в Termux

set -euo pipefail

PROJECT_ROOT="${HOME}/roampal-android"
TEST_FILE="backend/core/tests/test_memory_flow.py"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "❌ Проект не найден: $PROJECT_ROOT"
  exit 1
fi

cd "$PROJECT_ROOT"

echo "==== Memory tests runner ===="

echo "> git pull --ff-only"
git pull --ff-only || true

if [ ! -f "$TEST_FILE" ]; then
  echo "❌ Не найден файл тестов: $TEST_FILE"
  echo "Проверьте ветку: git branch -a"
  exit 1
fi

if ! python -m pytest --version >/dev/null 2>&1; then
  echo "⚠️ pytest не найден, устанавливаю через pip"
  python -m pip install pytest
fi

echo "> PYTHONPATH=backend/core python -m pytest -q $TEST_FILE"
PYTHONPATH=backend/core python -m pytest -q "$TEST_FILE"

echo "✅ Memory-тесты завершены"
