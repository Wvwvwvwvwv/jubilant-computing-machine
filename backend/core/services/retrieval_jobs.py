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
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0


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
            status="queued",
            created_at=now,
            updated_at=now,
            error=None,
            started_at=None,
            completed_at=None,
            attempts=0,
        )
        self._jobs[job.job_id] = job
        self._job_ids.append(job.job_id)
        if len(self._job_ids) > self._limit:
            drop_id = self._job_ids.pop(0)
            self._jobs.pop(drop_id, None)
        return job

    def process_job(self, job_id: str, fail_reason: str | None = None) -> Optional[RetrievalIndexJob]:
        job = self._jobs.get(job_id)
        if job is None:
            return None

        now = time.time()
        job.status = "running"
        job.started_at = now
        job.updated_at = now
        job.attempts += 1

        if fail_reason:
            job.status = "failed"
            job.error = fail_reason
            job.completed_at = time.time()
            job.updated_at = job.completed_at
            return job

        job.status = "completed"
        job.error = None
        job.completed_at = time.time()
        job.updated_at = job.completed_at
        return job

    def get_job(self, job_id: str) -> Optional[RetrievalIndexJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20, status: JobStatus | None = None) -> list[RetrievalIndexJob]:
        limit = max(1, min(int(limit), 200))
        ids = self._job_ids[::-1]
        items: list[RetrievalIndexJob] = []
        for jid in ids:
            job = self._jobs[jid]
            if status is not None and job.status != status:
                continue
            items.append(job)
            if len(items) >= limit:
                break
        return list(reversed(items))
