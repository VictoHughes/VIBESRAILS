"""Tests for context adapter — threshold adjustment by session mode."""

import copy

from vibesrails.context.adapter import (
    PROFILES,
    ContextAdapter,
    _deep_merge,
)
from vibesrails.context.mode import SessionMode

# ============================================
# _deep_merge
# ============================================


def test_deep_merge_flat():
    """Flat keys are merged."""
    base = {"a": 1, "b": 2}
    overlay = {"b": 3, "c": 4}
    result = _deep_merge(base, overlay)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested():
    """Nested dicts are recursively merged."""
    base = {"x": {"a": 1, "b": 2}}
    overlay = {"x": {"b": 3, "c": 4}}
    result = _deep_merge(base, overlay)
    assert result == {"x": {"a": 1, "b": 3, "c": 4}}


def test_deep_merge_no_mutation():
    """Original dicts are not mutated."""
    base = {"x": {"a": 1}}
    overlay = {"x": {"b": 2}}
    base_copy = copy.deepcopy(base)
    overlay_copy = copy.deepcopy(overlay)
    _deep_merge(base, overlay)
    assert base == base_copy
    assert overlay == overlay_copy


# ============================================
# PROFILES constants
# ============================================


def test_profiles_rnd_exists():
    """RND profile has expected keys."""
    profile = PROFILES[SessionMode.RND]
    assert "file_too_long" in profile
    assert "diff_size" in profile
    assert "complexity" in profile
    assert "brief_enforcer" in profile


def test_profiles_mixed_empty():
    """MIXED profile is empty (no changes)."""
    assert PROFILES[SessionMode.MIXED] == {}


def test_profiles_bugfix_exists():
    """BUGFIX profile has expected keys."""
    profile = PROFILES[SessionMode.BUGFIX]
    assert "file_too_long" in profile
    assert "diff_size" in profile
    assert "complexity" in profile
    assert "brief_enforcer" in profile


def test_profiles_rnd_more_lenient_than_bugfix():
    """RND thresholds are more lenient than BUGFIX."""
    rnd = PROFILES[SessionMode.RND]
    bugfix = PROFILES[SessionMode.BUGFIX]
    assert rnd["file_too_long"]["threshold"] > bugfix["file_too_long"]["threshold"]
    assert rnd["diff_size"]["warn"] > bugfix["diff_size"]["warn"]
    assert rnd["diff_size"]["block"] > bugfix["diff_size"]["block"]
    assert rnd["complexity"]["cyclomatic_warn"] > bugfix["complexity"]["cyclomatic_warn"]
    assert rnd["brief_enforcer"]["min_score"] < bugfix["brief_enforcer"]["min_score"]


# ============================================
# ContextAdapter.get_profile
# ============================================


def test_get_profile_rnd():
    """RND profile returned correctly."""
    adapter = ContextAdapter()
    profile = adapter.get_profile(SessionMode.RND)
    assert profile["file_too_long"]["threshold"] == 600


def test_get_profile_mixed():
    """MIXED profile returns empty dict."""
    adapter = ContextAdapter()
    profile = adapter.get_profile(SessionMode.MIXED)
    assert profile == {}


def test_get_profile_bugfix():
    """BUGFIX profile returned correctly."""
    adapter = ContextAdapter()
    profile = adapter.get_profile(SessionMode.BUGFIX)
    assert profile["file_too_long"]["threshold"] == 300


def test_get_profile_with_yaml_override():
    """YAML overrides are merged into profile."""
    overrides = {"rnd": {"file_too_long": {"threshold": 800}}}
    adapter = ContextAdapter(yaml_overrides=overrides)
    profile = adapter.get_profile(SessionMode.RND)
    assert profile["file_too_long"]["threshold"] == 800
    # Other keys preserved
    assert profile["diff_size"]["warn"] == 300


def test_get_profile_yaml_override_adds_new_key():
    """YAML overrides can add new keys to profile."""
    overrides = {"bugfix": {"custom_check": {"enabled": True}}}
    adapter = ContextAdapter(yaml_overrides=overrides)
    profile = adapter.get_profile(SessionMode.BUGFIX)
    assert profile["custom_check"]["enabled"] is True
    assert profile["file_too_long"]["threshold"] == 300


def test_get_profile_returns_fresh_copy():
    """Each call returns a new dict — safe to mutate."""
    adapter = ContextAdapter()
    p1 = adapter.get_profile(SessionMode.RND)
    p2 = adapter.get_profile(SessionMode.RND)
    assert p1 == p2
    p1["file_too_long"]["threshold"] = 999
    assert p2["file_too_long"]["threshold"] == 600


# ============================================
# ContextAdapter.adapt_config
# ============================================


def test_adapt_config_mixed_unchanged():
    """MIXED mode returns a copy without modifications."""
    config = {"complexity": {"max_file_lines": 400}}
    adapter = ContextAdapter()
    adapted = adapter.adapt_config(SessionMode.MIXED, config)
    assert adapted == config
    assert adapted is not config  # must be a copy


def test_adapt_config_rnd_file_too_long():
    """RND mode increases max_file_lines."""
    config = {"complexity": {"max_file_lines": 400}}
    adapter = ContextAdapter()
    adapted = adapter.adapt_config(SessionMode.RND, config)
    assert adapted["complexity"]["max_file_lines"] == 600
    assert adapted["complexity"]["file_too_long_severity"] == "WARN"


def test_adapt_config_bugfix_file_too_long():
    """BUGFIX mode decreases max_file_lines and blocks."""
    config = {"complexity": {"max_file_lines": 400}}
    adapter = ContextAdapter()
    adapted = adapter.adapt_config(SessionMode.BUGFIX, config)
    assert adapted["complexity"]["max_file_lines"] == 300
    assert adapted["complexity"]["file_too_long_severity"] == "BLOCK"


def test_adapt_config_no_mutation():
    """Original config is not mutated."""
    config = {"complexity": {"max_file_lines": 400}}
    config_copy = copy.deepcopy(config)
    adapter = ContextAdapter()
    adapter.adapt_config(SessionMode.BUGFIX, config)
    assert config == config_copy


def test_adapt_config_creates_missing_keys():
    """Adapt creates complexity/guardian keys if missing."""
    config = {}
    adapter = ContextAdapter()
    adapted = adapter.adapt_config(SessionMode.RND, config)
    assert adapted["complexity"]["max_file_lines"] == 600
    assert adapted["guardian"]["max_file_lines"] == 600


def test_adapt_config_guardian_max_file_lines():
    """Guardian.max_file_lines is adapted for pre_tool_use hook."""
    config = {"guardian": {"max_file_lines": 300}}
    adapter = ContextAdapter()
    adapted = adapter.adapt_config(SessionMode.RND, config)
    assert adapted["guardian"]["max_file_lines"] == 600


# ============================================
# ContextAdapter.format_adjustments
# ============================================


def test_format_adjustments_mixed():
    """MIXED mode shows no adjustments."""
    adapter = ContextAdapter()
    lines = adapter.format_adjustments(SessionMode.MIXED)
    assert lines == ["No threshold adjustments (default mode)"]


def test_format_adjustments_rnd():
    """RND mode shows relaxed thresholds."""
    adapter = ContextAdapter()
    lines = adapter.format_adjustments(SessionMode.RND)
    assert any("file_too_long" in line for line in lines)
    assert any("600" in line for line in lines)
    assert any("diff_size" in line for line in lines)


def test_format_adjustments_bugfix():
    """BUGFIX mode shows strict thresholds."""
    adapter = ContextAdapter()
    lines = adapter.format_adjustments(SessionMode.BUGFIX)
    assert any("300" in line for line in lines)
    assert any("BLOCK" in line for line in lines)


# ============================================
# get_current_mode
# ============================================


def test_get_current_mode_forced(tmp_path):
    """Forced mode returns the forced mode with no score."""
    from unittest import mock

    from vibesrails.context import get_current_mode

    with mock.patch("vibesrails.context.ContextDetector") as mock_cls:
        instance = mock_cls.return_value
        instance.read_forced_mode.return_value = "bugfix"
        mode, score = get_current_mode(tmp_path)
    assert mode == SessionMode.BUGFIX
    assert score is None


def test_get_current_mode_auto(tmp_path):
    """Auto mode detects and returns score."""
    from unittest import mock

    from vibesrails.context import get_current_mode
    from vibesrails.context.mode import ContextScore, ContextSignals

    fake_score = ContextScore(
        score=0.8, mode=SessionMode.RND, confidence=0.9, signal_scores={}
    )
    with mock.patch("vibesrails.context.ContextDetector") as mock_det, \
         mock.patch("vibesrails.context.ContextScorer") as mock_scorer:
        mock_det.return_value.read_forced_mode.return_value = None
        mock_det.return_value.detect.return_value = ContextSignals()
        mock_scorer.return_value.score.return_value = fake_score
        mode, score = get_current_mode(tmp_path)
    assert mode == SessionMode.RND
    assert score is fake_score
