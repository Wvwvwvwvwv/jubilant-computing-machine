#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${PYTHONPATH:-.}"

python -m py_compile \
  backend/core/main.py \
  backend/core/routers/chat.py \
  backend/core/routers/retrieval.py \
  backend/core/routers/voice.py

pytest -q backend/core/tests/test_full_system_check.py
