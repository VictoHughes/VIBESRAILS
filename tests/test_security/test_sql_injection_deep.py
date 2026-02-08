"""Deep SQL injection tests for every SQLite-writing module.

Tests multiple injection payloads against every module that writes to
SQLite, then verifies ALL tables survive intact.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from core.brief_enforcer import BriefEnforcer
from core.drift_tracker import DriftTracker
from core.hallucination_deep import DeepHallucinationChecker
from core.learning_engine import LearningEngine
from core.session_tracker import SessionTracker

# ── Injection payloads ───────────────────────────────────────────────

SQLI_DROP = "'; DROP TABLE sessions; --"
SQLI_OR = '" OR 1=1 --'
SQLI_BOBBY = "Robert'); DROP TABLE learning_events;--"
SQLI_UNION = "' UNION SELECT * FROM meta; --"

ALL_PAYLOADS = [SQLI_DROP, SQLI_OR, SQLI_BOBBY, SQLI_UNION]

# Expected tables after schema V3 migration
EXPECTED_TABLES = {
    "meta",
    "sessions",
    "violations",
    "drift_snapshots",
    "package_cache",
    "brief_history",
    "learning_events",
    "developer_profile",
}


def _assert_all_tables_exist(db_path: str) -> None:
    """Assert that every expected table still exists in the database."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        actual = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()
    missing = EXPECTED_TABLES - actual
    assert not missing, f"Tables destroyed by injection: {missing}"


# ── SessionTracker ───────────────────────────────────────────────────


class TestSessionTrackerSQLi:
    """SQL injection tests for session_tracker (sessions table)."""

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_start_session_with_sqli_project_path(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session(payload)
        assert sid  # Got a valid UUID back
        _assert_all_tables_exist(db)

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_update_session_with_sqli_files(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")
        tracker.update_session(sid, files_modified=[payload], changes_loc=10)
        _assert_all_tables_exist(db)
        # Verify the data was stored (not interpreted as SQL)
        session = tracker.get_session(sid)
        assert payload in session["files_modified"]


# ── DriftTracker ─────────────────────────────────────────────────────


class TestDriftTrackerSQLi:
    """SQL injection tests for drift_tracker (drift_snapshots table)."""

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_take_snapshot_with_sqli_session_id(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        tracker = DriftTracker(db_path=db)
        project = tmp_path / "proj"
        project.mkdir()
        (project / "app.py").write_text("x = 1")
        tracker.take_snapshot(str(project), session_id=payload)
        _assert_all_tables_exist(db)
        # Verify stored correctly
        conn = sqlite3.connect(db)
        try:
            row = conn.execute(
                "SELECT session_id FROM drift_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert row[0] == payload
        finally:
            conn.close()


# ── BriefEnforcer ────────────────────────────────────────────────────


class TestBriefEnforcerSQLi:
    """SQL injection tests for brief_enforcer (brief_history table)."""

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_store_brief_with_sqli_session_id(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        enforcer = BriefEnforcer(db_path=db)
        brief = {"intent": "Add user authentication with OAuth2 support"}
        enforcer.store_brief(brief, 50, "minimal", session_id=payload)
        _assert_all_tables_exist(db)

    def test_store_brief_with_sqli_in_brief_json(self, tmp_path):
        """Injection in brief dict values (serialized as JSON)."""
        db = str(tmp_path / "test.db")
        enforcer = BriefEnforcer(db_path=db)
        evil_brief = {"intent": SQLI_DROP, "constraints": [SQLI_BOBBY]}
        enforcer.store_brief(evil_brief, 30, "insufficient")
        _assert_all_tables_exist(db)
        # Verify the data round-trips correctly
        history = enforcer.get_history()
        assert len(history) >= 1
        assert history[-1]["brief"]["intent"] == SQLI_DROP


# ── LearningEngine ──────────────────────────────────────────────────


class TestLearningEngineSQLi:
    """SQL injection tests for learning_engine (learning_events + developer_profile)."""

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_record_event_with_sqli_session_id(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        engine = LearningEngine(db_path=db)
        engine.record_event(payload, "violation", {"guard_name": "test", "severity": "warn"})
        _assert_all_tables_exist(db)

    def test_record_event_with_sqli_event_data_keys(self, tmp_path):
        """Malicious JSON keys in event_data."""
        db = str(tmp_path / "test.db")
        engine = LearningEngine(db_path=db)
        evil_data = {
            SQLI_DROP: "value",
            "nested": {SQLI_BOBBY: SQLI_OR},
        }
        engine.record_event("session-1", "violation", evil_data)
        _assert_all_tables_exist(db)
        # Verify stored as JSON, not executed
        conn = sqlite3.connect(db)
        try:
            row = conn.execute(
                "SELECT event_data FROM learning_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            stored = json.loads(row[0])
            assert SQLI_DROP in stored
        finally:
            conn.close()

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_get_session_summary_with_sqli(self, tmp_path, payload):
        """session_summary queries with injection payloads don't crash."""
        db = str(tmp_path / "test.db")
        engine = LearningEngine(db_path=db)
        summary = engine.get_session_summary(payload)
        assert summary["events_count"] == 0
        _assert_all_tables_exist(db)


# ── HallucinationDeep ───────────────────────────────────────────────


class TestHallucinationDeepSQLi:
    """SQL injection tests for hallucination_deep (package_cache table)."""

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_set_cache_with_sqli_package_name(self, tmp_path, payload):
        db = str(tmp_path / "test.db")
        checker = DeepHallucinationChecker(db_path=db)
        checker._set_cache(payload, "pypi", True)
        _assert_all_tables_exist(db)
        # Verify stored literally
        conn = sqlite3.connect(db)
        try:
            row = conn.execute(
                "SELECT package_name FROM package_cache WHERE package_name = ?",
                (payload.lower(),),
            ).fetchone()
            assert row is not None
        finally:
            conn.close()

    @pytest.mark.parametrize("payload", ALL_PAYLOADS)
    def test_get_cache_with_sqli_package_name(self, tmp_path, payload):
        """Cache lookup with injection payload doesn't crash."""
        db = str(tmp_path / "test.db")
        checker = DeepHallucinationChecker(db_path=db)
        result = checker._get_cache(payload, "pypi", "existence")
        assert result is None  # Not found, but no crash
        _assert_all_tables_exist(db)
