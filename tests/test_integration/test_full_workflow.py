"""Full workflow tests: tool → learning bridge → learning engine → profile.

These tests verify the complete pipeline WITHOUT mocking — actual events
are recorded and verified via the learning engine profile.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.learning_bridge import get_engine, record_safe  # noqa: E402


class TestFullWorkflow:
    """End-to-end workflow tests."""

    def test_violations_appear_in_profile(self, tmp_path):
        db = str(tmp_path / "workflow.db")
        # Simulate what scan_code does
        record_safe(None, "violation", {"guard_name": "dead_code", "severity": "warn"}, db_path=db)
        record_safe(None, "violation", {"guard_name": "dead_code", "severity": "warn"}, db_path=db)
        record_safe(None, "violation", {"guard_name": "complexity", "severity": "warn"}, db_path=db)

        engine = get_engine(db_path=db)
        profile = engine.get_profile()
        assert profile["status"] == "ok"
        top = profile["top_violations"]
        guards = [v["guard"] for v in top]
        assert "dead_code" in guards

    def test_brief_score_appears_in_profile(self, tmp_path):
        db = str(tmp_path / "workflow.db")
        # Simulate what enforce_brief does
        record_safe("s1", "brief_score", {"score": 85}, db_path=db)
        record_safe("s2", "brief_score", {"score": 70}, db_path=db)

        engine = get_engine(db_path=db)
        profile = engine.get_profile()
        assert profile["avg_brief_score"] == 77.5

    def test_mixed_events_session_summary(self, tmp_path):
        db = str(tmp_path / "workflow.db")
        sid = "session_42"
        # Simulate events from multiple tools
        record_safe(sid, "violation", {"guard_name": "dead_code"}, db_path=db)
        record_safe(sid, "brief_score", {"score": 65}, db_path=db)
        record_safe(sid, "drift", {"velocity": 8.5, "highest_metric": "function_count"}, db_path=db)
        record_safe(sid, "hallucination", {"module": "fake_lib"}, db_path=db)
        record_safe(sid, "injection", {"category": "system_override"}, db_path=db)
        record_safe(sid, "config_issue", {"check_type": "exfiltration", "severity": "block"}, db_path=db)

        engine = get_engine(db_path=db)
        summary = engine.get_session_summary(sid)
        assert summary["events_count"] == 6
        assert summary["violations"] == ["dead_code"]
        assert summary["brief_score"] == 65
        assert summary["drift_velocity"] == 8.5
        assert summary["hallucinations"] == 1
        assert summary["injections_detected"] == 1

    def test_insights_after_multiple_sessions(self, tmp_path):
        db = str(tmp_path / "workflow.db")
        # Multiple sessions with low brief scores
        for i in range(5):
            record_safe(f"s{i}", "brief_score", {"score": 25}, db_path=db)

        engine = get_engine(db_path=db)
        insights = engine.get_insights()
        assert any("incomplets" in i for i in insights)
