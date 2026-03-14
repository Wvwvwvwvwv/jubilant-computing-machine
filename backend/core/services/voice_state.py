from __future__ import annotations

from dataclasses import dataclass
import time
import uuid


@dataclass
class VoiceSession:
    voice_session_id: str
    mode: str
    stt_engine: str
    tts_engine: str
    status: str
    created_at: float
    updated_at: float


class VoiceState:
    """In-memory control-plane state for local voice sessions (MVP)."""

    def __init__(self):
        self.sessions: dict[str, VoiceSession] = {}

    def start_session(self, mode: str, stt_engine: str, tts_engine: str) -> VoiceSession:
        mode = mode.lower().strip()
        if mode not in {"ptt", "duplex"}:
            raise ValueError("unsupported voice mode")

        now = time.time()
        sid = f"vs_{uuid.uuid4().hex[:10]}"
        sess = VoiceSession(
            voice_session_id=sid,
            mode=mode,
            stt_engine=stt_engine.strip() or "local_whisper_cpp",
            tts_engine=tts_engine.strip() or "local_piper",
            status="ready",
            created_at=now,
            updated_at=now,
        )
        self.sessions[sid] = sess
        return sess

    def stop_session(self, voice_session_id: str) -> VoiceSession:
        sess = self.sessions.get(voice_session_id)
        if not sess:
            raise ValueError("voice session not found")
        sess.status = "stopped"
        sess.updated_at = time.time()
        return sess

    def get_session(self, voice_session_id: str) -> VoiceSession:
        sess = self.sessions.get(voice_session_id)
        if not sess:
            raise ValueError("voice session not found")
        return sess

    def health(self, voice_session_id: str) -> dict:
        sess = self.get_session(voice_session_id)
        if sess.status == "stopped":
            return {
                "status": "stopped",
                "input_device": "unknown",
                "stt": "stopped",
                "tts": "stopped",
                "latency_p95_ms": None,
                "xruns_per_min": None,
            }

        return {
            "status": "healthy",
            "input_device": "ok",
            "stt": "ok",
            "tts": "ok",
            "latency_p95_ms": 1700,
            "xruns_per_min": 0,
        }
