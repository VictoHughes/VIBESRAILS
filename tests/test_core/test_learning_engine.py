"""Tests for core/learning_engine.py — Learning Engine cross-session profiling."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest  # noqa: E402

from core.learning_engine import VALID_EVENT_TYPES, LearningEngine  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _engine(tmp_path: Path) -> LearningEngine:
    db = tmp_path / "learning_test.db"
    return LearningEngine(db_path=str(db))


def _seed_violations(engine: LearningEngine, session_id: str, guards: list[str]) -> None:
    """Record multiple violation events."""
    for guard in guards:
        engine.record_event(session_id, "violation", {"guard_name": guard, "severity": "warn"})


def _seed_brief_scores(engine: LearningEngine, sessions: list[tuple[str, int]]) -> None:
    """Record brief_score events for multiple sessions."""
    for session_id, score in sessions:
        engine.record_event(session_id, "brief_score", {"score": score})


# ── record_event ─────────────────────────────────────────────────────


class TestRecordEvent:
    """Tests for record_event."""

    def test_insert_event(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "dead_code", "severity": "warn"})
        profile = e.get_profile()
        assert profile["status"] == "ok"
        assert profile["sessions_count"] == 1

    def test_invalid_event_type_raises(self, tmp_path):
        e = _engine(tmp_path)
        with pytest.raises(ValueError, match="Invalid event_type"):
            e.record_event("s1", "invalid_type", {"data": "test"})

    def test_multiple_events_same_session(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "dead_code"})
        e.record_event("s1", "violation", {"guard_name": "complexity"})
        e.record_event("s1", "brief_score", {"score": 75})
        summary = e.get_session_summary("s1")
        assert summary["events_count"] == 3

    def test_valid_event_types(self):
        expected = {"violation", "brief_score", "drift", "hallucination", "config_issue", "injection"}
        assert VALID_EVENT_TYPES == expected


# ── get_profile ──────────────────────────────────────────────────────


class TestGetProfile:
    """Tests for get_profile."""

    def test_empty_returns_no_data(self, tmp_path):
        e = _engine(tmp_path)
        profile = e.get_profile()
        assert profile["status"] == "no_data"
        assert profile["sessions_count"] == 0

    def test_profile_after_events(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 70), ("s2", 80), ("s3", 60), ("s4", 90), ("s5", 50)])
        profile = e.get_profile()
        assert profile["status"] == "ok"
        assert profile["sessions_count"] == 5

    def test_sessions_count_distinct(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "a"})
        e.record_event("s1", "violation", {"guard_name": "b"})
        e.record_event("s2", "violation", {"guard_name": "c"})
        profile = e.get_profile()
        assert profile["sessions_count"] == 2


# ── avg_brief_score ──────────────────────────────────────────────────


class TestAvgBriefScore:
    """Tests for avg_brief_score metric."""

    def test_avg_brief_score_calculated(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 60), ("s2", 80)])
        profile = e.get_profile()
        assert profile["avg_brief_score"] == 70.0

    def test_avg_brief_score_single_session(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 55)])
        profile = e.get_profile()
        assert profile["avg_brief_score"] == 55.0

    def test_avg_brief_score_none_without_brief_events(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "test"})
        profile = e.get_profile()
        assert profile["avg_brief_score"] is None


# ── top_violations ───────────────────────────────────────────────────


class TestTopViolations:
    """Tests for top_violations metric."""

    def test_top_violations_ranking(self, tmp_path):
        e = _engine(tmp_path)
        _seed_violations(e, "s1", ["dead_code", "dead_code", "complexity"])
        _seed_violations(e, "s2", ["dead_code", "complexity", "complexity"])
        _seed_violations(e, "s3", ["env_safety"])
        profile = e.get_profile()
        top = profile["top_violations"]
        assert len(top) == 3
        # dead_code: 3, complexity: 3, env_safety: 1
        guards = [v["guard"] for v in top]
        assert "dead_code" in guards
        assert "complexity" in guards

    def test_top_violations_limit_5(self, tmp_path):
        e = _engine(tmp_path)
        for i in range(10):
            e.record_event("s1", "violation", {"guard_name": f"guard_{i}"})
        profile = e.get_profile()
        assert len(profile["top_violations"]) <= 5


# ── hallucination_rate ───────────────────────────────────────────────


class TestHallucinationRate:
    """Tests for hallucination_rate metric."""

    def test_hallucination_rate_calculation(self, tmp_path):
        e = _engine(tmp_path)
        # 3 sessions, 2 have hallucinations
        e.record_event("s1", "hallucination", {"module": "fake_lib"})
        e.record_event("s2", "hallucination", {"module": "bogus_pkg"})
        e.record_event("s3", "violation", {"guard_name": "dead_code"})
        profile = e.get_profile()
        # 2 hallucination events / 3 distinct sessions = 0.667
        assert profile["hallucination_rate"] == pytest.approx(0.667, abs=0.01)

    def test_no_hallucinations_rate_zero(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "test"})
        profile = e.get_profile()
        assert profile["hallucination_rate"] == 0.0


# ── improvement_rate ─────────────────────────────────────────────────


class TestImprovementRate:
    """Tests for improvement_rate metric."""

    def test_improving_scores_positive_rate(self, tmp_path):
        e = _engine(tmp_path)
        # Old sessions (lower scores)
        _seed_brief_scores(e, [
            ("s01", 30), ("s02", 35), ("s03", 40), ("s04", 45), ("s05", 50),
        ])
        # Recent sessions (higher scores)
        _seed_brief_scores(e, [
            ("s06", 70), ("s07", 75), ("s08", 80), ("s09", 85), ("s10", 90),
        ])
        profile = e.get_profile()
        assert profile["improvement_rate"] is not None
        assert profile["improvement_rate"] > 0

    def test_declining_scores_negative_rate(self, tmp_path):
        e = _engine(tmp_path)
        # Old sessions (higher scores)
        _seed_brief_scores(e, [
            ("s01", 80), ("s02", 85), ("s03", 90), ("s04", 95), ("s05", 100),
        ])
        # Recent sessions (lower scores)
        _seed_brief_scores(e, [
            ("s06", 30), ("s07", 35), ("s08", 40), ("s09", 45), ("s10", 50),
        ])
        profile = e.get_profile()
        assert profile["improvement_rate"] is not None
        assert profile["improvement_rate"] < 0

    def test_not_enough_sessions_returns_none(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 50)])
        profile = e.get_profile()
        assert profile["improvement_rate"] is None


# ── get_insights ─────────────────────────────────────────────────────


class TestGetInsights:
    """Tests for get_insights."""

    def test_no_data_insight(self, tmp_path):
        e = _engine(tmp_path)
        insights = e.get_insights()
        assert len(insights) == 1
        assert "Pas encore" in insights[0]

    def test_low_brief_score_insight(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 20), ("s2", 30), ("s3", 40)])
        insights = e.get_insights()
        assert any("incomplets" in i for i in insights)

    def test_high_hallucination_rate_insight(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "hallucination", {"module": "a"})
        e.record_event("s2", "hallucination", {"module": "b"})
        e.record_event("s3", "violation", {"guard_name": "x"})
        insights = e.get_insights()
        assert any("hallucinations" in i.lower() for i in insights)

    def test_good_profile_positive_insight(self, tmp_path):
        e = _engine(tmp_path)
        _seed_brief_scores(e, [("s1", 85), ("s2", 90), ("s3", 95)])
        insights = e.get_insights()
        # No critical issues — should have a healthy profile message
        assert len(insights) >= 1

    def test_violations_insight(self, tmp_path):
        e = _engine(tmp_path)
        _seed_violations(e, "s1", ["dead_code", "dead_code", "complexity"])
        insights = e.get_insights()
        assert any("violations" in i.lower() for i in insights)


# ── get_session_summary ──────────────────────────────────────────────


class TestGetSessionSummary:
    """Tests for get_session_summary."""

    def test_summary_aggregates_correctly(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "dead_code"})
        e.record_event("s1", "violation", {"guard_name": "complexity"})
        e.record_event("s1", "brief_score", {"score": 75})
        e.record_event("s1", "drift", {"velocity": 12.5, "highest_metric": "function_count"})
        e.record_event("s1", "hallucination", {"module": "fake_lib"})
        e.record_event("s1", "injection", {"category": "system_override"})

        summary = e.get_session_summary("s1")
        assert summary["session_id"] == "s1"
        assert summary["events_count"] == 6
        assert summary["violations"] == ["dead_code", "complexity"]
        assert summary["brief_score"] == 75
        assert summary["drift_velocity"] == 12.5
        assert summary["hallucinations"] == 1
        assert summary["injections_detected"] == 1

    def test_nonexistent_session_empty(self, tmp_path):
        e = _engine(tmp_path)
        summary = e.get_session_summary("nonexistent")
        assert summary["events_count"] == 0
        assert summary["violations"] == []
        assert summary["brief_score"] is None

    def test_session_with_no_drift(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "violation", {"guard_name": "test"})
        summary = e.get_session_summary("s1")
        assert summary["drift_velocity"] is None


# ── common_drift_areas ───────────────────────────────────────────────


class TestCommonDriftAreas:
    """Tests for common_drift_areas metric."""

    def test_drift_areas_aggregated(self, tmp_path):
        e = _engine(tmp_path)
        e.record_event("s1", "drift", {"velocity": 10, "highest_metric": "function_count"})
        e.record_event("s2", "drift", {"velocity": 8, "highest_metric": "function_count"})
        e.record_event("s3", "drift", {"velocity": 15, "highest_metric": "complexity_avg"})
        profile = e.get_profile()
        areas = profile["common_drift_areas"]
        assert len(areas) >= 1
        assert areas[0]["metric"] == "function_count"
        assert areas[0]["count"] == 2
