"""Tests for context mode types and boundaries."""

from vibesrails.context.mode import (
    BUGFIX_THRESHOLD,
    RND_THRESHOLD,
    ContextScore,
    ContextSignals,
    SessionMode,
)

# ============================================
# SessionMode.from_score boundaries
# ============================================


def test_from_score_bugfix():
    """Score below threshold returns BUGFIX."""
    assert SessionMode.from_score(0.0) == SessionMode.BUGFIX
    assert SessionMode.from_score(0.1) == SessionMode.BUGFIX
    assert SessionMode.from_score(0.29) == SessionMode.BUGFIX


def test_from_score_mixed():
    """Score in middle range returns MIXED."""
    assert SessionMode.from_score(0.3) == SessionMode.MIXED
    assert SessionMode.from_score(0.5) == SessionMode.MIXED
    assert SessionMode.from_score(0.7) == SessionMode.MIXED


def test_from_score_rnd():
    """Score above threshold returns RND."""
    assert SessionMode.from_score(0.71) == SessionMode.RND
    assert SessionMode.from_score(0.9) == SessionMode.RND
    assert SessionMode.from_score(1.0) == SessionMode.RND


def test_from_score_exact_boundaries():
    """Exact boundary values: 0.3 = MIXED, 0.7 = MIXED."""
    assert SessionMode.from_score(BUGFIX_THRESHOLD) == SessionMode.MIXED
    assert SessionMode.from_score(RND_THRESHOLD) == SessionMode.MIXED


# ============================================
# ContextSignals defaults
# ============================================


def test_context_signals_defaults():
    """All optional fields default to None."""
    s = ContextSignals()
    assert s.branch_name == ""
    assert s.branch_type == "unknown"
    assert s.uncommitted_count is None
    assert s.files_created_ratio is None
    assert s.commit_frequency is None
    assert s.diff_spread is None


# ============================================
# ContextScore
# ============================================


def test_context_score_creation():
    """ContextScore can be created with all fields."""
    cs = ContextScore(
        score=0.75,
        mode=SessionMode.RND,
        confidence=0.8,
        signal_scores={"branch_type": 0.7},
    )
    assert cs.score == 0.75
    assert cs.mode == SessionMode.RND
    assert cs.confidence == 0.8


# ============================================
# SessionMode enum values
# ============================================


def test_session_mode_values():
    """All mode values are as expected."""
    assert SessionMode.RND.value == "rnd"
    assert SessionMode.MIXED.value == "mixed"
    assert SessionMode.BUGFIX.value == "bugfix"
    assert SessionMode.FORCED.value == "forced"
