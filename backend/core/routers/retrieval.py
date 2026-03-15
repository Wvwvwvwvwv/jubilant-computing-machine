from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.services.memory_engine import MemoryEngine
from backend.core.services.retrieval import multimodal_rag_enabled, search_with_backend
from backend.core.services.retrieval_jobs import JobStatus, RetrievalJobState

router = APIRouter()


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=8, ge=1, le=50)


class RetrievalSearchResponse(BaseModel):
    backend: str
    count: int
    results: list[dict[str, Any]]


class RetrievalIndexRequest(BaseModel):
    source_type: Literal["book", "file", "url", "manual"]
    source_ref: str = Field(..., min_length=1, max_length=4000)
    process_now: bool = True


class RetrievalIndexJobResponse(BaseModel):
    job_id: str
    source_type: str
    source_ref: str
    status: str
    created_at: float
    updated_at: float
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    attempts: int


class RetrievalJobsListResponse(BaseModel):
    items: list[RetrievalIndexJobResponse]
    count: int


class RetrievalProcessJobRequest(BaseModel):
    fail_reason: str | None = Field(default=None, max_length=4000)


@router.get("/health")
async def retrieval_health(req: Request):
    mm_retriever = getattr(req.app.state, "multimodal_retriever", None)
    return {
        "status": "healthy",
        "multimodal_flag": multimodal_rag_enabled(),
        "multimodal_injected": mm_retriever is not None,
    }


@router.post("/search", response_model=RetrievalSearchResponse)
async def retrieval_search(body: RetrievalSearchRequest, req: Request):
    memory_engine: MemoryEngine = req.app.state.memory_engine
    mm_retriever = getattr(req.app.state, "multimodal_retriever", None)

    results, backend = await search_with_backend(
        memory_engine=memory_engine,
        query_text=body.query,
        limit=body.limit,
        multimodal_retriever=mm_retriever,
    )

    return RetrievalSearchResponse(backend=backend, count=len(results), results=results)


@router.post("/index", response_model=RetrievalIndexJobResponse)
async def create_index_job(body: RetrievalIndexRequest, req: Request):
    job_state: RetrievalJobState = req.app.state.retrieval_job_state
    job = job_state.create_index_job(source_type=body.source_type, source_ref=body.source_ref)
    if body.process_now:
        job = job_state.process_job(job.job_id) or job
    return RetrievalIndexJobResponse(**job.__dict__)


@router.get("/jobs", response_model=RetrievalJobsListResponse)
async def list_index_jobs(req: Request, limit: int = 20, status: JobStatus | None = None):
    job_state: RetrievalJobState = req.app.state.retrieval_job_state
    jobs = job_state.list_jobs(limit=limit, status=status)
    items = [RetrievalIndexJobResponse(**job.__dict__) for job in jobs]
    return RetrievalJobsListResponse(items=items, count=len(items))


@router.get("/jobs/{job_id}", response_model=RetrievalIndexJobResponse)
async def get_index_job(job_id: str, req: Request):
    job_state: RetrievalJobState = req.app.state.retrieval_job_state
    job = job_state.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="index job not found")
    return RetrievalIndexJobResponse(**job.__dict__)


@router.post("/jobs/{job_id}/process", response_model=RetrievalIndexJobResponse)
async def process_index_job(job_id: str, body: RetrievalProcessJobRequest, req: Request):
    job_state: RetrievalJobState = req.app.state.retrieval_job_state
    job = job_state.process_job(job_id, fail_reason=body.fail_reason)
    if job is None:
        raise HTTPException(status_code=404, detail="index job not found")
    return RetrievalIndexJobResponse(**job.__dict__)
