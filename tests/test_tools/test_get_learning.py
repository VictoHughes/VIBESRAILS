"""Tests for tools/get_learning.py — MCP get_learning tool."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.get_learning import get_learning  # noqa: E402

# ── Action: profile ──────────────────────────────────────────────────


class TestProfileAction:
    """Tests for action='profile'."""

    def test_profile_no_data(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="profile", db_path=str(db))
        assert result["status"] == "info"
        assert result["data"]["status"] == "no_data"

    def test_profile_with_data(self, tmp_path):
        db = tmp_path / "test.db"
        # Record some events first
        get_learning(
            action="record", session_id="s1",
            event_type="brief_score", event_data={"score": 70},
            db_path=str(db),
        )
        result = get_learning(action="profile", db_path=str(db))
        assert result["status"] == "pass"
        assert result["data"]["sessions_count"] == 1
        assert result["data"]["avg_brief_score"] == 70.0

    def test_profile_has_pedagogy(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="profile", db_path=str(db))
        assert "pedagogy" in result
        assert "why" in result["pedagogy"]


# ── Action: insights ─────────────────────────────────────────────────


class TestInsightsAction:
    """Tests for action='insights'."""

    def test_insights_no_data(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="insights", db_path=str(db))
        assert result["status"] == "info"
        assert isinstance(result["data"], list)

    def test_insights_with_data(self, tmp_path):
        db = tmp_path / "test.db"
        for i in range(3):
            get_learning(
                action="record", session_id=f"s{i}",
                event_type="brief_score", event_data={"score": 30},
                db_path=str(db),
            )
        result = get_learning(action="insights", db_path=str(db))
        assert result["status"] == "pass"
        assert len(result["data"]) >= 1

    def test_insights_has_pedagogy(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="insights", db_path=str(db))
        assert "pedagogy" in result


# ── Action: session_summary ──────────────────────────────────────────


class TestSessionSummaryAction:
    """Tests for action='session_summary'."""

    def test_session_summary_requires_session_id(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="session_summary", db_path=str(db))
        assert result["status"] == "error"
        assert "session_id" in result["error"]

    def test_session_summary_valid(self, tmp_path):
        db = tmp_path / "test.db"
        get_learning(
            action="record", session_id="s1",
            event_type="violation", event_data={"guard_name": "dead_code"},
            db_path=str(db),
        )
        result = get_learning(
            action="session_summary", session_id="s1", db_path=str(db),
        )
        assert result["status"] == "pass"
        assert result["data"]["events_count"] == 1


# ── Action: record ───────────────────────────────────────────────────


class TestRecordAction:
    """Tests for action='record'."""

    def test_record_missing_session_id(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(
            action="record", event_type="violation",
            event_data={"guard_name": "test"}, db_path=str(db),
        )
        assert result["status"] == "error"
        assert "session_id" in result["error"]

    def test_record_missing_event_type(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(
            action="record", session_id="s1",
            event_data={"data": "test"}, db_path=str(db),
        )
        assert result["status"] == "error"
        assert "event_type" in result["error"]

    def test_record_missing_event_data(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(
            action="record", session_id="s1",
            event_type="violation", db_path=str(db),
        )
        assert result["status"] == "error"
        assert "event_data" in result["error"]

    def test_record_valid(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(
            action="record", session_id="s1",
            event_type="violation", event_data={"guard_name": "dead_code"},
            db_path=str(db),
        )
        assert result["status"] == "pass"
        assert result["data"]["recorded"] is True


# ── Invalid action ───────────────────────────────────────────────────


class TestInvalidAction:
    """Tests for invalid action."""

    def test_invalid_action_returns_error(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="invalid_action", db_path=str(db))
        assert result["status"] == "error"
        assert "Invalid action" in result["error"]


# ── Result structure ─────────────────────────────────────────────────


class TestResultStructure:
    """Tests for consistent result structure."""

    def test_result_has_required_keys(self, tmp_path):
        db = tmp_path / "test.db"
        result = get_learning(action="profile", db_path=str(db))
        for key in ("status", "data", "pedagogy"):
            assert key in result, f"Missing key: {key}"
