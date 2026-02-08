"""Tests for core/session_tracker.py — Session Entropy Monitor."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.session_tracker import (  # noqa: E402
    SessionTracker,
    calculate_entropy,
    classify_entropy,
)

# ── calculate_entropy ──────────────────────────────────────────────────


class TestCalculateEntropy:
    """Tests for the entropy formula."""

    def test_all_zeros(self):
        assert calculate_entropy(0, 0, 0, 0) == 0.0

    def test_all_maxed(self):
        # 60min, 20 files, 10 violations, 500 LOC → all factors = 1.0
        score = calculate_entropy(60, 20, 10, 500)
        assert score == 1.0

    def test_known_values(self):
        # 30min, 10 files, 5 violations, 250 LOC
        # duration_factor = 30/60 = 0.5
        # files_factor = 10/20 = 0.5
        # violations_factor = 5/10 = 0.5
        # change_factor = 250/500 = 0.5
        # entropy = 0.5*0.3 + 0.5*0.2 + 0.5*0.3 + 0.5*0.2
        #         = 0.15 + 0.10 + 0.15 + 0.10 = 0.50
        score = calculate_entropy(30, 10, 5, 250)
        assert abs(score - 0.50) < 0.001

    def test_clamped_at_one(self):
        # Values exceeding caps should still produce max 1.0
        score = calculate_entropy(120, 40, 20, 1000)
        assert score == 1.0

    def test_duration_only(self):
        # 60 min, nothing else
        # entropy = 1.0*0.3 + 0 + 0 + 0 = 0.3
        score = calculate_entropy(60, 0, 0, 0)
        assert abs(score - 0.3) < 0.001

    def test_violations_only(self):
        # 10 violations, nothing else
        # entropy = 0 + 0 + 1.0*0.3 + 0 = 0.3
        score = calculate_entropy(0, 0, 10, 0)
        assert abs(score - 0.3) < 0.001

    def test_partial_values(self):
        # 15min, 5 files, 2 violations, 100 LOC
        # duration = 15/60 = 0.25
        # files = 5/20 = 0.25
        # violations = 2/10 = 0.2
        # change = 100/500 = 0.2
        # entropy = 0.25*0.3 + 0.25*0.2 + 0.2*0.3 + 0.2*0.2
        #         = 0.075 + 0.05 + 0.06 + 0.04 = 0.225
        score = calculate_entropy(15, 5, 2, 100)
        assert abs(score - 0.225) < 0.001


# ── classify_entropy ───────────────────────────────────────────────────


class TestClassifyEntropy:
    """Tests for entropy level classification."""

    def test_safe(self):
        assert classify_entropy(0.0) == "safe"
        assert classify_entropy(0.15) == "safe"
        assert classify_entropy(0.29) == "safe"

    def test_warning(self):
        assert classify_entropy(0.3) == "warning"
        assert classify_entropy(0.45) == "warning"
        assert classify_entropy(0.59) == "warning"

    def test_elevated(self):
        assert classify_entropy(0.6) == "elevated"
        assert classify_entropy(0.7) == "elevated"
        assert classify_entropy(0.79) == "elevated"

    def test_critical(self):
        assert classify_entropy(0.8) == "critical"
        assert classify_entropy(0.9) == "critical"
        assert classify_entropy(1.0) == "critical"


# ── SessionTracker lifecycle ──────────────────────────────────────────


class TestSessionTrackerLifecycle:
    """Tests for the full session lifecycle."""

    def test_start_returns_uuid(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")
        assert len(sid) == 36  # UUID format
        assert "-" in sid

    def test_start_with_ai_tool(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project", ai_tool="claude_code")
        session = tracker.get_session(sid)
        assert session is not None
        assert session["ai_tool"] == "claude_code"

    def test_fresh_session_entropy_zero(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")
        session = tracker.get_session(sid)
        assert session["entropy_score"] == 0.0
        assert session["total_changes_loc"] == 0
        assert session["violations_count"] == 0
        assert session["files_modified"] == []

    def test_update_accumulates(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")

        tracker.update_session(sid, files_modified=["a.py"], changes_loc=50, violations=1)
        tracker.update_session(sid, files_modified=["b.py"], changes_loc=30, violations=2)

        session = tracker.get_session(sid)
        assert set(session["files_modified"]) == {"a.py", "b.py"}
        assert session["total_changes_loc"] == 80
        assert session["violations_count"] == 3

    def test_update_deduplicates_files(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")

        tracker.update_session(sid, files_modified=["a.py", "b.py"])
        tracker.update_session(sid, files_modified=["a.py", "c.py"])

        session = tracker.get_session(sid)
        assert set(session["files_modified"]) == {"a.py", "b.py", "c.py"}

    def test_end_session_returns_summary(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")
        tracker.update_session(sid, files_modified=["a.py"], changes_loc=100, violations=3)

        summary = tracker.end_session(sid)
        assert summary["session_id"] == sid
        assert summary["total_changes_loc"] == 100
        assert summary["violations_count"] == 3
        assert summary["files_modified"] == ["a.py"]
        assert summary["entropy_level"] in ("safe", "warning", "elevated", "critical")
        assert 0.0 <= summary["final_entropy"] <= 1.0

    def test_end_session_sets_end_time(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        sid = tracker.start_session("/tmp/project")
        tracker.end_session(sid)

        session = tracker.get_session(sid)
        assert session["end_time"] is not None


# ── Entropy calculation with time mocking ─────────────────────────────


class TestSessionEntropyWithTime:
    """Tests for entropy calculation with controlled time."""

    def test_entropy_grows_with_duration(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)

        # Start session at t=0
        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = base_time
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            sid = tracker.start_session("/tmp/project")

        # 30 minutes later, no changes
        later = base_time + timedelta(minutes=30)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = later
            mock_dt.fromisoformat = datetime.fromisoformat
            entropy = tracker.get_entropy(sid)

        # duration_factor = 30/60 = 0.5 → entropy = 0.5 * 0.3 = 0.15
        assert abs(entropy - 0.15) < 0.01

    def test_entropy_exact_calculation(self, tmp_path):
        """Test entropy with fully controlled time and known values."""
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)

        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = base_time
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            sid = tracker.start_session("/tmp/project")

        # 30min later, update with 10 files, 5 violations, 250 LOC
        later = base_time + timedelta(minutes=30)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = later
            mock_dt.fromisoformat = datetime.fromisoformat
            entropy = tracker.update_session(
                sid,
                files_modified=[f"file{i}.py" for i in range(10)],
                changes_loc=250,
                violations=5,
            )

        # duration=30/60=0.5, files=10/20=0.5, violations=5/10=0.5, loc=250/500=0.5
        # entropy = 0.5*0.3 + 0.5*0.2 + 0.5*0.3 + 0.5*0.2 = 0.50
        assert abs(entropy - 0.50) < 0.01

    def test_critical_entropy(self, tmp_path):
        """Session pushed to critical entropy."""
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)

        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = base_time
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            sid = tracker.start_session("/tmp/project")

        # 60min, 20 files, 10 violations, 500 LOC → entropy = 1.0
        later = base_time + timedelta(minutes=60)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = later
            mock_dt.fromisoformat = datetime.fromisoformat
            entropy = tracker.update_session(
                sid,
                files_modified=[f"f{i}.py" for i in range(20)],
                changes_loc=500,
                violations=10,
            )

        assert abs(entropy - 1.0) < 0.01
        assert classify_entropy(entropy) == "critical"


# ── Error handling ────────────────────────────────────────────────────


class TestSessionTrackerErrors:
    """Tests for error handling."""

    def test_update_unknown_session_raises(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        try:
            tracker.update_session("nonexistent-id")
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "not found" in str(exc).lower()

    def test_get_entropy_unknown_session_raises(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        try:
            tracker.get_entropy("nonexistent-id")
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "not found" in str(exc).lower()

    def test_end_unknown_session_raises(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        try:
            tracker.end_session("nonexistent-id")
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "not found" in str(exc).lower()

    def test_get_session_unknown_returns_none(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)
        assert tracker.get_session("nonexistent-id") is None


# ── Multiple sessions ─────────────────────────────────────────────────


class TestMultipleSessions:
    """Tests for running multiple sessions simultaneously."""

    def test_two_concurrent_sessions(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)

        sid1 = tracker.start_session("/project/a")
        sid2 = tracker.start_session("/project/b")

        assert sid1 != sid2

        tracker.update_session(sid1, files_modified=["a.py"], changes_loc=100)
        tracker.update_session(sid2, files_modified=["b.py"], changes_loc=200)

        s1 = tracker.get_session(sid1)
        s2 = tracker.get_session(sid2)

        assert s1["total_changes_loc"] == 100
        assert s2["total_changes_loc"] == 200
        assert s1["files_modified"] == ["a.py"]
        assert s2["files_modified"] == ["b.py"]

    def test_sessions_persist_independently(self, tmp_path):
        db = tmp_path / "test.db"
        tracker = SessionTracker(db_path=db)

        sid1 = tracker.start_session("/project/a")
        sid2 = tracker.start_session("/project/b")

        tracker.update_session(sid1, violations=5)
        tracker.end_session(sid1)

        # sid2 should not be affected
        s2 = tracker.get_session(sid2)
        assert s2["violations_count"] == 0
        assert s2["end_time"] is None


# ── Persistence ───────────────────────────────────────────────────────


class TestPersistence:
    """Tests for SQLite persistence."""

    def test_session_survives_new_tracker_instance(self, tmp_path):
        db = tmp_path / "test.db"

        # First tracker instance
        tracker1 = SessionTracker(db_path=db)
        sid = tracker1.start_session("/tmp/project")
        tracker1.update_session(sid, files_modified=["a.py"], changes_loc=50, violations=2)

        # Second tracker instance (same DB)
        tracker2 = SessionTracker(db_path=db)
        session = tracker2.get_session(sid)

        assert session is not None
        assert session["total_changes_loc"] == 50
        assert session["violations_count"] == 2
        assert session["files_modified"] == ["a.py"]
