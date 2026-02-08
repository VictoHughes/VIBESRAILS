"""Tests for tools/check_session.py — MCP check_session tool."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.check_session import (  # noqa: E402
    SESSION_PEDAGOGY,
    check_session,
)


class TestCheckSessionResult:
    """Tests for the check_session result structure."""

    def test_result_has_required_keys(self):
        result = check_session()
        assert "is_ai_session" in result
        assert "agent_name" in result
        assert "env_markers_checked" in result
        assert "guardian_stats" in result
        assert "pedagogy" in result

    def test_guardian_stats_structure(self):
        result = check_session()
        stats = result["guardian_stats"]
        assert "total_blocks" in stats
        assert "by_pattern" in stats
        assert "by_agent" in stats

    def test_pedagogy_structure(self):
        result = check_session()
        pedagogy = result["pedagogy"]
        assert "why" in pedagogy
        assert "recommendation" in pedagogy

    def test_env_markers_is_list(self):
        result = check_session()
        assert isinstance(result["env_markers_checked"], list)
        assert len(result["env_markers_checked"]) > 0


class TestCheckSessionDetection:
    """Tests for AI session detection via environment variables."""

    def test_no_ai_env_returns_false(self):
        with patch.dict("os.environ", {}, clear=True):
            # Also patch TERM_PROGRAM and Path.home
            with patch("core.guardian.Path") as mock_path:
                mock_path.home.return_value.joinpath.return_value.exists.return_value = False
                result = check_session()
                assert result["is_ai_session"] is False
                assert result["agent_name"] is None

    def test_claude_code_env_detected(self):
        with patch.dict("os.environ", {"CLAUDE_CODE": "1"}, clear=False):
            result = check_session()
            assert result["is_ai_session"] is True
            assert result["agent_name"] == "Claude Code"

    def test_cursor_env_detected(self):
        with patch.dict("os.environ", {"CURSOR_SESSION": "1"}, clear=False):
            result = check_session()
            assert result["is_ai_session"] is True
            assert result["agent_name"] == "Cursor"

    def test_manual_override_detected(self):
        with patch.dict("os.environ", {"VIBESRAILS_AGENT_MODE": "1"}, clear=False):
            result = check_session()
            assert result["is_ai_session"] is True
            assert result["agent_name"] == "AI Agent (manual)"

    def test_pedagogy_changes_with_detection(self):
        with patch.dict("os.environ", {"CLAUDE_CODE": "1"}, clear=False):
            result = check_session()
            assert "stricter rules" in result["pedagogy"]["why"].lower() or \
                   "environment variables" in result["pedagogy"]["why"].lower()

    def test_no_ai_pedagogy(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("core.guardian.Path") as mock_path:
                mock_path.home.return_value.joinpath.return_value.exists.return_value = False
                result = check_session()
                assert "no ai" in result["pedagogy"]["why"].lower() or \
                       "no active" in result["pedagogy"]["why"].lower() or \
                       "not found" in result["pedagogy"]["why"].lower()


class TestSessionPedagogy:
    """Tests for pedagogy messages."""

    def test_ai_detected_pedagogy_exists(self):
        assert "ai_detected" in SESSION_PEDAGOGY
        p = SESSION_PEDAGOGY["ai_detected"]
        assert "why" in p
        assert "recommendation" in p

    def test_no_ai_detected_pedagogy_exists(self):
        assert "no_ai_detected" in SESSION_PEDAGOGY
        p = SESSION_PEDAGOGY["no_ai_detected"]
        assert "why" in p
        assert "recommendation" in p
