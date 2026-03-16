from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.services.online_tools import download_to_local, online_tools_enabled, web_search

router = APIRouter()


class OnlineSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)


class OnlineSearchResponse(BaseModel):
    enabled: bool
    query: str
    results: list[dict]


class OnlineDownloadRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000)
    filename: str | None = Field(default=None, max_length=300)


class OnlineDownloadResponse(BaseModel):
    enabled: bool
    path: str
    filename: str
    size_bytes: int


def _assert_online_enabled() -> None:
    if not online_tools_enabled():
        raise HTTPException(
            status_code=403,
            detail="Online tools disabled. Set ENABLE_ONLINE_TOOLS=1 to enable internet search/download.",
        )


@router.get("/health")
async def online_health():
    return {"enabled": online_tools_enabled()}


@router.post("/search", response_model=OnlineSearchResponse)
async def online_search(body: OnlineSearchRequest):
    _assert_online_enabled()
    try:
        results = await web_search(body.query, limit=body.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"online search failed: {exc}")
    return OnlineSearchResponse(enabled=True, query=body.query, results=results)


@router.post("/download", response_model=OnlineDownloadResponse)
async def online_download(body: OnlineDownloadRequest):
    _assert_online_enabled()
    try:
        result = await download_to_local(url=body.url, filename=body.filename)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"download failed: {exc}")
    return OnlineDownloadResponse(enabled=True, **result)
