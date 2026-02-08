"""Tests for core/brief_enforcer.py — Pre-Generation Discipline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.brief_enforcer import BriefEnforcer, classify_level  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _enforcer(tmp_path: Path) -> BriefEnforcer:
    db = tmp_path / "brief_test.db"
    return BriefEnforcer(db_path=str(db))


def _full_brief() -> dict:
    return {
        "intent": "Add a user authentication endpoint using JWT tokens",
        "constraints": ["Must use existing database schema", "Timeout under 200ms"],
        "affects": ["auth/routes.py", "auth/middleware.py", "tests/test_auth.py"],
        "tradeoffs": "Prefer simplicity over maximum security for MVP phase",
        "rollback": "Feature flag can disable the endpoint instantly",
        "dependencies": ["pyjwt", "auth/models.py", "database connection pool"],
    }


def _minimal_brief() -> dict:
    return {
        "intent": "Refactor the payment processing module for clarity",
        "constraints": ["Keep backward compatibility"],
        "affects": ["payments/processor.py"],
    }


def _empty_brief() -> dict:
    return {}


# ── classify_level ───────────────────────────────────────────────────


class TestClassifyLevel:
    """Tests for level classification."""

    def test_insufficient(self):
        assert classify_level(0) == "insufficient"
        assert classify_level(20) == "insufficient"
        assert classify_level(39) == "insufficient"

    def test_minimal(self):
        assert classify_level(40) == "minimal"
        assert classify_level(50) == "minimal"
        assert classify_level(59) == "minimal"

    def test_adequate(self):
        assert classify_level(60) == "adequate"
        assert classify_level(70) == "adequate"
        assert classify_level(79) == "adequate"

    def test_strong(self):
        assert classify_level(80) == "strong"
        assert classify_level(90) == "strong"
        assert classify_level(100) == "strong"


# ── validate_brief ───────────────────────────────────────────────────


class TestValidateBrief:
    """Tests for brief validation."""

    def test_full_brief_high_score(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.validate_brief(_full_brief())
        assert result["score"] >= 80
        assert result["level"] == "strong"
        assert result["missing_required"] == []

    def test_minimal_brief_adequate(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.validate_brief(_minimal_brief())
        assert result["score"] >= 40
        assert result["level"] in ("minimal", "adequate")
        assert "tradeoffs" in result["missing_optional"]

    def test_empty_brief_insufficient(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.validate_brief(_empty_brief())
        assert result["score"] == 0
        assert result["level"] == "insufficient"
        assert len(result["missing_required"]) == 3

    def test_result_has_all_keys(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.validate_brief(_minimal_brief())
        for key in ("score", "level", "missing_required", "missing_optional", "field_issues"):
            assert key in result, f"Missing key: {key}"

    def test_optional_fields_increase_score(self, tmp_path):
        e = _enforcer(tmp_path)
        minimal = e.validate_brief(_minimal_brief())
        full = e.validate_brief(_full_brief())
        assert full["score"] > minimal["score"]


# ── score_quality ────────────────────────────────────────────────────


class TestScoreQuality:
    """Tests for individual field quality scoring."""

    def test_vague_intent_scores_zero(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality("fix it", "intent")
        assert result["score"] == 0.0
        assert "too_vague" in result["flags"]

    def test_make_it_work_scores_zero(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality("make it work", "intent")
        assert result["score"] == 0.0
        assert "too_vague" in result["flags"]

    def test_short_text_scores_zero(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality("do X", "intent")
        assert result["score"] == 0.0
        assert "too_short" in result["flags"]

    def test_empty_text_scores_zero(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality("", "intent")
        assert result["score"] == 0.0
        assert "empty" in result["flags"]

    def test_good_intent_positive_score(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality(
            "Add rate limiting to the API endpoints in routes.py", "intent"
        )
        assert result["score"] > 0.5

    def test_action_verb_bonus(self, tmp_path):
        e = _enforcer(tmp_path)
        with_verb = e.score_quality(
            "Implement caching for database queries", "intent"
        )
        without_verb = e.score_quality(
            "Something about database queries caching", "intent"
        )
        assert with_verb["score"] >= without_verb["score"]

    def test_no_action_flag(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality(
            "Something about the user module here", "intent"
        )
        assert "no_action" in result["flags"]

    def test_file_reference_bonus(self, tmp_path):
        e = _enforcer(tmp_path)
        result = e.score_quality(
            "Modify the handler in api/routes.py for better error handling", "intent"
        )
        assert result["score"] >= 0.75


# ── suggest_improvement ──────────────────────────────────────────────


class TestSuggestImprovement:
    """Tests for improvement suggestions."""

    def test_empty_brief_gives_suggestions(self, tmp_path):
        e = _enforcer(tmp_path)
        suggestions = e.suggest_improvement(_empty_brief())
        assert len(suggestions) >= 3
        assert any("intent" in s for s in suggestions)
        assert any("constraints" in s for s in suggestions)

    def test_full_brief_fewer_suggestions(self, tmp_path):
        e = _enforcer(tmp_path)
        empty_sug = e.suggest_improvement(_empty_brief())
        full_sug = e.suggest_improvement(_full_brief())
        assert len(full_sug) < len(empty_sug)

    def test_vague_brief_gets_fix_suggestion(self, tmp_path):
        e = _enforcer(tmp_path)
        brief = {"intent": "fix it", "constraints": [], "affects": []}
        suggestions = e.suggest_improvement(brief)
        assert any("[FIX]" in s for s in suggestions)


# ── History ──────────────────────────────────────────────────────────


class TestBriefHistory:
    """Tests for brief history storage."""

    def test_store_and_retrieve(self, tmp_path):
        e = _enforcer(tmp_path)
        brief = _minimal_brief()
        row_id = e.store_brief(brief, 55, "minimal", session_id="s1")
        assert row_id is not None
        assert row_id > 0

        history = e.get_history(session_id="s1")
        assert len(history) == 1
        assert history[0]["score"] == 55
        assert history[0]["level"] == "minimal"
        assert history[0]["brief"]["intent"] == brief["intent"]

    def test_multiple_briefs_stored(self, tmp_path):
        e = _enforcer(tmp_path)
        e.store_brief({"intent": "first"}, 30, "insufficient", session_id="s1")
        e.store_brief({"intent": "second"}, 60, "adequate", session_id="s1")
        e.store_brief({"intent": "third"}, 85, "strong", session_id="s2")

        s1_history = e.get_history(session_id="s1")
        assert len(s1_history) == 2

        all_history = e.get_history()
        assert len(all_history) == 3

    def test_history_without_session(self, tmp_path):
        e = _enforcer(tmp_path)
        e.store_brief({"intent": "no session"}, 50, "minimal")
        history = e.get_history()
        assert len(history) == 1
        assert history[0]["session_id"] is None
