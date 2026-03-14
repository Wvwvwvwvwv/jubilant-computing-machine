from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.services.companion_state import (
    ChallengeMode,
    CompanionState,
    InitiativeMode,
    ReasoningMode,
    VoiceMode,
)

router = APIRouter()


class CompanionSessionResponse(BaseModel):
    session_id: str
    reasoning_mode: ReasoningMode
    challenge_mode: ChallengeMode
    initiative_mode: InitiativeMode
    voice_mode: VoiceMode
    updated_at: float


class CompanionSessionPatchRequest(BaseModel):
    reasoning_mode: Optional[ReasoningMode] = None
    challenge_mode: Optional[ChallengeMode] = None
    initiative_mode: Optional[InitiativeMode] = None
    voice_mode: Optional[VoiceMode] = None


class LastResponseTraceResponse(BaseModel):
    response_id: str
    reasoning_mode: ReasoningMode
    challenge_mode: ChallengeMode
    relationship_used: list[str]
    uncertainty_markers: list[str]
    counter_position_used: bool
    confidence: float
    ts: float


@router.get("/session", response_model=CompanionSessionResponse)
async def get_session(req: Request):
    state: CompanionState = req.app.state.companion_state
    session = state.get_session()
    return CompanionSessionResponse(**session.__dict__)


@router.patch("/session", response_model=CompanionSessionResponse)
async def patch_session(body: CompanionSessionPatchRequest, req: Request):
    state: CompanionState = req.app.state.companion_state
    session = state.update_session(
        reasoning_mode=body.reasoning_mode,
        challenge_mode=body.challenge_mode,
        initiative_mode=body.initiative_mode,
        voice_mode=body.voice_mode,
    )
    return CompanionSessionResponse(**session.__dict__)


@router.get("/last-response-trace", response_model=Optional[LastResponseTraceResponse])
async def get_last_response_trace(req: Request):
    state: CompanionState = req.app.state.companion_state
    trace = state.get_last_trace()
    if trace is None:
        return None
    return LastResponseTraceResponse(**trace.__dict__)
