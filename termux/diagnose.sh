#!/data/data/com.termux/files/usr/bin/bash
# Диагностика Roampal Android в Termux

set -u

PROJECT_ROOT="${HOME}/roampal-android"
LOG_DIR="$PROJECT_ROOT/logs"
CORE_TASK_LOG="$PROJECT_ROOT/backend/core/logs/task_audit.log"
CORE_TASK_DB="$PROJECT_ROOT/backend/core/logs/tasks.db"

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

section "Tasks diagnostics"
run_may_fail "ls -la $PROJECT_ROOT/backend/core/logs"
run_may_fail "tail -n 80 $CORE_TASK_LOG"
echo "> python (sqlite diagnostics)"
python - <<PY || true
import sqlite3
from pathlib import Path

db = Path("$CORE_TASK_DB")
if not db.exists():
    print("tasks.db not found")
    raise SystemExit(0)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
print("tasks_count=", conn.execute("select count(*) c from tasks").fetchone()["c"])
print("events_count=", conn.execute("select count(*) c from task_events").fetchone()["c"])
rows = conn.execute(
    "select task_id,status,attempt,max_attempts,updated_at from tasks order by updated_at desc limit 5"
).fetchall()
for row in rows:
    print(dict(row))

gaps = conn.execute(
    """
    select t.task_id from tasks t
    left join task_events e on e.task_id=t.task_id
    where e.id is null
    limit 20
    """
).fetchall()
print("tasks_with_no_events=", len(gaps))
PY

section "Last logs"
run_may_fail "tail -n 120 $LOG_DIR/core.log"
run_may_fail "tail -n 120 $LOG_DIR/embeddings.log"
run_may_fail "tail -n 120 $LOG_DIR/koboldcpp.log"
run_may_fail "tail -n 120 $LOG_DIR/frontend.log"

section "Done"
echo "Если есть ошибки выше — пришлите весь вывод этой команды."
