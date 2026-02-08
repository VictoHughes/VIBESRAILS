"""Session Entropy Monitor — tracks AI coding session health.

Measures session entropy based on duration, files modified, violations,
and lines of code changed. Higher entropy = higher risk of AI hallucinations
and code quality degradation.

Persists session data in SQLite via storage/migrations.py schema.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

logger = logging.getLogger(__name__)

# ── Entropy levels ────────────────────────────────────────────────────

ENTROPY_LEVELS = {
    "safe": (0.0, 0.3),
    "warning": (0.3, 0.6),
    "elevated": (0.6, 0.8),
    "critical": (0.8, 1.0),
}


def classify_entropy(score: float) -> str:
    """Classify an entropy score into a level."""
    if score < 0.3:
        return "safe"
    if score < 0.6:
        return "warning"
    if score < 0.8:
        return "elevated"
    return "critical"


def calculate_entropy(
    duration_minutes: float,
    files_count: int,
    violations_count: int,
    total_loc: int,
) -> float:
    """Calculate session entropy score.

    Formula:
        entropy = duration_factor*0.3 + files_factor*0.2
                + violations_factor*0.3 + change_factor*0.2

    All factors are clamped to [0.0, 1.0].

    Returns:
        Float in [0.0, 1.0].
    """
    duration_factor = min(1.0, duration_minutes / 60)
    files_factor = min(1.0, files_count / 20)
    violations_factor = min(1.0, violations_count / 10)
    change_factor = min(1.0, total_loc / 500)

    return (
        duration_factor * 0.3
        + files_factor * 0.2
        + violations_factor * 0.3
        + change_factor * 0.2
    )


# ── SessionTracker ────────────────────────────────────────────────────


class SessionTracker:
    """Tracks AI coding sessions and computes entropy scores.

    Args:
        db_path: Path to SQLite database. Defaults to ~/.vibesrails/sessions.db.
    """

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = get_db_path()
        self._db_path = Path(db_path)
        # Ensure schema is ready
        migrate(self._db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), timeout=10)

    def start_session(
        self, project_path: str, ai_tool: str | None = None
    ) -> str:
        """Start a new session. Returns session_id (UUID)."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO sessions (id, start_time, ai_tool, files_modified, "
                "total_changes_loc, violations_count, entropy_score, project_path) "
                "VALUES (?, ?, ?, ?, 0, 0, 0.0, ?)",
                (session_id, now, ai_tool, json.dumps([]), project_path),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info("Session started: %s (project=%s, ai=%s)", session_id, project_path, ai_tool)
        return session_id

    def update_session(
        self,
        session_id: str,
        files_modified: list[str] | None = None,
        changes_loc: int = 0,
        violations: int = 0,
    ) -> float:
        """Update session metrics. Returns current entropy score.

        Raises:
            ValueError: If session_id not found.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT files_modified, total_changes_loc, violations_count, start_time "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            existing_files = json.loads(row[0]) if row[0] else []
            current_loc = row[1]
            current_violations = row[2]
            start_time = row[3]

            # Merge files (deduplicate)
            if files_modified:
                merged = list(set(existing_files + files_modified))
            else:
                merged = existing_files

            new_loc = current_loc + changes_loc
            new_violations = current_violations + violations

            # Calculate entropy
            start_dt = datetime.fromisoformat(start_time)
            now = datetime.now(timezone.utc)
            duration_minutes = (now - start_dt).total_seconds() / 60

            entropy = calculate_entropy(
                duration_minutes=duration_minutes,
                files_count=len(merged),
                violations_count=new_violations,
                total_loc=new_loc,
            )

            conn.execute(
                "UPDATE sessions SET files_modified = ?, total_changes_loc = ?, "
                "violations_count = ?, entropy_score = ? WHERE id = ?",
                (json.dumps(merged), new_loc, new_violations, entropy, session_id),
            )
            conn.commit()

            return entropy
        finally:
            conn.close()

    def get_entropy(self, session_id: str) -> float:
        """Get current entropy score for a session.

        Recalculates based on current time (duration keeps growing).

        Raises:
            ValueError: If session_id not found.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT start_time, files_modified, total_changes_loc, violations_count "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            start_dt = datetime.fromisoformat(row[0])
            files = json.loads(row[1]) if row[1] else []
            loc = row[2]
            violations = row[3]

            now = datetime.now(timezone.utc)
            duration_minutes = (now - start_dt).total_seconds() / 60

            return calculate_entropy(
                duration_minutes=duration_minutes,
                files_count=len(files),
                violations_count=violations,
                total_loc=loc,
            )
        finally:
            conn.close()

    def get_session(self, session_id: str) -> dict | None:
        """Get full session data. Returns None if not found."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, start_time, end_time, ai_tool, files_modified, "
                "total_changes_loc, violations_count, entropy_score, project_path "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                return None

            start_dt = datetime.fromisoformat(row[1])
            now = datetime.now(timezone.utc)
            duration_minutes = (now - start_dt).total_seconds() / 60

            return {
                "session_id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "ai_tool": row[3],
                "files_modified": json.loads(row[4]) if row[4] else [],
                "total_changes_loc": row[5],
                "violations_count": row[6],
                "entropy_score": row[7],
                "project_path": row[8],
                "duration_minutes": round(duration_minutes, 1),
            }
        finally:
            conn.close()

    def end_session(self, session_id: str) -> dict:
        """End a session. Returns session summary.

        Raises:
            ValueError: If session_id not found.
        """
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT start_time, files_modified, total_changes_loc, violations_count "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Session not found: {session_id}")

            start_dt = datetime.fromisoformat(row[0])
            now = datetime.now(timezone.utc)
            duration_minutes = (now - start_dt).total_seconds() / 60
            files = json.loads(row[1]) if row[1] else []
            loc = row[2]
            violations = row[3]

            final_entropy = calculate_entropy(
                duration_minutes=duration_minutes,
                files_count=len(files),
                violations_count=violations,
                total_loc=loc,
            )

            conn.execute(
                "UPDATE sessions SET end_time = ?, entropy_score = ? WHERE id = ?",
                (now.isoformat(), final_entropy, session_id),
            )
            conn.commit()

            return {
                "session_id": session_id,
                "duration_minutes": round(duration_minutes, 1),
                "files_modified": files,
                "total_changes_loc": loc,
                "violations_count": violations,
                "final_entropy": round(final_entropy, 4),
                "entropy_level": classify_entropy(final_entropy),
            }
        finally:
            conn.close()
