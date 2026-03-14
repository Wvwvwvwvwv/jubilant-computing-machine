from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
import time
import uuid
from typing import Optional


@dataclass
class RelationshipProfile:
    user_id: str
    verbosity: str
    tone: str
    language: str
    allow_disagreement: bool
    disagreement_strictness: str
    allow_proactive_suggestions: bool
    max_unsolicited_per_hour: int
    created_at: float
    updated_at: float
    version: int


@dataclass
class RelationshipFact:
    fact_id: str
    user_id: str
    fact: str
    confidence: float
    source_type: str
    source_ref_id: Optional[str]
    status: str
    ttl_days: Optional[int]
    created_at: float
    updated_at: float


@dataclass
class InitiativeProposal:
    proposal_id: str
    user_id: str
    text: str
    reason: str
    expected_value: str
    risk_level: str
    stop_condition: str
    unsolicited: bool
    status: str
    created_at: float
    updated_at: float




@dataclass
class InitiativeProposalEvent:
    ts: float
    event_kind: str
    payload: dict

class CompanionMemory:
    def __init__(self):
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = logs_dir / "companion.db"
        self._init_db()
        self._ensure_default_profile()

    def _db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._db() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relationship_profiles (
                  user_id TEXT PRIMARY KEY,
                  verbosity TEXT NOT NULL DEFAULT 'medium',
                  tone TEXT NOT NULL DEFAULT 'direct',
                  language TEXT NOT NULL DEFAULT 'ru',
                  allow_disagreement INTEGER NOT NULL DEFAULT 1,
                  disagreement_strictness TEXT NOT NULL DEFAULT 'balanced',
                  allow_proactive_suggestions INTEGER NOT NULL DEFAULT 1,
                  max_unsolicited_per_hour INTEGER NOT NULL DEFAULT 3,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  version INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relationship_facts (
                  fact_id TEXT PRIMARY KEY,
                  user_id TEXT NOT NULL,
                  fact TEXT NOT NULL,
                  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
                  source_type TEXT NOT NULL,
                  source_ref_id TEXT,
                  status TEXT NOT NULL DEFAULT 'active',
                  ttl_days INTEGER,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES relationship_profiles(user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relationship_fact_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fact_id TEXT NOT NULL,
                  event_kind TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  ts REAL NOT NULL,
                  FOREIGN KEY(fact_id) REFERENCES relationship_facts(fact_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS initiative_proposals (
                  proposal_id TEXT PRIMARY KEY,
                  user_id TEXT NOT NULL,
                  text TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  expected_value TEXT NOT NULL,
                  risk_level TEXT NOT NULL,
                  stop_condition TEXT NOT NULL,
                  unsolicited INTEGER NOT NULL DEFAULT 0,
                  status TEXT NOT NULL DEFAULT 'open',
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES relationship_profiles(user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS initiative_proposal_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  proposal_id TEXT NOT NULL,
                  event_kind TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  ts REAL NOT NULL,
                  FOREIGN KEY(proposal_id) REFERENCES initiative_proposals(proposal_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relationship_facts_user_status
                ON relationship_facts(user_id, status)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relationship_fact_events_fact
                ON relationship_fact_events(fact_id, id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_initiative_proposals_user_status
                ON initiative_proposals(user_id, status, created_at)
                """
            )

    def _ensure_default_profile(self):
        now = time.time()
        with self._db() as conn:
            row = conn.execute("SELECT user_id FROM relationship_profiles WHERE user_id=?", ("local_user",)).fetchone()
            if row:
                return
            conn.execute(
                """
                INSERT INTO relationship_profiles (
                  user_id, verbosity, tone, language,
                  allow_disagreement, disagreement_strictness,
                  allow_proactive_suggestions, max_unsolicited_per_hour,
                  created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "local_user",
                    "medium",
                    "direct",
                    "ru",
                    1,
                    "balanced",
                    1,
                    3,
                    now,
                    now,
                    1,
                ),
            )

    def get_profile(self, user_id: str = "local_user") -> RelationshipProfile:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM relationship_profiles WHERE user_id=?", (user_id,)).fetchone()
            if not row:
                raise ValueError("profile not found")
            return RelationshipProfile(
                user_id=row["user_id"],
                verbosity=row["verbosity"],
                tone=row["tone"],
                language=row["language"],
                allow_disagreement=bool(row["allow_disagreement"]),
                disagreement_strictness=row["disagreement_strictness"],
                allow_proactive_suggestions=bool(row["allow_proactive_suggestions"]),
                max_unsolicited_per_hour=int(row["max_unsolicited_per_hour"]),
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
                version=int(row["version"]),
            )

    def patch_profile(self, patch: dict, user_id: str = "local_user") -> RelationshipProfile:
        current = self.get_profile(user_id)
        style = patch.get("style", {})
        debate = patch.get("debate_preferences", {})
        initiative = patch.get("initiative_preferences", {})

        verbosity = style.get("verbosity", current.verbosity)
        tone = style.get("tone", current.tone)
        language = style.get("language", current.language)
        allow_disagreement = debate.get("allow_disagreement", current.allow_disagreement)
        disagreement_strictness = debate.get("strictness", current.disagreement_strictness)
        allow_proactive_suggestions = initiative.get(
            "allow_proactive_suggestions", current.allow_proactive_suggestions
        )
        max_unsolicited_per_hour = initiative.get(
            "max_unsolicited_per_hour", current.max_unsolicited_per_hour
        )
        now = time.time()

        with self._db() as conn:
            conn.execute(
                """
                UPDATE relationship_profiles
                SET verbosity=?, tone=?, language=?,
                    allow_disagreement=?, disagreement_strictness=?,
                    allow_proactive_suggestions=?, max_unsolicited_per_hour=?,
                    updated_at=?, version=version+1
                WHERE user_id=?
                """,
                (
                    verbosity,
                    tone,
                    language,
                    1 if allow_disagreement else 0,
                    disagreement_strictness,
                    1 if allow_proactive_suggestions else 0,
                    int(max_unsolicited_per_hour),
                    now,
                    user_id,
                ),
            )

        return self.get_profile(user_id)

    def add_fact(
        self,
        fact: str,
        source_type: str,
        source_ref_id: Optional[str],
        confidence: float,
        ttl_days: Optional[int],
        user_id: str = "local_user",
    ) -> RelationshipFact:
        now = time.time()
        fact_id = f"rf_{uuid.uuid4().hex[:12]}"
        confidence = max(0.0, min(1.0, float(confidence)))
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO relationship_facts (
                  fact_id, user_id, fact, confidence, source_type, source_ref_id,
                  status, ttl_days, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (fact_id, user_id, fact, confidence, source_type, source_ref_id, ttl_days, now, now),
            )
            conn.execute(
                """
                INSERT INTO relationship_fact_events (fact_id, event_kind, payload_json, ts)
                VALUES (?, 'created', ?, ?)
                """,
                (fact_id, json.dumps({"fact": fact, "confidence": confidence}, ensure_ascii=False), now),
            )
        return self.get_fact(fact_id)

    def get_fact(self, fact_id: str) -> RelationshipFact:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM relationship_facts WHERE fact_id=?", (fact_id,)).fetchone()
            if not row:
                raise ValueError("fact not found")
            return RelationshipFact(
                fact_id=row["fact_id"],
                user_id=row["user_id"],
                fact=row["fact"],
                confidence=float(row["confidence"]),
                source_type=row["source_type"],
                source_ref_id=row["source_ref_id"],
                status=row["status"],
                ttl_days=row["ttl_days"],
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )

    def list_facts(self, query: str = "", limit: int = 20, user_id: str = "local_user") -> list[RelationshipFact]:
        q = (query or "").strip()
        limit = max(1, min(int(limit), 200))
        with self._db() as conn:
            if q:
                rows = conn.execute(
                    """
                    SELECT * FROM relationship_facts
                    WHERE user_id=? AND status='active' AND fact LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (user_id, f"%{q}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM relationship_facts
                    WHERE user_id=? AND status='active'
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()

        return [
            RelationshipFact(
                fact_id=row["fact_id"],
                user_id=row["user_id"],
                fact=row["fact"],
                confidence=float(row["confidence"]),
                source_type=row["source_type"],
                source_ref_id=row["source_ref_id"],
                status=row["status"],
                ttl_days=row["ttl_days"],
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )
            for row in rows
        ]

    def invalidate_fact(self, fact_id: str) -> RelationshipFact:
        now = time.time()
        with self._db() as conn:
            row = conn.execute("SELECT fact_id FROM relationship_facts WHERE fact_id=?", (fact_id,)).fetchone()
            if not row:
                raise ValueError("fact not found")
            conn.execute(
                "UPDATE relationship_facts SET status='invalidated', updated_at=? WHERE fact_id=?",
                (now, fact_id),
            )
            conn.execute(
                """
                INSERT INTO relationship_fact_events (fact_id, event_kind, payload_json, ts)
                VALUES (?, 'invalidated', ?, ?)
                """,
                (fact_id, json.dumps({"reason": "manual"}, ensure_ascii=False), now),
            )
        return self.get_fact(fact_id)

    def _recent_unsolicited_count(self, user_id: str = "local_user", window_s: int = 3600) -> int:
        since = time.time() - window_s
        with self._db() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM initiative_proposals
                WHERE user_id=? AND unsolicited=1 AND created_at>=? AND status IN ('open','accepted')
                """,
                (user_id, since),
            ).fetchone()
            return int(row["c"]) if row else 0

    def add_proposal(
        self,
        text: str,
        reason: str,
        expected_value: str,
        risk_level: str,
        stop_condition: str,
        unsolicited: bool,
        user_id: str = "local_user",
    ) -> InitiativeProposal:
        profile = self.get_profile(user_id)
        if unsolicited and not profile.allow_proactive_suggestions:
            raise ValueError("proactive suggestions disabled by profile")
        if unsolicited and self._recent_unsolicited_count(user_id=user_id) >= profile.max_unsolicited_per_hour:
            raise ValueError("unsolicited proposal rate limit exceeded")

        now = time.time()
        proposal_id = f"pr_{uuid.uuid4().hex[:12]}"
        risk_level = (risk_level or "medium").lower()
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"

        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO initiative_proposals (
                  proposal_id, user_id, text, reason, expected_value, risk_level,
                  stop_condition, unsolicited, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    proposal_id,
                    user_id,
                    text,
                    reason,
                    expected_value,
                    risk_level,
                    stop_condition,
                    1 if unsolicited else 0,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO initiative_proposal_events (proposal_id, event_kind, payload_json, ts)
                VALUES (?, 'created', ?, ?)
                """,
                (
                    proposal_id,
                    json.dumps(
                        {
                            "unsolicited": unsolicited,
                            "risk_level": risk_level,
                            "expected_value": expected_value,
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> InitiativeProposal:
        with self._db() as conn:
            row = conn.execute("SELECT * FROM initiative_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                raise ValueError("proposal not found")
            return InitiativeProposal(
                proposal_id=row["proposal_id"],
                user_id=row["user_id"],
                text=row["text"],
                reason=row["reason"],
                expected_value=row["expected_value"],
                risk_level=row["risk_level"],
                stop_condition=row["stop_condition"],
                unsolicited=bool(row["unsolicited"]),
                status=row["status"],
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )

    def list_proposals(self, status: str = "open", limit: int = 20, user_id: str = "local_user") -> list[InitiativeProposal]:
        limit = max(1, min(int(limit), 200))
        with self._db() as conn:
            if status == "all":
                rows = conn.execute(
                    "SELECT * FROM initiative_proposals WHERE user_id=? ORDER BY updated_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM initiative_proposals
                    WHERE user_id=? AND status=?
                    ORDER BY updated_at DESC LIMIT ?
                    """,
                    (user_id, status, limit),
                ).fetchall()

        return [
            InitiativeProposal(
                proposal_id=row["proposal_id"],
                user_id=row["user_id"],
                text=row["text"],
                reason=row["reason"],
                expected_value=row["expected_value"],
                risk_level=row["risk_level"],
                stop_condition=row["stop_condition"],
                unsolicited=bool(row["unsolicited"]),
                status=row["status"],
                created_at=float(row["created_at"]),
                updated_at=float(row["updated_at"]),
            )
            for row in rows
        ]

    def update_proposal_status(self, proposal_id: str, status: str) -> InitiativeProposal:
        status = status.lower()
        if status not in {"accepted", "dismissed", "open"}:
            raise ValueError("unsupported proposal status")
        now = time.time()
        with self._db() as conn:
            row = conn.execute("SELECT proposal_id FROM initiative_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                raise ValueError("proposal not found")
            conn.execute(
                "UPDATE initiative_proposals SET status=?, updated_at=? WHERE proposal_id=?",
                (status, now, proposal_id),
            )
            conn.execute(
                """
                INSERT INTO initiative_proposal_events (proposal_id, event_kind, payload_json, ts)
                VALUES (?, ?, ?, ?)
                """,
                (proposal_id, f"status_{status}", json.dumps({"status": status}, ensure_ascii=False), now),
            )

        return self.get_proposal(proposal_id)


    def list_proposal_events(self, proposal_id: str, limit: int = 50) -> list[InitiativeProposalEvent]:
        limit = max(1, min(int(limit), 500))
        with self._db() as conn:
            row = conn.execute("SELECT proposal_id FROM initiative_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                raise ValueError("proposal not found")
            rows = conn.execute(
                """
                SELECT ts, event_kind, payload_json
                FROM initiative_proposal_events
                WHERE proposal_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (proposal_id, limit),
            ).fetchall()

        events: list[InitiativeProposalEvent] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                payload = {}
            events.append(
                InitiativeProposalEvent(
                    ts=float(row["ts"]),
                    event_kind=row["event_kind"],
                    payload=payload,
                )
            )

        events.reverse()
        return events
