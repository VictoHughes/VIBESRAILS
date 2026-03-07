"""Tests for unified SessionContext — mode + phase + adapted config."""

from unittest import mock

import yaml

from vibesrails.context import get_session_context
from vibesrails.context.mode import SessionContext, SessionMode
from vibesrails.context.phase import ProjectPhase

# ============================================
# SessionContext dataclass
# ============================================


def test_session_context_defaults():
    """SessionContext has sensible defaults."""
    ctx = SessionContext(
        mode=SessionMode.MIXED,
        mode_score=0.5,
        mode_confidence=0.0,
    )
    assert ctx.phase == 0
    assert ctx.phase_name == "DECIDE"
    assert ctx.phase_missing == []
    assert ctx.adapted_config == {}
    assert ctx.mode_forced is False
    assert ctx.phase_is_override is False


def test_session_context_all_fields():
    """SessionContext populates all fields."""
    ctx = SessionContext(
        mode=SessionMode.RND,
        mode_score=0.85,
        mode_confidence=0.9,
        mode_forced=False,
        phase=2,
        phase_name="FLESH OUT",
        phase_is_override=True,
        phase_missing=["has_ci"],
        adapted_config={"complexity": {"max_file_lines": 600}},
    )
    assert ctx.mode == SessionMode.RND
    assert ctx.phase == 2
    assert ctx.phase_name == "FLESH OUT"
    assert ctx.phase_is_override is True
    assert ctx.phase_missing == ["has_ci"]
    assert ctx.adapted_config["complexity"]["max_file_lines"] == 600


# ============================================
# get_session_context() integration
# ============================================


def test_get_session_context_empty_project(tmp_path):
    """Empty project returns MIXED mode + DECIDE phase."""
    with mock.patch("vibesrails.context.ContextDetector") as mock_det, \
         mock.patch("vibesrails.context.ContextScorer") as mock_scorer:
        from vibesrails.context.mode import ContextScore

        mock_det.return_value.read_forced_mode.return_value = None
        mock_det.return_value.detect.return_value = mock.Mock()
        mock_scorer.return_value.score.return_value = ContextScore(
            score=0.5, mode=SessionMode.MIXED, confidence=0.0, signal_scores={}
        )
        ctx = get_session_context(tmp_path)

    assert ctx.mode == SessionMode.MIXED
    assert ctx.phase == ProjectPhase.DECIDE.value
    assert ctx.phase_name == "DECIDE"
    assert not ctx.mode_forced
    assert not ctx.phase_is_override
    assert isinstance(ctx.adapted_config, dict)


def test_get_session_context_forced_mode(tmp_path):
    """Forced mode sets mode_forced=True."""
    with mock.patch("vibesrails.context.ContextDetector") as mock_det:
        mock_det.return_value.read_forced_mode.return_value = "bugfix"
        ctx = get_session_context(tmp_path)

    assert ctx.mode == SessionMode.BUGFIX
    assert ctx.mode_forced is True
    assert ctx.mode_score == 0.5
    assert ctx.mode_confidence == 0.0


def test_get_session_context_with_phase_override(tmp_path):
    """Phase override from methodology.yaml is reflected."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": 2}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    with mock.patch("vibesrails.context.ContextDetector") as mock_det, \
         mock.patch("vibesrails.context.ContextScorer") as mock_scorer:
        from vibesrails.context.mode import ContextScore

        mock_det.return_value.read_forced_mode.return_value = None
        mock_det.return_value.detect.return_value = mock.Mock()
        mock_scorer.return_value.score.return_value = ContextScore(
            score=0.5, mode=SessionMode.MIXED, confidence=0.0, signal_scores={}
        )
        ctx = get_session_context(tmp_path)

    assert ctx.phase == ProjectPhase.FLESH_OUT.value
    assert ctx.phase_name == "FLESH OUT"
    assert ctx.phase_is_override is True


def test_get_session_context_adapted_config_has_phase(tmp_path):
    """Adapted config contains _phase and _phase_flags from adapter."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": 0}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    with mock.patch("vibesrails.context.ContextDetector") as mock_det, \
         mock.patch("vibesrails.context.ContextScorer") as mock_scorer:
        from vibesrails.context.mode import ContextScore

        mock_det.return_value.read_forced_mode.return_value = None
        mock_det.return_value.detect.return_value = mock.Mock()
        mock_scorer.return_value.score.return_value = ContextScore(
            score=0.85, mode=SessionMode.RND, confidence=0.9, signal_scores={}
        )
        ctx = get_session_context(tmp_path)

    # DECIDE phase flags should be in adapted config
    assert ctx.adapted_config.get("_phase") == 0
    flags = ctx.adapted_config.get("_phase_flags", {})
    assert flags.get("block_without_adr") is True


def test_get_session_context_mode_plus_phase_merge(tmp_path):
    """RND mode + DECIDE phase: brief_enforcer min_score = 80 (phase wins)."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    config = {"methodology": {"current_phase": 0}}
    (vr / "methodology.yaml").write_text(yaml.dump(config))

    with mock.patch("vibesrails.context.ContextDetector") as mock_det, \
         mock.patch("vibesrails.context.ContextScorer") as mock_scorer:
        from vibesrails.context.mode import ContextScore

        mock_det.return_value.read_forced_mode.return_value = None
        mock_det.return_value.detect.return_value = mock.Mock()
        mock_scorer.return_value.score.return_value = ContextScore(
            score=0.85, mode=SessionMode.RND, confidence=0.9, signal_scores={}
        )
        ctx = get_session_context(tmp_path)

    # RND min_score=30, DECIDE min_score=80 → phase wins
    assert ctx.adapted_config.get("brief_enforcer", {}).get("min_score") == 80


# ============================================
# Preflight integration
# ============================================


def test_preflight_shows_session_context(tmp_path):
    """Preflight check_session_context returns unified info."""
    from vibesrails.preflight import check_session_context

    results = check_session_context(tmp_path)
    assert len(results) >= 1
    # Should contain a "Session" result with mode + phase info
    session_result = next(r for r in results if r.name == "Session")
    assert "Phase" in session_result.message
    # Mode info (MIXED since empty project with no git)
    assert any(
        word in session_result.message
        for word in ("R&D", "Mixed", "Bugfix", "forced")
    )


def test_preflight_session_context_shows_gate(tmp_path):
    """Preflight shows next phase gate when not at DEPLOY."""
    from vibesrails.preflight import check_session_context

    results = check_session_context(tmp_path)
    gate_results = [r for r in results if r.name == "Next phase gate"]
    # Empty project = DECIDE phase, should show gate to SKELETON
    assert len(gate_results) == 1
    assert "SKELETON" in gate_results[0].message
