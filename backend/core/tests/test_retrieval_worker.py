import asyncio

from backend.core.main import retrieval_worker_loop
from backend.core.services.retrieval_jobs import RetrievalJobState


def test_retrieval_worker_loop_processes_queued_jobs():
    state = RetrievalJobState()
    job = state.create_index_job(source_type="book", source_ref="worker_job")
    stop_event = asyncio.Event()

    async def _run():
        task = asyncio.create_task(retrieval_worker_loop(state, stop_event))
        await asyncio.sleep(0.7)
        stop_event.set()
        await task

    asyncio.run(_run())
    assert state.get_job(job.job_id).status == "completed"
