"""Tests for core/learning_bridge.py — safe fire-and-forget recording."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.learning_bridge import _reset, get_engine, record_safe  # noqa: E402


class TestGetEngine:
    """Tests for get_engine()."""

    def test_returns_learning_engine(self, tmp_path):
        db = tmp_path / "bridge_test.db"
        engine = get_engine(db_path=str(db))
        assert engine is not None

    def test_singleton_reuse(self):
        _reset()
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
        _reset()

    def test_db_path_bypasses_singleton(self, tmp_path):
        _reset()
        db1 = tmp_path / "a.db"
        db2 = tmp_path / "b.db"
        e1 = get_engine(db_path=str(db1))
        e2 = get_engine(db_path=str(db2))
        assert e1 is not e2
        _reset()


class TestRecordSafe:
    """Tests for record_safe()."""

    def test_records_event(self, tmp_path):
        db = tmp_path / "record_test.db"
        record_safe("s1", "violation", {"guard_name": "dead_code"}, db_path=str(db))
        engine = get_engine(db_path=str(db))
        profile = engine.get_profile()
        assert profile["sessions_count"] == 1

    def test_anonymous_session_id(self, tmp_path):
        db = tmp_path / "anon_test.db"
        record_safe(None, "violation", {"guard_name": "test"}, db_path=str(db))
        engine = get_engine(db_path=str(db))
        summary = engine.get_session_summary("anonymous")
        assert summary["events_count"] == 1

    def test_never_raises_on_invalid_event_type(self, tmp_path):
        db = tmp_path / "err_test.db"
        # Invalid event_type would raise ValueError in LearningEngine.record_event
        # but record_safe should swallow it
        record_safe("s1", "totally_invalid", {"data": "test"}, db_path=str(db))
        # No exception — test passes

    def test_never_raises_on_db_error(self):
        # Non-existent deep path should fail but record_safe swallows it
        record_safe("s1", "violation", {"guard_name": "test"}, db_path="/nonexistent/deep/path/db.db")
        # No exception — test passes

    def test_multiple_events_accumulate(self, tmp_path):
        db = tmp_path / "multi_test.db"
        record_safe("s1", "violation", {"guard_name": "dead_code"}, db_path=str(db))
        record_safe("s1", "violation", {"guard_name": "complexity"}, db_path=str(db))
        record_safe("s1", "brief_score", {"score": 75}, db_path=str(db))
        engine = get_engine(db_path=str(db))
        summary = engine.get_session_summary("s1")
        assert summary["events_count"] == 3


class TestReset:
    """Tests for _reset()."""

    def test_reset_clears_singleton(self):
        _reset()
        e1 = get_engine()
        _reset()
        e2 = get_engine()
        # After reset, a new instance should be created
        assert e1 is not e2
        _reset()
