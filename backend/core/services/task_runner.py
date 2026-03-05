from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import json
import re
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


class TaskRunner:
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
            )
        except (KeyError, ValueError, TypeError):
            return None

    def save_state(self):
        snapshot = {
            "saved_at": time.time(),
            "tasks": [self._serialize_task(task) for task in self.tasks.values()],
        }
        with self.state_path.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

    def load_state(self):
        if not self.state_path.exists():
            return

        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        loaded_tasks: Dict[str, TaskRecord] = {}
        for payload in raw.get("tasks", []):
            task = self._deserialize_task(payload)
            if task:
                loaded_tasks[task.task_id] = task

        self.tasks = loaded_tasks

    def _event(self, rec: TaskRecord, kind: str, message: str, payload: Optional[dict] = None):
        rec.updated_at = time.time()
        rec.events.append(TaskEvent(ts=rec.updated_at, kind=kind, message=message, payload=payload or {}))
        self._audit(rec.task_id, kind, message, payload or {})
        self.save_state()

    def requires_approval(self, goal: str) -> bool:
        normalized_goal = (goal or "").lower()
        return any(re.search(pattern, normalized_goal) for pattern in self.DANGEROUS_PATTERNS)

    def classify_error(self, exit_code: int, stderr: str) -> str:
        normalized_stderr = (stderr or "").lower()
        if "permission denied" in normalized_stderr:
            return "permission"
        if "not found" in normalized_stderr or exit_code == 127:
            return "command"
        if "timed out" in normalized_stderr or "timeout" in normalized_stderr:
            return "transient"
        return "runtime"

    def create_task(self, goal: str, max_attempts: int = 3, approval_required: bool = False) -> TaskRecord:
        policy_requires_approval = self.requires_approval(goal)
        approval_required = approval_required or policy_requires_approval

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
            },
        )
        if approval_required:
            rec.status = TaskStatus.NEEDS_APPROVAL
            self._event(rec, "task_needs_approval", "Task requires explicit user approval")
        return rec

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[TaskRecord]:
        items = sorted(self.tasks.values(), key=lambda x: x.updated_at, reverse=True)
        return items[: max(1, min(limit, 200))]

    def approve_task(self, task_id: str) -> TaskRecord:
        rec = self.tasks[task_id]
        rec.approved = True
        if rec.status == TaskStatus.NEEDS_APPROVAL:
            rec.status = TaskStatus.PENDING
        self._event(rec, "task_approved", "Task approved by user")
        return rec

    def run_with_result(self, task_id: str, exit_code: int, stdout: str = "", stderr: str = "") -> TaskRecord:
        rec = self.tasks[task_id]

        if rec.approval_required and not rec.approved:
            rec.status = TaskStatus.NEEDS_APPROVAL
            self._event(rec, "task_blocked", "Approval required before run")
            return rec

        if rec.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
            self._event(rec, "task_skip", f"Task already terminal: {rec.status.value}")
            return rec

        rec.status = TaskStatus.RUNNING
        self._event(rec, "task_started", "Task run started", {"attempt": rec.attempt + 1})

        if exit_code == 0:
            rec.status = TaskStatus.SUCCESS
            rec.error_class = None
            self._event(rec, "task_success", "Task succeeded", {"stdout": stdout[-1000:]})
            return rec

        rec.attempt += 1
        rec.last_error = (stderr or "Execution error")[:1000]
        rec.error_class = self.classify_error(exit_code, rec.last_error)
        payload = {
            "attempt": rec.attempt,
            "exit_code": exit_code,
            "error_class": rec.error_class,
        }

        if rec.attempt >= rec.max_attempts:
            rec.status = TaskStatus.FAILED
            self._event(rec, "task_failed", rec.last_error, payload)
        else:
            rec.status = TaskStatus.RETRYING
            self._event(rec, "task_retry", rec.last_error, payload)

        return rec
