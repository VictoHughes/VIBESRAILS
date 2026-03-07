"""Context detection — unified session mode + project phase."""

from __future__ import annotations

from pathlib import Path

from .adapter import PHASE_PROFILES, ContextAdapter
from .detector import ContextDetector
from .mode import ContextScore, ContextSignals, SessionContext, SessionMode
from .phase import PhaseDetector, PhaseResult, PhaseSignals, ProjectPhase
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


def get_session_context(
    root: Path | None = None,
    base_config: dict | None = None,
) -> SessionContext:
    """Detect session mode + project phase, return unified context.

    This is the recommended single entry point for context-aware decisions.
    Combines both dimensions and produces an adapted config.

    Args:
        root: Project root. Defaults to cwd.
        base_config: Scanner config to adapt. Defaults to empty dict.
    """
    if root is None:
        root = Path.cwd()
    if base_config is None:
        base_config = {}

    # ── Mode detection ──
    mode_forced = False
    detector = ContextDetector(root)
    forced = detector.read_forced_mode()
    if forced:
        mode = SessionMode(forced)
        mode_score = 0.5
        mode_confidence = 0.0
        mode_forced = True
    else:
        signals = detector.detect()
        score = ContextScorer().score(signals)
        mode = score.mode
        mode_score = score.score
        mode_confidence = score.confidence

    # ── Phase detection ──
    phase_detector = PhaseDetector(root)
    phase_result = phase_detector.detect()

    # ── Adapt config (mode + phase) ──
    adapter = ContextAdapter(base_config.get("session_profiles"))
    adapted = adapter.adapt_full_config(mode, phase_result.phase, base_config)

    return SessionContext(
        mode=mode,
        mode_score=mode_score,
        mode_confidence=mode_confidence,
        mode_forced=mode_forced,
        phase=phase_result.phase.value,
        phase_name=phase_result.phase.name.replace("_", " "),
        phase_is_override=phase_result.is_override,
        phase_missing=phase_result.missing_for_next,
        adapted_config=adapted,
    )


__all__ = [
    "ContextAdapter",
    "PHASE_PROFILES",
    "ContextDetector",
    "ContextScore",
    "ContextScorer",
    "ContextSignals",
    "SessionContext",
    "SessionMode",
    "get_current_mode",
    "get_session_context",
    "PhaseDetector",
    "PhaseResult",
    "PhaseSignals",
    "ProjectPhase",
]
