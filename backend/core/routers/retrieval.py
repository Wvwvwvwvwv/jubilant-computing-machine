from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.core.services.memory_engine import MemoryEngine
from backend.core.services.retrieval import multimodal_rag_enabled, search_with_backend

router = APIRouter()


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    limit: int = Field(default=8, ge=1, le=50)


class RetrievalSearchResponse(BaseModel):
    backend: str
    count: int
    results: list[dict[str, Any]]


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
