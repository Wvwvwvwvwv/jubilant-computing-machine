from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import json
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


class TaskRunner:
    """
    Minimal in-memory task runner scaffold.
    """
    def __init__(self):
        self.tasks: Dict[str, TaskRecord] = {}
        self.log_path = Path(__file__).resolve().parents[1] / "logs" / "task_audit.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

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

    def create_task(self, goal: str, max_attempts: int = 3) -> TaskRecord:
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
        )
        rec.events.append(TaskEvent(ts=now, kind="task_created", message="Task created"))
        self.tasks[task_id] = rec
        self._audit(task_id, "task_created", "Task created", {"goal": goal, "max_attempts": rec.max_attempts})
        return rec

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[TaskRecord]:
        items = sorted(self.tasks.values(), key=lambda x: x.updated_at, reverse=True)
        return items[: max(1, min(limit, 200))]

    def start_task(self, task_id: str) -> TaskRecord:
        rec = self.tasks[task_id]
        rec.status = TaskStatus.RUNNING
        rec.updated_at = time.time()
        rec.events.append(TaskEvent(ts=rec.updated_at, kind="task_started", message="Task started"))
        self._audit(task_id, "task_started", "Task started")
        return rec

    def mark_retry(self, task_id: str, error: str) -> TaskRecord:
        rec = self.tasks[task_id]
        rec.attempt += 1
        rec.last_error = error
        rec.updated_at = time.time()

        if rec.attempt >= rec.max_attempts:
            rec.status = TaskStatus.FAILED
            rec.events.append(TaskEvent(ts=rec.updated_at, kind="task_failed", message=error))
            self._audit(task_id, "task_failed", error, {"attempt": rec.attempt})
        else:
            rec.status = TaskStatus.RETRYING
            rec.events.append(TaskEvent(ts=rec.updated_at, kind="task_retry", message=error))
            self._audit(task_id, "task_retry", error, {"attempt": rec.attempt})

        return rec

    def mark_success(self, task_id: str, note: str = "Task succeeded") -> TaskRecord:
        rec = self.tasks[task_id]
        rec.status = TaskStatus.SUCCESS
        rec.updated_at = time.time()
        rec.events.append(TaskEvent(ts=rec.updated_at, kind="task_success", message=note))
        self._audit(task_id, "task_success", note)
        return rec
