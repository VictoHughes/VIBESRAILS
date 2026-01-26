"""File placement and duplication validation."""

from .placement_guard import PlacementGuard, PlacementResult
from .duplication_guard import DuplicationGuard, DuplicationResult
from .dialogue import InteractiveDialogue

# Re-export AI guardian functions for backward compatibility
from ..ai_guardian import (
    AI_ENV_MARKERS,
    is_ai_session,
    get_ai_agent_name,
    get_guardian_config,
    should_apply_guardian,
    get_stricter_patterns,
    apply_guardian_rules,
    log_guardian_block,
    get_guardian_stats,
    show_guardian_stats,
    print_guardian_status,
)

__all__ = [
    # New 1.3.0 learning features
    "PlacementGuard",
    "PlacementResult",
    "DuplicationGuard",
    "DuplicationResult",
    "InteractiveDialogue",
    # Backward compatibility - AI guardian functions
    "AI_ENV_MARKERS",
    "is_ai_session",
    "get_ai_agent_name",
    "get_guardian_config",
    "should_apply_guardian",
    "get_stricter_patterns",
    "apply_guardian_rules",
    "log_guardian_block",
    "get_guardian_stats",
    "show_guardian_stats",
    "print_guardian_status",
]
