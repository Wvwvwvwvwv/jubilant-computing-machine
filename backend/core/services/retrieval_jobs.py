from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
from typing import Literal, Optional


JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class RetrievalIndexJob:
    job_id: str
    source_type: str
    source_ref: str
    status: JobStatus
    created_at: float
    updated_at: float
    error: Optional[str] = None


class RetrievalJobState:
    """In-memory week-2 indexing jobs registry (bootstrap)."""

    def __init__(self):
        self._jobs: dict[str, RetrievalIndexJob] = {}
        self._job_ids: list[str] = []
        self._limit = 500

    def create_index_job(self, source_type: str, source_ref: str) -> RetrievalIndexJob:
        now = time.time()
        job = RetrievalIndexJob(
            job_id=f"rj_{uuid.uuid4().hex[:12]}",
            source_type=source_type,
            source_ref=source_ref,
            status="completed",  # week-2 bootstrap: synchronous placeholder completion
            created_at=now,
            updated_at=now,
            error=None,
        )
        self._jobs[job.job_id] = job
        self._job_ids.append(job.job_id)
        if len(self._job_ids) > self._limit:
            drop_id = self._job_ids.pop(0)
            self._jobs.pop(drop_id, None)
        return job

    def get_job(self, job_id: str) -> Optional[RetrievalIndexJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[RetrievalIndexJob]:
        limit = max(1, min(int(limit), 200))
        ids = self._job_ids[-limit:]
        return [self._jobs[jid] for jid in ids]
