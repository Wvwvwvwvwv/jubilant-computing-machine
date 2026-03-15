#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${PYTHONPATH:-.}"

run_pytest() {
  if command -v poetry >/dev/null 2>&1; then
    poetry run pytest -q backend/core/tests/test_full_system_check.py
    return
  fi

  if command -v pytest >/dev/null 2>&1; then
    pytest -q backend/core/tests/test_full_system_check.py
    return
  fi

  if python -c "import pytest" >/dev/null 2>&1; then
    python -m pytest -q backend/core/tests/test_full_system_check.py
    return
  fi

  echo "[error] pytest is not available (no pytest/poetry/python -m pytest path found)." >&2
  echo "[hint] Install test dependencies, e.g. 'pip install pytest' or use Poetry env." >&2
  exit 127
}

python -m py_compile \
  backend/core/main.py \
  backend/core/routers/chat.py \
  backend/core/routers/retrieval.py \
  backend/core/routers/voice.py

run_pytest
