#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${PYTHONPATH:-.}"

TARGET_TEST="backend/core/tests/test_full_system_check.py"

run_pytest() {
  # Prefer Poetry env when available, but self-heal if pytest is missing there.
  if command -v poetry >/dev/null 2>&1; then
    if poetry run python -c "import pytest" >/dev/null 2>&1; then
      poetry run python -m pytest -q "$TARGET_TEST"
      return
    fi

    echo "[warn] pytest is missing in Poetry environment; installing minimal test deps..."
    poetry run python -m pip install -q pytest python-multipart aiofiles
    poetry run python -m pytest -q "$TARGET_TEST"
    return
  fi

  # Global pytest command
  if command -v pytest >/dev/null 2>&1; then
    pytest -q "$TARGET_TEST"
    return
  fi

  # Module execution path
  if python -c "import pytest" >/dev/null 2>&1; then
    python -m pytest -q "$TARGET_TEST"
    return
  fi

  # Last-resort self-heal for environments without pytest preinstalled.
  echo "[warn] pytest is not available; installing minimal test deps in current Python..."
  python -m pip install -q pytest python-multipart aiofiles
  python -m pytest -q "$TARGET_TEST"
}

python -m py_compile \
  backend/core/main.py \
  backend/core/routers/chat.py \
  backend/core/routers/retrieval.py \
  backend/core/routers/voice.py

run_pytest
