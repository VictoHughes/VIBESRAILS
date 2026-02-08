"""Security tests: SQL injection resistance.

Verifies that SQL injection payloads in user inputs don't corrupt
the database. All queries use parameterized statements.
"""

from __future__ import annotations

import sqlite3

from core.brief_enforcer import BriefEnforcer
from core.drift_tracker import DriftTracker
from core.learning_engine import LearningEngine
from core.session_tracker import SessionTracker

_SQLI_PAYLOAD = "'; DROP TABLE sessions; --"


def test_brief_enforcer_sqli_safe(tmp_path):
    """SQL injection in session_id doesn't drop tables."""
    db = str(tmp_path / "test.db")
    enforcer = BriefEnforcer(db_path=db)
    brief = {"intent": "Add a user login feature with OAuth2 support"}
    enforcer.store_brief(brief, 50, "minimal", session_id=_SQLI_PAYLOAD)

    # Table still exists and has data
    conn = sqlite3.connect(db)
    cursor = conn.execute("SELECT COUNT(*) FROM brief_history")
    assert cursor.fetchone()[0] >= 1
    conn.close()


def test_drift_tracker_sqli_safe(tmp_path):
    """SQL injection in session_id doesn't corrupt drift_snapshots."""
    db = str(tmp_path / "test.db")
    tracker = DriftTracker(db_path=db)

    # Create a minimal project dir to snapshot
    project = tmp_path / "proj"
    project.mkdir()
    (project / "main.py").write_text("x = 1")

    tracker.take_snapshot(str(project), session_id=_SQLI_PAYLOAD)

    conn = sqlite3.connect(db)
    cursor = conn.execute("SELECT COUNT(*) FROM drift_snapshots")
    assert cursor.fetchone()[0] >= 1
    conn.close()


def test_learning_engine_sqli_safe(tmp_path):
    """SQL injection in session_id doesn't corrupt learning_events."""
    db = str(tmp_path / "test.db")
    engine = LearningEngine(db_path=db)
    engine.record_event(_SQLI_PAYLOAD, "violation", {"guard_name": "test", "severity": "warn"})

    conn = sqlite3.connect(db)
    cursor = conn.execute("SELECT COUNT(*) FROM learning_events")
    assert cursor.fetchone()[0] >= 1
    conn.close()


def test_session_tracker_sqli_safe(tmp_path):
    """SQL injection in project_path doesn't corrupt sessions."""
    db = str(tmp_path / "test.db")
    tracker = SessionTracker(db_path=db)
    sid = tracker.start_session(_SQLI_PAYLOAD)

    conn = sqlite3.connect(db)
    cursor = conn.execute("SELECT COUNT(*) FROM sessions")
    assert cursor.fetchone()[0] >= 1
    conn.close()

    # End the session to verify it doesn't crash
    tracker.end_session(sid)
