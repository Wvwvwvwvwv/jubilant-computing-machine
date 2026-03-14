from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.services.voice_state import VoiceState

router = APIRouter()


class VoiceSessionStartRequest(BaseModel):
    mode: str = Field("ptt")
    stt_engine: str = Field("local_whisper_cpp")
    tts_engine: str = Field("local_piper")


class VoiceSessionResponse(BaseModel):
    voice_session_id: str
    mode: str
    status: str


class VoiceSessionHealthResponse(BaseModel):
    status: str
    mode: str
    stt_engine: str
    tts_engine: str
    input_device: str
    stt: str
    tts: str
    latency_p95_ms: int | None = None
    xruns_per_min: int | None = None


class VoiceMetricsUpdateRequest(BaseModel):
    latency_p95_ms: int | None = Field(default=None, ge=0, le=120000)
    xruns_per_min: int | None = Field(default=None, ge=0, le=10000)
    crash_free_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    audio_loss_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    approval_bypass_incidents: int | None = Field(default=None, ge=0, le=100000)
    user_score: float | None = Field(default=None, ge=0.0, le=5.0)


class VoiceGoNoGoResponse(BaseModel):
    voice_session_id: str
    decision: str
    checks: dict
    failed_checks: list[str]
    metrics: dict


@router.post("/session/start", response_model=VoiceSessionResponse)
async def start_voice_session(body: VoiceSessionStartRequest, req: Request):
    state: VoiceState = req.app.state.voice_state
    try:
        sess = state.start_session(mode=body.mode, stt_engine=body.stt_engine, tts_engine=body.tts_engine)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return VoiceSessionResponse(voice_session_id=sess.voice_session_id, mode=sess.mode, status=sess.status)


@router.post("/session/{voice_session_id}/stop", response_model=VoiceSessionResponse)
async def stop_voice_session(voice_session_id: str, req: Request):
    state: VoiceState = req.app.state.voice_state
    try:
        sess = state.stop_session(voice_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return VoiceSessionResponse(voice_session_id=sess.voice_session_id, mode=sess.mode, status=sess.status)


@router.get("/session/{voice_session_id}/health", response_model=VoiceSessionHealthResponse)
async def health_voice_session(voice_session_id: str, req: Request):
    state: VoiceState = req.app.state.voice_state
    try:
        health = state.health(voice_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return VoiceSessionHealthResponse(**health)


@router.patch("/session/{voice_session_id}/metrics", response_model=VoiceSessionResponse)
async def update_voice_metrics(voice_session_id: str, body: VoiceMetricsUpdateRequest, req: Request):
    state: VoiceState = req.app.state.voice_state
    try:
        sess = state.update_metrics(voice_session_id=voice_session_id, **body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return VoiceSessionResponse(voice_session_id=sess.voice_session_id, mode=sess.mode, status=sess.status)


@router.get("/session/{voice_session_id}/go-no-go", response_model=VoiceGoNoGoResponse)
async def go_no_go_voice_session(voice_session_id: str, req: Request):
    state: VoiceState = req.app.state.voice_state
    try:
        decision = state.go_no_go(voice_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return VoiceGoNoGoResponse(**decision)
