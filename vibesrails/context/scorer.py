"""Context scorer — weighted scoring of signals into session mode."""

from __future__ import annotations

from .mode import ContextScore, ContextSignals, SessionMode

# Weights for each signal (must sum to 1.0)
WEIGHTS = {
    "branch_type": 0.35,
    "files_created_ratio": 0.25,
    "uncommitted_count": 0.15,
    "commit_frequency": 0.15,
    "diff_spread": 0.10,
}

# Branch type → R&D score (0.0 = bugfix, 1.0 = R&D)
_BRANCH_SCORES: dict[str, float] = {
    "fix": 0.0,
    "unknown": 0.5,
    "feature": 0.7,
    "spike": 1.0,
}

# Uncommitted count thresholds
_UNCOMMITTED_LOW = 2   # ≤2 files → bugfix-like (focused)
_UNCOMMITTED_HIGH = 10  # ≥10 files → R&D-like (broad)

# Commit frequency thresholds (commits/hour)
_FREQ_HIGH = 5  # ≥5/h → bugfix-like (rapid patches)
_FREQ_LOW = 2   # ≤2/h → R&D-like (exploring)

# Diff spread thresholds (unique dirs)
_SPREAD_LOW = 2   # ≤2 dirs → bugfix-like (focused)
_SPREAD_HIGH = 5  # ≥5 dirs → R&D-like (broad changes)


def _score_branch(branch_type: str) -> float:
    return _BRANCH_SCORES.get(branch_type, 0.5)


def _score_files_created_ratio(ratio: float) -> float:
    """Mostly creates → R&D, mostly modifies → bugfix."""
    return min(1.0, ratio)


def _score_uncommitted(count: int) -> float:
    """Many files → R&D, few files → bugfix."""
    if count <= _UNCOMMITTED_LOW:
        return 0.1
    if count >= _UNCOMMITTED_HIGH:
        return 0.9
    return 0.1 + 0.8 * (count - _UNCOMMITTED_LOW) / (_UNCOMMITTED_HIGH - _UNCOMMITTED_LOW)


def _score_commit_frequency(freq: int) -> float:
    """High freq → bugfix (0.1), low freq → R&D (0.8)."""
    if freq >= _FREQ_HIGH:
        return 0.1
    if freq <= _FREQ_LOW:
        return 0.8
    # Linear interpolation: high freq = low score
    return 0.8 - 0.7 * (freq - _FREQ_LOW) / (_FREQ_HIGH - _FREQ_LOW)


def _score_diff_spread(spread: int) -> float:
    """Many dirs → R&D, few dirs → bugfix."""
    if spread <= _SPREAD_LOW:
        return 0.1
    if spread >= _SPREAD_HIGH:
        return 0.9
    return 0.1 + 0.8 * (spread - _SPREAD_LOW) / (_SPREAD_HIGH - _SPREAD_LOW)


class ContextScorer:
    """Scores context signals into a session mode classification."""

    def score(self, signals: ContextSignals) -> ContextScore:
        """Compute weighted score from signals. Skips None signals."""
        scored: dict[str, float] = {}
        available_weight = 0.0

        # Branch type (always available if branch_name is set)
        if signals.branch_name:
            scored["branch_type"] = _score_branch(signals.branch_type)
            available_weight += WEIGHTS["branch_type"]

        if signals.files_created_ratio is not None:
            scored["files_created_ratio"] = _score_files_created_ratio(
                signals.files_created_ratio
            )
            available_weight += WEIGHTS["files_created_ratio"]

        if signals.uncommitted_count is not None:
            scored["uncommitted_count"] = _score_uncommitted(signals.uncommitted_count)
            available_weight += WEIGHTS["uncommitted_count"]

        if signals.commit_frequency is not None:
            scored["commit_frequency"] = _score_commit_frequency(
                signals.commit_frequency
            )
            available_weight += WEIGHTS["commit_frequency"]

        if signals.diff_spread is not None:
            scored["diff_spread"] = _score_diff_spread(signals.diff_spread)
            available_weight += WEIGHTS["diff_spread"]

        # Weighted average (redistribute weights proportionally)
        if not scored or available_weight == 0:
            return ContextScore(
                score=0.5,
                mode=SessionMode.MIXED,
                confidence=0.0,
                signal_scores={},
            )

        weighted_sum = sum(
            scored[name] * WEIGHTS[name] / available_weight
            for name in scored
        )
        confidence = available_weight / sum(WEIGHTS.values())

        return ContextScore(
            score=round(weighted_sum, 3),
            mode=SessionMode.from_score(weighted_sum),
            confidence=round(confidence, 2),
            signal_scores=scored,
        )
