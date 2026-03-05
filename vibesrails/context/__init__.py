"""Context detection — dynamic R&D vs Bugfix session mode."""

from __future__ import annotations

from pathlib import Path

from .adapter import ContextAdapter
from .detector import ContextDetector
from .mode import ContextScore, ContextSignals, SessionMode
from .scorer import ContextScorer


def get_current_mode(root: Path | None = None) -> tuple[SessionMode, ContextScore | None]:
    """Detect or read the current session mode.

    Returns:
        (mode, score) — score is None if mode is forced.
    """
    if root is None:
        root = Path.cwd()

    detector = ContextDetector(root)

    # Check forced mode first
    forced = detector.read_forced_mode()
    if forced:
        mode = SessionMode(forced)
        return mode, None

    # Auto-detect from git signals
    signals = detector.detect()
    score = ContextScorer().score(signals)
    return score.mode, score


__all__ = [
    "ContextAdapter",
    "ContextDetector",
    "ContextScore",
    "ContextScorer",
    "ContextSignals",
    "SessionMode",
    "get_current_mode",
]
