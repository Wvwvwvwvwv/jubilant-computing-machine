#!/data/data/com.termux/files/usr/bin/bash
# Диагностика Roampal Android в Termux

set -u

PROJECT_ROOT="${HOME}/roampal-android"
LOG_DIR="$PROJECT_ROOT/logs"

section() {
  echo
  echo "==== $1 ===="
}

run() {
  echo "> $*"
  bash -lc "$*"
}

run_may_fail() {
  echo "> $*"
  bash -lc "$*" || true
}

section "System"
run_may_fail "date"
run_may_fail "uname -a"
run_may_fail "python --version"
run_may_fail "node --version"
run_may_fail "npm --version"

section "Project paths"
run_may_fail "pwd"
run_may_fail "ls -la $PROJECT_ROOT"
run_may_fail "ls -la $PROJECT_ROOT/termux"

section "Service processes"
run_may_fail "pgrep -af 'python main.py|uvicorn|koboldcpp|vite|node'"

section "Service health"
run_may_fail "curl -sS -m 8 http://localhost:8000/health"
run_may_fail "curl -sS -m 8 http://localhost:8001/health"
run_may_fail "curl -sS -m 8 http://localhost:5001/api/v1/model"
run_may_fail "curl -sS -m 8 http://127.0.0.1:5173 | head -c 300"

section "Port probes"
run_may_fail "for p in 5001 8000 8001 5173; do echo \"port \$p\"; (echo >/dev/tcp/127.0.0.1/\$p) >/dev/null 2>&1 && echo open || echo closed; done"

section "Last logs"
run_may_fail "tail -n 120 $LOG_DIR/core.log"
run_may_fail "tail -n 120 $LOG_DIR/embeddings.log"
run_may_fail "tail -n 120 $LOG_DIR/koboldcpp.log"
run_may_fail "tail -n 120 $LOG_DIR/frontend.log"

section "Done"
echo "Если есть ошибки выше — пришлите весь вывод этой команды."
