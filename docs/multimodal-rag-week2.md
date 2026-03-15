# Multimodal RAG Integration — Week 2

## Scope

Week 2 adds an indexing-jobs control plane for retrieval ingestion orchestration.

## Delivered in Week 2

- Retrieval jobs state service: `backend/core/services/retrieval_jobs.py`.
- Retrieval jobs API endpoints:
  - `POST /api/retrieval/index`
  - `GET /api/retrieval/jobs`
  - `GET /api/retrieval/jobs/{job_id}`
- Week-2 bootstrap behavior: `process_now=true` processes jobs synchronously (`completed`), `process_now=false` leaves them in `queued`.
- Retrieval search path remains backward-compatible (legacy by default, multimodal by feature flag/runtime injection).
- Job payload includes telemetry fields: `started_at`, `completed_at`, `attempts`, `error`.

## Next (Week 3)

- Introduce asynchronous workers for actual document indexing.
- Add job progress (`queued/running/completed/failed`) and error telemetry.
- ✅ Connect `books/upload` pipeline to retrieval index enqueue path (`retrieval_job_id` in upload response).
