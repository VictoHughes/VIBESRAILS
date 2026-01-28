"""File placement and duplication validation."""

# Re-export AI guardian functions for backward compatibility
from ..ai_guardian import (
    AI_ENV_MARKERS,
    apply_guardian_rules,
    get_ai_agent_name,
    get_guardian_config,
    get_guardian_stats,
    get_stricter_patterns,
    is_ai_session,
    log_guardian_block,
    print_guardian_status,
    should_apply_guardian,
    show_guardian_stats,
)
from .dialogue import InteractiveDialogue
from .duplication_guard import DuplicationGuard, DuplicationResult
from .placement_guard import PlacementGuard, PlacementResult

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
