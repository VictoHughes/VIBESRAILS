"""File placement and duplication validation.

This package provides AI guardian features including placement validation,
duplication detection, and interactive dialogue for code review.
"""

from pathlib import Path

from .dialogue import InteractiveDialogue
from .duplication_guard import DuplicationGuard, DuplicationResult
from .placement_guard import PlacementGuard, PlacementResult
from .types import Signature

GUARDIAN_VERSION = "1.3.0"

GUARDIAN_CHECKS = ("placement", "duplication", "dialogue")


def create_placement_guard(cache_dir: Path) -> PlacementGuard:
    """Create a PlacementGuard with the given cache directory."""
    return PlacementGuard(cache_dir)


__all__ = [
    # Package API
    "GUARDIAN_VERSION",
    "GUARDIAN_CHECKS",
    "create_placement_guard",
    # Guardian features
    "PlacementGuard",
    "PlacementResult",
    "DuplicationGuard",
    "DuplicationResult",
    "InteractiveDialogue",
    "Signature",
]
