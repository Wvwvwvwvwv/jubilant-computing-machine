# Multimodal RAG Integration — Week 3

## Scope

Week 3 introduces a background worker loop for retrieval indexing jobs.

## Delivered in Week 3

- Background retrieval worker in app lifespan (`retrieval_worker_loop`).
- Periodic processing of `queued` indexing jobs via `RetrievalJobState.process_pending_jobs(...)`.
- Worker runtime knobs:
  - `RETRIEVAL_WORKER_INTERVAL_SECONDS` (default `0.5`)
  - `RETRIEVAL_WORKER_BATCH_SIZE` (default `10`)
- Graceful worker shutdown on app stop.

## Notes

- This is still an in-memory bootstrap worker.
- Job payload/lifecycle remains compatible with Week 2 APIs.

## Next (Week 4)

- Replace in-memory processing with persistent queue / durable job backend.
- Add actual multimodal document parser/indexer execution in worker.
- Expose worker metrics endpoint (`queue_depth`, throughput, failures).
