from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional


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
