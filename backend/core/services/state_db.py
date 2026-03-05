from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional, List, Dict, Any
import json
import time
import uuid


class StateDB:
    """Minimal companion.db foundation (Phase 1, non-breaking).

    В этой фазе БД инициализируется и хранится в app.state,
    но бизнес-логика ещё не переключена на SQLite.
    """

    def __init__(self, db_path: Optional[Path] = None):
        default_path = Path.home() / "roampal-android" / "data" / "companion.db"
        self.db_path = db_path or default_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA cache_size=-20000;")

            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    settings_json TEXT
                );

                CREATE TABLE IF NOT EXISTS runtime_settings (
                    user_id TEXT PRIMARY KEY,
                    max_wakes_per_day INTEGER NOT NULL DEFAULT 3,
                    cooldown_between_wakes_sec INTEGER NOT NULL DEFAULT 7200,
                    battery_deny_below_pct INTEGER NOT NULL DEFAULT 20,
                    temp_deny_above_c INTEGER NOT NULL DEFAULT 100,
                    memory_top_k INTEGER NOT NULL DEFAULT 12,
                    updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    updated_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    web_evidence_ids_json TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv_time
                    ON messages(conversation_id, created_at);

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending','running','done','failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    next_run_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
                    updated_at INTEGER,
                    last_error TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE (user_id, idempotency_key)
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_next_run
                    ON jobs(status, next_run_at);
                """
            )

            # Single-user bootstrap for Phase 1.
            conn.execute(
                "INSERT OR IGNORE INTO users(id, settings_json) VALUES (?, ?)",
                ("local-user", "{}"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO runtime_settings(user_id) VALUES (?)",
                ("local-user",),
            )
            conn.commit()
        finally:
            conn.close()

    def health(self) -> dict:
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            return {"ok": True, "path": str(self.db_path)}
        except Exception as e:
            return {"ok": False, "path": str(self.db_path), "error": str(e)}

    def enqueue_job(
        self,
        *,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        user_id: str = "local-user",
        max_attempts: int = 5,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = int(time.time())

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute(
                """
                INSERT INTO jobs (
                    id, user_id, type, payload_json, idempotency_key,
                    status, attempts, max_attempts, next_run_at, created_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
                """,
                (
                    job_id,
                    user_id,
                    job_type,
                    json.dumps(payload, ensure_ascii=False),
                    idempotency_key,
                    max_attempts,
                    now,
                    now,
                ),
            )
            conn.commit()
            return {
                "id": job_id,
                "user_id": user_id,
                "type": job_type,
                "status": "pending",
                "idempotency_key": idempotency_key,
                "created_at": now,
            }
        except sqlite3.IntegrityError:
            row = conn.execute(
                """
                SELECT id, user_id, type, status, idempotency_key, created_at
                FROM jobs
                WHERE user_id=? AND idempotency_key=?
                """,
                (user_id, idempotency_key),
            ).fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "type": row[2],
                    "status": row[3],
                    "idempotency_key": row[4],
                    "created_at": row[5],
                    "deduplicated": True,
                }
            raise
        finally:
            conn.close()

    def list_jobs(self, *, user_id: str = "local-user", limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(limit, 200))
        conn = sqlite3.connect(str(self.db_path))
        try:
            rows = conn.execute(
                """
                SELECT id, user_id, type, status, attempts, max_attempts, next_run_at, created_at, idempotency_key
                FROM jobs
                WHERE user_id=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "type": row[2],
                    "status": row[3],
                    "attempts": row[4],
                    "max_attempts": row[5],
                    "next_run_at": row[6],
                    "created_at": row[7],
                    "idempotency_key": row[8],
                }
                for row in rows
            ]
        finally:
            conn.close()
