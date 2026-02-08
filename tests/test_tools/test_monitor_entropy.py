"""Tests for tools/monitor_entropy.py — MCP monitor_entropy tool."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.monitor_entropy import (  # noqa: E402
    ENTROPY_PEDAGOGY,
    monitor_entropy,
)

# ── action=start ──────────────────────────────────────────────────────


class TestMonitorEntropyStart:
    """Tests for action=start."""

    def test_start_returns_session_id(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="start", project_path="/tmp/project", db_path=str(db))
        assert result["status"] == "ok"
        assert result["session_id"] is not None
        assert len(result["session_id"]) == 36

    def test_start_initial_entropy_zero(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="start", project_path="/tmp/project", db_path=str(db))
        assert result["entropy_score"] == 0.0
        assert result["entropy_level"] == "safe"

    def test_start_has_pedagogy(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="start", project_path="/tmp/project", db_path=str(db))
        assert "pedagogy" in result
        assert "why" in result["pedagogy"]
        assert "recommendation" in result["pedagogy"]

    def test_start_without_project_path_errors(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="start", db_path=str(db))
        assert result["status"] == "error"
        assert "project_path" in result["error"]


# ── action=update ─────────────────────────────────────────────────────


class TestMonitorEntropyUpdate:
    """Tests for action=update."""

    def test_update_returns_entropy(self, tmp_path):
        db = tmp_path / "test.db"
        start = monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))
        sid = start["session_id"]

        result = monitor_entropy(
            action="update", session_id=sid,
            files_modified=["a.py"], changes_loc=100, violations=2,
            db_path=str(db),
        )
        assert result["status"] == "ok"
        assert result["entropy_score"] >= 0.0
        assert result["entropy_level"] in ("safe", "warning", "elevated", "critical")

    def test_update_without_session_id_errors(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="update", db_path=str(db))
        assert result["status"] == "error"
        assert "session_id" in result["error"]

    def test_update_unknown_session_errors(self, tmp_path):
        db = tmp_path / "test.db"
        # Need to init the DB first
        monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))
        result = monitor_entropy(action="update", session_id="nonexistent", db_path=str(db))
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


# ── action=status ─────────────────────────────────────────────────────


class TestMonitorEntropyStatus:
    """Tests for action=status."""

    def test_status_returns_session_info(self, tmp_path):
        db = tmp_path / "test.db"
        start = monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))
        sid = start["session_id"]

        result = monitor_entropy(action="status", session_id=sid, db_path=str(db))
        assert result["status"] == "ok"
        assert result["session_id"] == sid
        assert "files_modified" in result
        assert "total_changes_loc" in result
        assert "violations_count" in result

    def test_status_without_session_id_errors(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="status", db_path=str(db))
        assert result["status"] == "error"

    def test_status_unknown_session_errors(self, tmp_path):
        db = tmp_path / "test.db"
        monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))
        result = monitor_entropy(action="status", session_id="nonexistent", db_path=str(db))
        assert result["status"] == "error"


# ── action=end ────────────────────────────────────────────────────────


class TestMonitorEntropyEnd:
    """Tests for action=end."""

    def test_end_returns_summary(self, tmp_path):
        db = tmp_path / "test.db"
        start = monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))
        sid = start["session_id"]

        monitor_entropy(
            action="update", session_id=sid,
            files_modified=["a.py"], changes_loc=50, violations=1,
            db_path=str(db),
        )

        result = monitor_entropy(action="end", session_id=sid, db_path=str(db))
        assert result["status"] == "ok"
        assert "session_summary" in result
        assert result["session_summary"]["total_changes_loc"] == 50

    def test_end_without_session_id_errors(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="end", db_path=str(db))
        assert result["status"] == "error"


# ── Invalid action ────────────────────────────────────────────────────


class TestMonitorEntropyInvalidAction:
    """Tests for invalid action values."""

    def test_invalid_action_returns_error(self, tmp_path):
        db = tmp_path / "test.db"
        result = monitor_entropy(action="restart", db_path=str(db))
        assert result["status"] == "error"
        assert "invalid action" in result["error"].lower()
        assert "restart" in result["error"]


# ── Pedagogy changes per level ────────────────────────────────────────


class TestPedagogyPerLevel:
    """Test that pedagogy changes based on entropy level."""

    def test_pedagogy_templates_exist(self):
        for level in ("safe", "warning", "elevated", "critical"):
            assert level in ENTROPY_PEDAGOGY
            assert "why" in ENTROPY_PEDAGOGY[level]
            assert "recommendation" in ENTROPY_PEDAGOGY[level]

    def test_warning_pedagogy_mentions_hallucination(self, tmp_path):
        """Push entropy to warning level and check pedagogy."""
        db = tmp_path / "test.db"

        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = base_time
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            start = monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))

        sid = start["session_id"]

        # 30min + 5 violations → warning level
        later = base_time + timedelta(minutes=30)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = later
            mock_dt.fromisoformat = datetime.fromisoformat
            result = monitor_entropy(
                action="update", session_id=sid,
                files_modified=[f"f{i}.py" for i in range(5)],
                changes_loc=100, violations=5,
                db_path=str(db),
            )

        assert result["entropy_level"] in ("warning", "elevated")
        assert "hallucination" in result["pedagogy"]["why"].lower() or \
               "risk" in result["pedagogy"]["why"].lower()

    def test_critical_pedagogy_says_stop(self, tmp_path):
        """Push entropy to critical and verify pedagogy."""
        db = tmp_path / "test.db"

        base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = base_time
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            start = monitor_entropy(action="start", project_path="/tmp/p", db_path=str(db))

        sid = start["session_id"]

        # 60min, 20 files, 10 violations, 500 LOC → critical
        later = base_time + timedelta(minutes=60)
        with patch("core.session_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = later
            mock_dt.fromisoformat = datetime.fromisoformat
            result = monitor_entropy(
                action="update", session_id=sid,
                files_modified=[f"f{i}.py" for i in range(20)],
                changes_loc=500, violations=10,
                db_path=str(db),
            )

        assert result["entropy_level"] == "critical"
        assert "stop" in result["pedagogy"]["why"].lower()
