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

    # observed metrics for go/no-go assessment
    latency_p95_ms: int | None = 1700
    xruns_per_min: int | None = 0
    crash_free_rate: float = 1.0
    audio_loss_percent: float = 0.0
    approval_bypass_incidents: int = 0
    user_score: float = 4.5


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

    def update_metrics(
        self,
        voice_session_id: str,
        latency_p95_ms: int | None = None,
        xruns_per_min: int | None = None,
        crash_free_rate: float | None = None,
        audio_loss_percent: float | None = None,
        approval_bypass_incidents: int | None = None,
        user_score: float | None = None,
    ) -> VoiceSession:
        sess = self.get_session(voice_session_id)
        if latency_p95_ms is not None:
            sess.latency_p95_ms = int(latency_p95_ms)
        if xruns_per_min is not None:
            sess.xruns_per_min = int(xruns_per_min)
        if crash_free_rate is not None:
            sess.crash_free_rate = float(crash_free_rate)
        if audio_loss_percent is not None:
            sess.audio_loss_percent = float(audio_loss_percent)
        if approval_bypass_incidents is not None:
            sess.approval_bypass_incidents = int(approval_bypass_incidents)
        if user_score is not None:
            sess.user_score = float(user_score)
        sess.updated_at = time.time()
        return sess

    def health(self, voice_session_id: str) -> dict:
        sess = self.get_session(voice_session_id)
        if sess.status == "stopped":
            return {
                "status": "stopped",
                "mode": sess.mode,
                "stt_engine": sess.stt_engine,
                "tts_engine": sess.tts_engine,
                "input_device": "unknown",
                "stt": "stopped",
                "tts": "stopped",
                "latency_p95_ms": None,
                "xruns_per_min": None,
            }

        return {
            "status": "healthy",
            "mode": sess.mode,
            "stt_engine": sess.stt_engine,
            "tts_engine": sess.tts_engine,
            "input_device": "ok",
            "stt": "ok",
            "tts": "ok",
            "latency_p95_ms": sess.latency_p95_ms,
            "xruns_per_min": sess.xruns_per_min,
        }

    def go_no_go(self, voice_session_id: str) -> dict:
        sess = self.get_session(voice_session_id)

        checks: dict[str, bool] = {
            "latency_p95_ms_le_2500": sess.latency_p95_ms is not None and sess.latency_p95_ms <= 2500,
            "crash_free_rate_ge_0_99": sess.crash_free_rate >= 0.99,
            "audio_loss_percent_le_2": sess.audio_loss_percent <= 2.0,
            "approval_bypass_incidents_eq_0": sess.approval_bypass_incidents == 0,
            "user_score_ge_4": sess.user_score >= 4.0,
        }

        failed = [k for k, ok in checks.items() if not ok]
        decision = "GO" if not failed else "NO_GO"
        return {
            "voice_session_id": sess.voice_session_id,
            "decision": decision,
            "checks": checks,
            "failed_checks": failed,
            "metrics": {
                "latency_p95_ms": sess.latency_p95_ms,
                "xruns_per_min": sess.xruns_per_min,
                "crash_free_rate": sess.crash_free_rate,
                "audio_loss_percent": sess.audio_loss_percent,
                "approval_bypass_incidents": sess.approval_bypass_incidents,
                "user_score": sess.user_score,
            },
        }
