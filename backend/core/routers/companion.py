from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.core.services.companion_memory import CompanionMemory
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


class StylePatch(BaseModel):
    verbosity: Optional[str] = None
    tone: Optional[str] = None
    language: Optional[str] = None


class DebatePreferencesPatch(BaseModel):
    allow_disagreement: Optional[bool] = None
    strictness: Optional[str] = None


class InitiativePreferencesPatch(BaseModel):
    allow_proactive_suggestions: Optional[bool] = None
    max_unsolicited_per_hour: Optional[int] = Field(default=None, ge=0, le=1000)


class RelationshipProfilePatchRequest(BaseModel):
    style: Optional[StylePatch] = None
    debate_preferences: Optional[DebatePreferencesPatch] = None
    initiative_preferences: Optional[InitiativePreferencesPatch] = None


class RelationshipProfileResponse(BaseModel):
    user_id: str
    style: dict
    debate_preferences: dict
    initiative_preferences: dict
    created_at: float
    updated_at: float
    version: int


class RelationshipFactSource(BaseModel):
    type: str
    ref_id: Optional[str] = None


class RelationshipFactCreateRequest(BaseModel):
    fact: str = Field(..., min_length=3, max_length=4000)
    source: RelationshipFactSource
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    ttl_days: Optional[int] = Field(default=None, ge=1, le=3650)


class RelationshipFactResponse(BaseModel):
    fact_id: str
    fact: str
    confidence: float
    source: dict
    status: str
    created_at: float
    updated_at: float


class RelationshipFactsListResponse(BaseModel):
    items: list[RelationshipFactResponse]
    count: int


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


def _profile_to_response(profile) -> RelationshipProfileResponse:
    return RelationshipProfileResponse(
        user_id=profile.user_id,
        style={
            "verbosity": profile.verbosity,
            "tone": profile.tone,
            "language": profile.language,
        },
        debate_preferences={
            "allow_disagreement": profile.allow_disagreement,
            "strictness": profile.disagreement_strictness,
        },
        initiative_preferences={
            "allow_proactive_suggestions": profile.allow_proactive_suggestions,
            "max_unsolicited_per_hour": profile.max_unsolicited_per_hour,
        },
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        version=profile.version,
    )


def _fact_to_response(fact) -> RelationshipFactResponse:
    return RelationshipFactResponse(
        fact_id=fact.fact_id,
        fact=fact.fact,
        confidence=fact.confidence,
        source={"type": fact.source_type, "ref_id": fact.source_ref_id},
        status=fact.status,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


@router.get("/relationship-profile", response_model=RelationshipProfileResponse)
async def get_relationship_profile(req: Request):
    memory: CompanionMemory = req.app.state.companion_memory
    return _profile_to_response(memory.get_profile())


@router.patch("/relationship-profile", response_model=RelationshipProfileResponse)
async def patch_relationship_profile(body: RelationshipProfilePatchRequest, req: Request):
    memory: CompanionMemory = req.app.state.companion_memory
    payload = body.model_dump(exclude_none=True)
    updated = memory.patch_profile(payload)
    return _profile_to_response(updated)


@router.post("/relationship-facts", response_model=RelationshipFactResponse)
async def create_relationship_fact(body: RelationshipFactCreateRequest, req: Request):
    memory: CompanionMemory = req.app.state.companion_memory
    created = memory.add_fact(
        fact=body.fact,
        source_type=body.source.type,
        source_ref_id=body.source.ref_id,
        confidence=body.confidence,
        ttl_days=body.ttl_days,
    )
    return _fact_to_response(created)


@router.get("/relationship-facts", response_model=RelationshipFactsListResponse)
async def list_relationship_facts(req: Request, query: str = "", limit: int = 20):
    memory: CompanionMemory = req.app.state.companion_memory
    items = memory.list_facts(query=query, limit=limit)
    mapped = [_fact_to_response(x) for x in items]
    return RelationshipFactsListResponse(items=mapped, count=len(mapped))


@router.post("/relationship-facts/{fact_id}/invalidate", response_model=RelationshipFactResponse)
async def invalidate_relationship_fact(fact_id: str, req: Request):
    memory: CompanionMemory = req.app.state.companion_memory
    updated = memory.invalidate_fact(fact_id)
    return _fact_to_response(updated)
