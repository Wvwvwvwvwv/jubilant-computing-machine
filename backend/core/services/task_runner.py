from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import json
import re
import sqlite3
import time
import uuid


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass
class TaskEvent:
    ts: float
    kind: str
    message: str
    payload: dict = field(default_factory=dict)


@dataclass
class TaskRecord:
    task_id: str
    goal: str
    status: TaskStatus
    attempt: int
    max_attempts: int
    created_at: float
    updated_at: float
    events: List[TaskEvent] = field(default_factory=list)
    last_error: Optional[str] = None
    error_class: Optional[str] = None
    approval_required: bool = False
    approved: bool = False
    approval_fingerprint: Optional[str] = None
    approved_fingerprint: Optional[str] = None


class TaskRunner:
    POLICY_VERSION = "task-approval-policy-v1"

    DANGEROUS_PATTERNS = [
        r"\brm\s+-rf\b",
        r"\bdd\s+if=",
        r"curl\s+.*\|\s*(bash|sh)",
        r"wget\s+.*\|\s*(bash|sh)",
        r"\bmkfs\.",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r">\s*/dev/",
    ]

    def __init__(self):
        self.tasks: Dict[str, TaskRecord] = {}
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = logs_dir / "task_audit.log"
        self.state_path = logs_dir / "tasks_state.json"
        self.db_path = logs_dir / "tasks.db"
        self._init_db()

    def _db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_error TEXT,
                    error_class TEXT,
                    approval_required INTEGER NOT NULL,
                    approved INTEGER NOT NULL,
                    approval_fingerprint TEXT,
                    approved_fingerprint TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                )
                """
            )
            self._ensure_tasks_schema(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_ts ON task_events(task_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)")


    def _ensure_tasks_schema(self, conn: sqlite3.Connection):
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "approval_fingerprint" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN approval_fingerprint TEXT")
        if "approved_fingerprint" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN approved_fingerprint TEXT")

    def _upsert_task(self, conn: sqlite3.Connection, task: TaskRecord):
        conn.execute(
            """
            INSERT INTO tasks (
                task_id, goal, status, attempt, max_attempts, created_at, updated_at,
                last_error, error_class, approval_required, approved,
                approval_fingerprint, approved_fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                goal=excluded.goal,
                status=excluded.status,
                attempt=excluded.attempt,
                max_attempts=excluded.max_attempts,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                last_error=excluded.last_error,
                error_class=excluded.error_class,
                approval_required=excluded.approval_required,
                approved=excluded.approved,
                approval_fingerprint=excluded.approval_fingerprint,
                approved_fingerprint=excluded.approved_fingerprint
            """,
            (
                task.task_id,
                task.goal,
                task.status.value,
                task.attempt,
                task.max_attempts,
                task.created_at,
                task.updated_at,
                task.last_error,
                task.error_class,
                int(task.approval_required),
                int(task.approved),
                task.approval_fingerprint,
                task.approved_fingerprint,
            ),
        )

    def _insert_event(self, conn: sqlite3.Connection, task_id: str, event: TaskEvent):
        conn.execute(
            """
            INSERT INTO task_events (task_id, ts, kind, message, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, event.ts, event.kind, event.message, json.dumps(event.payload, ensure_ascii=False)),
        )

    def _audit(self, task_id: str, kind: str, message: str, payload: Optional[dict] = None):
        row = {
            "ts": time.time(),
            "task_id": task_id,
            "kind": kind,
            "message": message,
            "payload": payload or {},
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _serialize_task(self, task: TaskRecord) -> dict:
        return {
            "task_id": task.task_id,
            "goal": task.goal,
            "status": task.status.value,
            "attempt": task.attempt,
            "max_attempts": task.max_attempts,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "last_error": task.last_error,
            "error_class": task.error_class,
            "approval_required": task.approval_required,
            "approved": task.approved,
            "approval_fingerprint": task.approval_fingerprint,
            "approved_fingerprint": task.approved_fingerprint,
            "events": [
                {
                    "ts": event.ts,
                    "kind": event.kind,
                    "message": event.message,
                    "payload": event.payload,
                }
                for event in task.events
            ],
        }

    def _deserialize_task(self, payload: dict) -> Optional[TaskRecord]:
        try:
            return TaskRecord(
                task_id=payload["task_id"],
                goal=payload["goal"],
                status=TaskStatus(payload["status"]),
                attempt=int(payload["attempt"]),
                max_attempts=int(payload["max_attempts"]),
                created_at=float(payload["created_at"]),
                updated_at=float(payload.get("updated_at", payload["created_at"])),
                events=[
                    TaskEvent(
                        ts=float(event["ts"]),
                        kind=event["kind"],
                        message=event["message"],
                        payload=event.get("payload", {}),
                    )
                    for event in payload.get("events", [])
                ],
                last_error=payload.get("last_error"),
                error_class=payload.get("error_class"),
                approval_required=bool(payload.get("approval_required", False)),
                approved=bool(payload.get("approved", False)),
                approval_fingerprint=payload.get("approval_fingerprint"),
                approved_fingerprint=payload.get("approved_fingerprint"),
            )
        except (KeyError, ValueError, TypeError):
            return None

    def save_state(self):
        with self._db() as conn:
            conn.execute("DELETE FROM task_events")
            conn.execute("DELETE FROM tasks")
            for task in self.tasks.values():
                self._upsert_task(conn, task)
                for event in task.events:
                    self._insert_event(conn, task.task_id, event)

    def load_state(self):
        loaded_tasks: Dict[str, TaskRecord] = {}
        with self._db() as conn:
            rows = conn.execute(
                """
                SELECT task_id, goal, status, attempt, max_attempts, created_at, updated_at,
                       last_error, error_class, approval_required, approved,
                       approval_fingerprint, approved_fingerprint
                FROM tasks
                """
            ).fetchall()

            for row in rows:
                loaded_tasks[row["task_id"]] = TaskRecord(
                    task_id=row["task_id"],
                    goal=row["goal"],
                    status=TaskStatus(row["status"]),
                    attempt=int(row["attempt"]),
                    max_attempts=int(row["max_attempts"]),
                    created_at=float(row["created_at"]),
                    updated_at=float(row["updated_at"]),
                    last_error=row["last_error"],
                    error_class=row["error_class"],
                    approval_required=bool(row["approval_required"]),
                    approved=bool(row["approved"]),
                    approval_fingerprint=row["approval_fingerprint"],
                    approved_fingerprint=row["approved_fingerprint"],
                    events=[],
                )

            event_rows = conn.execute(
                """
                SELECT task_id, ts, kind, message, payload_json
                FROM task_events
                ORDER BY id ASC
                """
            ).fetchall()
            for row in event_rows:
                task = loaded_tasks.get(row["task_id"])
                if not task:
                    continue
                try:
                    payload = json.loads(row["payload_json"])
                except json.JSONDecodeError:
                    payload = {}
                task.events.append(
                    TaskEvent(
                        ts=float(row["ts"]),
                        kind=row["kind"],
                        message=row["message"],
                        payload=payload,
                    )
                )

        if loaded_tasks:
            self.tasks = loaded_tasks
            return

        # One-time migration path from legacy JSON state file.
        if not self.state_path.exists():
            self.tasks = {}
            return

        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.tasks = {}
            return

        migrated: Dict[str, TaskRecord] = {}
        for payload in raw.get("tasks", []):
            task = self._deserialize_task(payload)
            if task:
                migrated[task.task_id] = task

        self.tasks = migrated
        if migrated:
            self.save_state()

    def _event(self, rec: TaskRecord, kind: str, message: str, payload: Optional[dict] = None):
        rec.updated_at = time.time()
        event = TaskEvent(ts=rec.updated_at, kind=kind, message=message, payload=payload or {})
        rec.events.append(event)
        self._audit(rec.task_id, kind, message, payload or {})
        with self._db() as conn:
            self._upsert_task(conn, rec)
            self._insert_event(conn, rec.task_id, event)

    def classify_risk_level(self, goal: str) -> str:
        normalized_goal = (goal or "").lower().strip()
        if any(re.search(pattern, normalized_goal) for pattern in self.DANGEROUS_PATTERNS):
            return "high"
        if normalized_goal.startswith(("curl ", "wget ")) or "sudo " in normalized_goal:
            return "medium"
        return "low"

    def approval_reason(self, risk_level: str) -> Optional[str]:
        if risk_level == "high":
            return "policy_high_risk_command"
        return None

    def policy_fingerprint(self, goal: str, risk_level: str, approval_reason: Optional[str]) -> str:
        raw = f"{self.POLICY_VERSION}|{risk_level}|{approval_reason or ''}|{(goal or '').strip()}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def requires_approval(self, goal: str) -> bool:
        return self.classify_risk_level(goal) == "high"

    def classify_error(self, exit_code: int, stderr: str) -> str:
        normalized_stderr = (stderr or "").lower()
        if "permission denied" in normalized_stderr:
            return "permission"
        if "not found" in normalized_stderr or exit_code == 127:
            return "command"
        if "timed out" in normalized_stderr or "timeout" in normalized_stderr:
            return "transient"
        return "runtime"


    def retry_backoff_seconds(self, attempt: int, error_class: str) -> int:
        """Return recommended retry delay for RETRYING tasks."""
        if error_class != "transient":
            return 0

        # Exponential backoff capped to keep MVP responsiveness.
        # attempt=1 -> 2s, attempt=2 -> 4s, attempt=3 -> 8s, ... max 30s
        return min(30, 2 ** max(1, attempt))

    def should_retry(self, error_class: str, attempt: int, max_attempts: int) -> bool:
        if attempt >= max_attempts:
            return False
        # Fail-fast policy for deterministic or policy-related failures.
        if error_class in {"command", "permission", "runtime"}:
            return False
        # Retry only transient class.
        return error_class == "transient"

    def create_task(self, goal: str, max_attempts: int = 3, approval_required: bool = False) -> TaskRecord:
        risk_level = self.classify_risk_level(goal)
        policy_requires_approval = self.approval_reason(risk_level) is not None
        approval_reason = self.approval_reason(risk_level)
        approval_required = approval_required or policy_requires_approval
        approval_fingerprint = self.policy_fingerprint(goal, risk_level, approval_reason)

        task_id = str(uuid.uuid4())
        now = time.time()
        rec = TaskRecord(
            task_id=task_id,
            goal=goal,
            status=TaskStatus.PENDING,
            attempt=0,
            max_attempts=max(1, min(max_attempts, 10)),
            created_at=now,
            updated_at=now,
            approval_required=approval_required,
            approved=not approval_required,
            approval_fingerprint=approval_fingerprint,
            approved_fingerprint=approval_fingerprint if not approval_required else None,
        )
        self.tasks[task_id] = rec
        self._event(
            rec,
            "task_created",
            "Task created",
            {
                "goal": goal,
                "max_attempts": rec.max_attempts,
                "approval_required": approval_required,
                "policy_requires_approval": policy_requires_approval,
                "policy_version": self.POLICY_VERSION,
                "risk_level": risk_level,
                "approval_reason": approval_reason,
                "approval_fingerprint": approval_fingerprint,
            },
        )
        if approval_required:
            rec.status = TaskStatus.NEEDS_APPROVAL
            self._event(
                rec,
                "task_needs_approval",
                "Task requires explicit user approval",
                {
                    "policy_version": self.POLICY_VERSION,
                    "risk_level": risk_level,
                    "approval_reason": approval_reason or "manual_request",
                    "approval_fingerprint": approval_fingerprint,
                },
            )
        return rec

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        db_task = self._load_task_from_db(task_id)
        if db_task is not None:
            self.tasks[task_id] = db_task
            return db_task
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[TaskRecord]:
        # Refresh in-memory cache from DB to stay consistent with external maintenance operations.
        self.load_state()
        items = sorted(self.tasks.values(), key=lambda x: x.updated_at, reverse=True)
        return items[: max(1, min(limit, 200))]

    def _load_task_from_db(self, task_id: str) -> Optional[TaskRecord]:
        with self._db() as conn:
            row = conn.execute(
                """
                SELECT task_id, goal, status, attempt, max_attempts, created_at, updated_at,
                       last_error, error_class, approval_required, approved,
                       approval_fingerprint, approved_fingerprint
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                return None

            rec = TaskRecord(
                task_id=row["task_id"],
                goal=row["goal"],
                status=TaskStatus(row["status"]),
                attempt=int(row["attempt"]),
                max_attempts=int(row["max_attempts"]),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
                last_error=row["last_error"],
                error_class=row["error_class"],
                approval_required=bool(row["approval_required"]),
                approved=bool(row["approved"]),
                approval_fingerprint=row["approval_fingerprint"],
                approved_fingerprint=row["approved_fingerprint"],
                events=[],
            )

            event_rows = conn.execute(
                """
                SELECT ts, kind, message, payload_json
                FROM task_events
                WHERE task_id = ?
                ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()
            for ev in event_rows:
                try:
                    payload = json.loads(ev["payload_json"])
                except json.JSONDecodeError:
                    payload = {}
                rec.events.append(
                    TaskEvent(
                        ts=float(ev["ts"]),
                        kind=ev["kind"],
                        message=ev["message"],
                        payload=payload,
                    )
                )

            return rec

    def approve_task(self, task_id: str) -> TaskRecord:
        rec = self.tasks[task_id]
        rec.approved = True
        if rec.status == TaskStatus.NEEDS_APPROVAL:
            rec.status = TaskStatus.PENDING
        risk_level = self.classify_risk_level(rec.goal)
        approval_reason = self.approval_reason(risk_level)
        rec.approved_fingerprint = self.policy_fingerprint(rec.goal, risk_level, approval_reason)
        self._event(
            rec,
            "task_approved",
            "Task approved by user",
            {
                "policy_version": self.POLICY_VERSION,
                "risk_level": risk_level,
                "approver": "user",
                "approved_at": time.time(),
                "approved_fingerprint": rec.approved_fingerprint,
            },
        )
        return rec

    def run_with_result(
        self,
        task_id: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        started_payload: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        rec = self.tasks[task_id]

        if rec.approval_required and not rec.approved:
            rec.status = TaskStatus.NEEDS_APPROVAL
            self._event(
                rec,
                "task_blocked",
                "Approval required before run",
                {
                    "policy_version": self.POLICY_VERSION,
                    "risk_level": self.classify_risk_level(rec.goal),
                    "approval_fingerprint": rec.approval_fingerprint,
                },
            )
            return rec

        if rec.approval_required and rec.approved:
            risk_level = self.classify_risk_level(rec.goal)
            approval_reason = self.approval_reason(risk_level)
            current_fingerprint = self.policy_fingerprint(rec.goal, risk_level, approval_reason)
            if rec.approved_fingerprint != current_fingerprint:
                rec.approved = False
                rec.approved_fingerprint = None
                rec.approval_fingerprint = current_fingerprint
                rec.status = TaskStatus.NEEDS_APPROVAL
                self._event(
                    rec,
                    "task_approval_invalidated",
                    "Approval invalidated due to task/policy drift",
                    {
                        "policy_version": self.POLICY_VERSION,
                        "risk_level": risk_level,
                        "approval_fingerprint": current_fingerprint,
                    },
                )
                return rec

        if rec.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
            self._event(rec, "task_skip", f"Task already terminal: {rec.status.value}")
            return rec

        rec.status = TaskStatus.RUNNING
        started = {"attempt": rec.attempt + 1}
        if started_payload:
            started.update(started_payload)
        self._event(rec, "task_started", "Task run started", started)

        if exit_code == 0:
            rec.status = TaskStatus.SUCCESS
            rec.error_class = None
            self._event(rec, "task_success", "Task succeeded", {"stdout": stdout[-1000:]})
            return rec

        rec.attempt += 1
        rec.last_error = (stderr or "Execution error")[:1000]
        rec.error_class = self.classify_error(exit_code, rec.last_error)
        retry_allowed = self.should_retry(rec.error_class, rec.attempt, rec.max_attempts)
        retry_delay_seconds = self.retry_backoff_seconds(rec.attempt, rec.error_class)
        payload = {
            "attempt": rec.attempt,
            "exit_code": exit_code,
            "error_class": rec.error_class,
            "retry_allowed": retry_allowed,
            "retry_delay_seconds": retry_delay_seconds,
        }

        if retry_allowed:
            rec.status = TaskStatus.RETRYING
            self._event(rec, "task_retry", rec.last_error, payload)
        else:
            rec.status = TaskStatus.FAILED
            self._event(rec, "task_failed", rec.last_error, payload)

        return rec
