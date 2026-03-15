from backend.core.services.retrieval_jobs import RetrievalJobState


def test_create_and_get_job():
    state = RetrievalJobState()
    job = state.create_index_job(source_type="book", source_ref="book_1")

    fetched = state.get_job(job.job_id)
    assert fetched is not None
    assert fetched.job_id == job.job_id
    assert fetched.status == "queued"


def test_process_job_marks_completed_and_sets_timestamps():
    state = RetrievalJobState()
    job = state.create_index_job(source_type="manual", source_ref="ref_1")

    processed = state.process_job(job.job_id)
    assert processed is not None
    assert processed.status == "completed"
    assert processed.started_at is not None
    assert processed.completed_at is not None
    assert processed.attempts == 1


def test_list_jobs_respects_limit_and_status_filter():
    state = RetrievalJobState()
    for i in range(5):
        state.create_index_job(source_type="manual", source_ref=f"ref_{i}")

    state.process_job(state.list_jobs(limit=1)[0].job_id)

    queued = state.list_jobs(limit=10, status="queued")
    assert all(x.status == "queued" for x in queued)

    jobs = state.list_jobs(limit=3)
    assert len(jobs) == 3
    assert jobs[-1].source_ref == "ref_4"


def test_process_job_marks_failed_when_reason_provided():
    state = RetrievalJobState()
    job = state.create_index_job(source_type="file", source_ref="f1")
    processed = state.process_job(job.job_id, fail_reason="bad parse")
    assert processed is not None
    assert processed.status == "failed"
    assert processed.error == "bad parse"
    assert processed.attempts == 1


def test_process_pending_jobs_processes_only_queued():
    state = RetrievalJobState()
    j1 = state.create_index_job(source_type="book", source_ref="a")
    j2 = state.create_index_job(source_type="book", source_ref="b")
    state.process_job(j1.job_id, fail_reason="bad")

    processed = state.process_pending_jobs(max_jobs=10)
    assert processed == 1
    assert state.get_job(j1.job_id).status == "failed"
    assert state.get_job(j2.job_id).status == "completed"
