"""Tests for tools/enforce_brief.py — MCP enforce_brief tool."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.enforce_brief import enforce_brief  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _full_brief() -> dict:
    return {
        "intent": "Create a REST API endpoint for user profile updates",
        "constraints": ["Must validate all input fields", "Rate limit to 10 req/s"],
        "affects": ["api/users.py", "api/validators.py", "tests/test_users.py"],
        "tradeoffs": "Prefer strict validation over permissive input handling",
        "rollback": "Feature flag USER_PROFILE_V2 can disable the endpoint",
        "dependencies": ["pydantic", "api/auth.py", "database models"],
    }


def _minimal_brief() -> dict:
    return {
        "intent": "Refactor the error handling in the payment module",
        "constraints": ["Keep existing API contract"],
        "affects": ["payments/handler.py"],
    }


def _empty_brief() -> dict:
    return {}


def _vague_brief() -> dict:
    return {
        "intent": "fix it",
        "constraints": [],
        "affects": [],
    }


# ── Strong brief ─────────────────────────────────────────────────────


class TestStrongBrief:
    """Tests for strong briefs that should pass."""

    def test_full_brief_passes(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_full_brief(), db_path=str(db))
        assert result["status"] == "pass"
        assert result["score"] >= 80
        assert result["level"] == "strong"

    def test_strong_brief_has_pedagogy(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_full_brief(), db_path=str(db))
        assert "pedagogy" in result
        assert "solide" in result["pedagogy"]["why"].lower()


# ── Weak brief ───────────────────────────────────────────────────────


class TestWeakBrief:
    """Tests for weak briefs — normal vs strict mode."""

    def test_weak_brief_warns_normal_mode(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(
            brief=_minimal_brief(), strict=False, db_path=str(db),
        )
        # Minimal brief should be warn or pass (score ~40-60)
        assert result["status"] in ("warn", "pass")

    def test_weak_brief_blocks_strict_mode(self, tmp_path):
        db = tmp_path / "test.db"
        # A brief that scores between 20-59 should block in strict mode
        brief = {
            "intent": "Update the configuration loading mechanism",
            "constraints": ["backward compat"],
            "affects": ["config.py"],
        }
        result = enforce_brief(brief=brief, strict=True, db_path=str(db))
        if result["score"] < 60:
            assert result["status"] == "block"


# ── Insufficient brief ───────────────────────────────────────────────


class TestInsufficientBrief:
    """Tests for insufficient briefs that should block."""

    def test_empty_brief_blocks_both_modes(self, tmp_path):
        db = tmp_path / "test.db"
        normal = enforce_brief(brief=_empty_brief(), strict=False, db_path=str(db))
        strict = enforce_brief(brief=_empty_brief(), strict=True, db_path=str(db))
        assert normal["status"] == "block"
        assert strict["status"] == "block"

    def test_vague_brief_blocks(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_vague_brief(), db_path=str(db))
        assert result["status"] == "block"
        assert result["score"] < 20


# ── Pedagogy ─────────────────────────────────────────────────────────


class TestPedagogy:
    """Tests for pedagogy presence."""

    def test_all_results_have_pedagogy(self, tmp_path):
        db = tmp_path / "test.db"
        for brief_fn in [_full_brief, _minimal_brief, _empty_brief, _vague_brief]:
            result = enforce_brief(brief=brief_fn(), db_path=str(db))
            assert "pedagogy" in result
            assert "why" in result["pedagogy"]
            assert "recommendation" in result["pedagogy"]


# ── Suggestions ──────────────────────────────────────────────────────


class TestSuggestions:
    """Tests for improvement suggestions."""

    def test_weak_brief_has_suggestions(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_empty_brief(), db_path=str(db))
        assert len(result["suggestions"]) > 0

    def test_strong_brief_fewer_suggestions(self, tmp_path):
        db = tmp_path / "test.db"
        weak = enforce_brief(brief=_empty_brief(), db_path=str(db))
        strong = enforce_brief(brief=_full_brief(), db_path=str(db))
        assert len(strong["suggestions"]) < len(weak["suggestions"])


# ── Session tracking ─────────────────────────────────────────────────


class TestSessionTracking:
    """Tests for session_id parameter."""

    def test_session_id_optional(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_full_brief(), db_path=str(db))
        assert result["status"] == "pass"

    def test_session_id_accepted(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(
            brief=_full_brief(), session_id="test-session-123",
            db_path=str(db),
        )
        assert result["status"] == "pass"


# ── Result structure ─────────────────────────────────────────────────


class TestResultStructure:
    """Tests for consistent result structure."""

    def test_result_has_required_keys(self, tmp_path):
        db = tmp_path / "test.db"
        result = enforce_brief(brief=_minimal_brief(), db_path=str(db))
        for key in ("status", "score", "level", "missing_required",
                     "missing_optional", "field_issues", "suggestions", "pedagogy"):
            assert key in result, f"Missing key: {key}"
