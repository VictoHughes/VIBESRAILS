"""Learning Engine bridge — safe, fire-and-forget recording.

Provides get_engine() for lazy singleton access and record_safe()
which wraps record_event in try/except to never crash calling tools.
"""

from __future__ import annotations

import logging

from core.learning_engine import LearningEngine

logger = logging.getLogger(__name__)

_engine: LearningEngine | None = None


def get_engine(db_path: str | None = None) -> LearningEngine:
    """Get or create the LearningEngine instance.

    If db_path is provided, always creates a fresh instance (useful for
    testing).  Otherwise reuses the singleton.
    """
    global _engine
    if db_path is not None:
        return LearningEngine(db_path=db_path)
    if _engine is None:
        _engine = LearningEngine()
    return _engine


def record_safe(
    session_id: str | None,
    event_type: str,
    event_data: dict,
    db_path: str | None = None,
) -> None:
    """Record a learning event, swallowing any exception.

    This is the main entry point for tools to feed the Learning Engine.
    It NEVER raises — if anything goes wrong, it logs and returns silently.
    """
    try:
        engine = get_engine(db_path=db_path)
        engine.record_event(
            session_id=session_id or "anonymous",
            event_type=event_type,
            event_data=event_data,
        )
    except Exception:
        logger.debug("learning_bridge: record_safe failed", exc_info=True)


def _reset() -> None:
    """Reset the singleton (for testing only)."""
    global _engine
    _engine = None
