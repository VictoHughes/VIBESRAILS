"""Tests for context scorer — signal weighting and mode classification."""

from vibesrails.context.mode import ContextSignals, SessionMode
from vibesrails.context.scorer import (
    ContextScorer,
    _score_branch,
    _score_commit_frequency,
    _score_diff_spread,
    _score_files_created_ratio,
    _score_uncommitted,
)

# ============================================
# Individual signal scoring
# ============================================


def test_score_branch_fix():
    """Fix branch scores low (bugfix)."""
    assert _score_branch("fix") == 0.0


def test_score_branch_feature():
    """Feature branch scores high (R&D)."""
    assert _score_branch("feature") == 0.7


def test_score_branch_spike():
    """Spike branch scores maximum (R&D)."""
    assert _score_branch("spike") == 1.0


def test_score_branch_unknown():
    """Unknown branch scores middle."""
    assert _score_branch("unknown") == 0.5


def test_score_files_created_ratio():
    """High create ratio → R&D, low → bugfix."""
    assert _score_files_created_ratio(0.0) == 0.0
    assert _score_files_created_ratio(1.0) == 1.0
    assert _score_files_created_ratio(0.5) == 0.5


def test_score_uncommitted_few():
    """Few uncommitted files → bugfix score."""
    assert _score_uncommitted(0) == 0.1
    assert _score_uncommitted(1) == 0.1
    assert _score_uncommitted(2) == 0.1


def test_score_uncommitted_many():
    """Many uncommitted files → R&D score."""
    assert _score_uncommitted(10) == 0.9
    assert _score_uncommitted(20) == 0.9


def test_score_uncommitted_middle():
    """Mid-range uncommitted files → middle score."""
    score = _score_uncommitted(6)
    assert 0.3 < score < 0.7


def test_score_commit_frequency_high():
    """High commit frequency → low score (bugfix)."""
    assert _score_commit_frequency(5) == 0.1
    assert _score_commit_frequency(10) == 0.1


def test_score_commit_frequency_low():
    """Low commit frequency → high score (R&D)."""
    assert _score_commit_frequency(0) == 0.8
    assert _score_commit_frequency(1) == 0.8
    assert _score_commit_frequency(2) == 0.8


def test_score_commit_frequency_middle():
    """Mid-range frequency → middle score."""
    score = _score_commit_frequency(3)
    assert 0.2 < score < 0.7


def test_score_diff_spread_few():
    """Few dirs → bugfix score."""
    assert _score_diff_spread(1) == 0.1
    assert _score_diff_spread(2) == 0.1


def test_score_diff_spread_many():
    """Many dirs → R&D score."""
    assert _score_diff_spread(5) == 0.9
    assert _score_diff_spread(10) == 0.9


# ============================================
# ContextScorer.score
# ============================================


def test_score_all_bugfix_signals():
    """All bugfix signals → BUGFIX mode."""
    signals = ContextSignals(
        branch_name="fix/null-check",
        branch_type="fix",
        uncommitted_count=1,
        files_created_ratio=0.0,
        commit_frequency=8,
        diff_spread=1,
    )
    result = ContextScorer().score(signals)
    assert result.mode == SessionMode.BUGFIX
    assert result.score < 0.3
    assert result.confidence == 1.0


def test_score_all_rnd_signals():
    """All R&D signals → RND mode."""
    signals = ContextSignals(
        branch_name="spike/new-algo",
        branch_type="spike",
        uncommitted_count=15,
        files_created_ratio=0.9,
        commit_frequency=0,
        diff_spread=8,
    )
    result = ContextScorer().score(signals)
    assert result.mode == SessionMode.RND
    assert result.score > 0.7
    assert result.confidence == 1.0


def test_score_no_signals():
    """No signals → MIXED with zero confidence."""
    signals = ContextSignals()
    result = ContextScorer().score(signals)
    assert result.mode == SessionMode.MIXED
    assert result.confidence == 0.0
    assert result.score == 0.5


def test_score_partial_signals():
    """Partial signals → reduced confidence."""
    signals = ContextSignals(
        branch_name="feat/auth",
        branch_type="feature",
        uncommitted_count=3,
        # files_created_ratio=None → skipped
        # commit_frequency=None → skipped
        # diff_spread=None → skipped
    )
    result = ContextScorer().score(signals)
    assert 0.0 < result.confidence < 1.0
    assert len(result.signal_scores) == 2  # branch + uncommitted


def test_score_branch_only():
    """Branch-only signals still produce a score."""
    signals = ContextSignals(
        branch_name="fix/urgent",
        branch_type="fix",
    )
    result = ContextScorer().score(signals)
    assert result.mode == SessionMode.BUGFIX
    assert result.confidence == 0.35  # branch weight only
    assert result.score == 0.0


def test_score_signal_scores_populated():
    """Signal scores dict contains scored signals."""
    signals = ContextSignals(
        branch_name="feat/x",
        branch_type="feature",
        uncommitted_count=5,
        files_created_ratio=0.5,
    )
    result = ContextScorer().score(signals)
    assert "branch_type" in result.signal_scores
    assert "uncommitted_count" in result.signal_scores
    assert "files_created_ratio" in result.signal_scores
    assert "commit_frequency" not in result.signal_scores
