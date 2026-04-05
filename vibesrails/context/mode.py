"""Session mode types — enums and dataclasses for context detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Score boundaries
BUGFIX_THRESHOLD = 0.3
RND_THRESHOLD = 0.7


class SessionMode(Enum):
    """Detected session mode."""

    RND = "rnd"
    MIXED = "mixed"
    BUGFIX = "bugfix"
    FORCED = "forced"

    @classmethod
    def from_score(cls, score: float) -> SessionMode:
        """Map a 0.0–1.0 score to a session mode."""
        if score < BUGFIX_THRESHOLD:
            return cls.BUGFIX
        if score > RND_THRESHOLD:
            return cls.RND
        return cls.MIXED


@dataclass
class ContextSignals:
    """Raw signals collected from git and filesystem."""

    branch_name: str = ""
    branch_type: str = "unknown"  # "feature"|"fix"|"spike"|"unknown"
    uncommitted_count: int | None = None
    files_created_ratio: float | None = None
    commit_frequency: int | None = None  # commits in last hour
    diff_spread: int | None = None  # unique dirs in last diff
    project_type: str = "unknown"  # "web"|"cli"|"library"|"data"|"ml"|"unknown"


@dataclass
class ContextScore:
    """Scored context with mode classification."""

    score: float
    mode: SessionMode
    confidence: float  # 0.0–1.0, proportion of available signals
    signal_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Unified context: mode (R&D/Bugfix) + phase (DECIDE→DEPLOY) + adapted config.

    This is the single entry point for all context-aware decisions.
    The phase field stores the ProjectPhase IntEnum value (0-4).
    """

    # Mode dimension (R&D vs Bugfix)
    mode: SessionMode
    mode_score: float  # 0.0–1.0 weighted score
    mode_confidence: float  # 0.0–1.0 signal confidence
    mode_forced: bool = False

    # Phase dimension (DECIDE→DEPLOY)
    phase: int = 0  # ProjectPhase IntEnum value (0-4)
    phase_name: str = "DECIDE"
    phase_is_override: bool = False
    phase_missing: list[str] = field(default_factory=list)

    # Adapted config (mode + phase merged)
    adapted_config: dict[str, Any] = field(default_factory=dict)
