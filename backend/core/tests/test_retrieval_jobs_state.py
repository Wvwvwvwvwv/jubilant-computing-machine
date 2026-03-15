from backend.core.services.retrieval_jobs import RetrievalJobState


def test_create_and_get_job():
    state = RetrievalJobState()
    job = state.create_index_job(source_type="book", source_ref="book_1")

    fetched = state.get_job(job.job_id)
    assert fetched is not None
    assert fetched.job_id == job.job_id
    assert fetched.status == "completed"


def test_list_jobs_respects_limit():
    state = RetrievalJobState()
    for i in range(5):
        state.create_index_job(source_type="manual", source_ref=f"ref_{i}")

    jobs = state.list_jobs(limit=3)
    assert len(jobs) == 3
    assert jobs[-1].source_ref == "ref_4"
