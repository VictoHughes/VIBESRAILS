"""SQLite schema migrations for vibesrails MCP server.

Executed at server startup. Idempotent — safe to run multiple times.
Uses parameterized queries only. No ORM, pure sqlite3.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 3

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT,
            ai_tool TEXT,
            files_modified TEXT,
            total_changes_loc INTEGER DEFAULT 0,
            violations_count INTEGER DEFAULT 0,
            entropy_score REAL DEFAULT 0.0,
            project_path TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            timestamp TEXT NOT NULL,
            guard_name TEXT NOT NULL,
            file_path TEXT,
            severity TEXT,
            message TEXT,
            pedagogy_shown INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS drift_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            file_path TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metrics TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS package_cache (
            package_name TEXT NOT NULL,
            ecosystem TEXT NOT NULL,
            exists_flag INTEGER,
            api_surface TEXT,
            version TEXT,
            cached_at TEXT NOT NULL,
            PRIMARY KEY (package_name, ecosystem)
        )""",
    ],
    2: [
        """CREATE TABLE IF NOT EXISTS brief_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            brief_json TEXT NOT NULL,
            score INTEGER NOT NULL,
            level TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        """CREATE INDEX IF NOT EXISTS idx_brief_history_session
            ON brief_history (session_id)""",
    ],
    3: [
        """CREATE TABLE IF NOT EXISTS learning_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE INDEX IF NOT EXISTS idx_learning_events_type_date
            ON learning_events (event_type, created_at)""",
        """CREATE TABLE IF NOT EXISTS developer_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT UNIQUE NOT NULL,
            metric_value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""",
    ],
}

_META_SEED = "INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)"


def get_db_path() -> Path:
    """Return the default database path: ~/.vibesrails/sessions.db."""
    db_dir = Path.home() / ".vibesrails"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "sessions.db"


def get_current_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version from the meta table."""
    try:
        cursor = conn.execute(
            "SELECT value FROM meta WHERE key = ?", ("schema_version",)
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def migrate(db_path: str | Path | None = None) -> None:
    """Run all pending migrations. Idempotent — safe to call at every startup.

    Args:
        db_path: Path to the SQLite database. Defaults to ~/.vibesrails/sessions.db.
    """
    if db_path is None:
        db_path = get_db_path()

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        # WAL mode: allows concurrent reads during writes
        conn.execute("PRAGMA journal_mode=WAL")
        # Retry for 5s on lock contention instead of failing immediately
        conn.execute("PRAGMA busy_timeout=5000")

        current = get_current_version(conn)

        for version in sorted(MIGRATIONS.keys()):
            if version > current:
                for sql in MIGRATIONS[version]:
                    conn.execute(sql)
                conn.execute(_META_SEED, ("schema_version", str(version)))
                conn.execute(
                    "UPDATE meta SET value = ? WHERE key = ?",
                    (str(version), "schema_version"),
                )
        conn.commit()
    finally:
        conn.close()
