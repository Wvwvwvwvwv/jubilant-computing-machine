from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Literal, Optional


ReasoningMode = Literal["stable", "wild"]
ChallengeMode = Literal["off", "balanced", "strict"]
InitiativeMode = Literal["off", "adaptive", "proactive"]
VoiceMode = Literal["off", "ptt", "duplex"]


@dataclass
class CompanionSession:
    session_id: str = "local_session"
    reasoning_mode: ReasoningMode = "stable"
    challenge_mode: ChallengeMode = "balanced"
    initiative_mode: InitiativeMode = "adaptive"
    voice_mode: VoiceMode = "off"
    updated_at: float = 0.0


@dataclass
class ResponseTrace:
    response_id: str
    reasoning_mode: ReasoningMode
    challenge_mode: ChallengeMode
    relationship_used: list[str]
    uncertainty_markers: list[str]
    counter_position_used: bool
    confidence: float
    ts: float


class CompanionState:
    """In-memory state holder for companion session and last response trace."""

    def __init__(self):
        now = time.time()
        self._session = CompanionSession(updated_at=now)
        self._last_trace: Optional[ResponseTrace] = None

    def get_session(self) -> CompanionSession:
        return self._session

    def update_session(
        self,
        reasoning_mode: Optional[ReasoningMode] = None,
        challenge_mode: Optional[ChallengeMode] = None,
        initiative_mode: Optional[InitiativeMode] = None,
        voice_mode: Optional[VoiceMode] = None,
    ) -> CompanionSession:
        if reasoning_mode is not None:
            self._session.reasoning_mode = reasoning_mode
        if challenge_mode is not None:
            self._session.challenge_mode = challenge_mode
        if initiative_mode is not None:
            self._session.initiative_mode = initiative_mode
        if voice_mode is not None:
            self._session.voice_mode = voice_mode
        self._session.updated_at = time.time()
        return self._session

    def get_last_trace(self) -> Optional[ResponseTrace]:
        return self._last_trace

    def set_last_trace(
        self,
        response_id: str,
        relationship_used: Optional[list[str]] = None,
        uncertainty_markers: Optional[list[str]] = None,
        counter_position_used: bool = False,
        confidence: float = 0.5,
    ) -> ResponseTrace:
        sess = self._session
        trace = ResponseTrace(
            response_id=response_id,
            reasoning_mode=sess.reasoning_mode,
            challenge_mode=sess.challenge_mode,
            relationship_used=relationship_used or [],
            uncertainty_markers=uncertainty_markers or [],
            counter_position_used=counter_position_used,
            confidence=max(0.0, min(1.0, float(confidence))),
            ts=time.time(),
        )
        self._last_trace = trace
        return trace
