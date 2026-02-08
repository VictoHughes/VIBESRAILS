"""MCP tool: check_drift — measure architectural drift velocity.

Wraps core/drift_tracker.py as an MCP-callable tool.
Takes a project snapshot, computes the rate of architectural change
compared to the previous snapshot, and flags excessive drift.
"""

from __future__ import annotations

import logging

from core.drift_tracker import DriftTracker
from core.input_validator import InputValidationError, validate_optional_string
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path

logger = logging.getLogger(__name__)

# ── Pedagogy per velocity level ──────────────────────────────────────

VELOCITY_PEDAGOGY: dict[str, dict[str, str]] = {
    "normal": {
        "why": "Architecture stable. Drift minimal entre sessions.",
        "recommendation": (
            "Continue as planned. The codebase is evolving at a healthy pace. "
            "Take snapshots regularly to maintain this baseline."
        ),
    },
    "warning": {
        "why": (
            "Drift en hausse ({velocity:.1f}%). {highest_metric} a le plus "
            "change. Verifiez que ces changements sont intentionnels."
        ),
        "recommendation": (
            "Review the recent changes to {highest_metric}. "
            "If this is intentional, document the architectural decision. "
            "If not, consider reverting."
        ),
    },
    "critical": {
        "why": (
            "Drift critique ({velocity:.1f}%). L'architecture diverge "
            "rapidement de sa baseline. Risque: l'IA genere du code qui "
            "s'eloigne du design original. Recommandation: review "
            "architectural avant de continuer."
        ),
        "recommendation": (
            "STOP and review. Compare the current architecture with the "
            "initial design. Run scan_code + scan_senior before continuing. "
            "Consider splitting changes into smaller sessions."
        ),
    },
}

_REVIEW_REQUIRED_PEDAGOGY = {
    "why": (
        "3+ sessions consecutives avec drift >10%. Pattern detecte: "
        "l'architecture se transforme progressivement sans supervision. "
        "C'est le mode de defaillance #1 du vibe coding."
    ),
    "recommendation": (
        "Full architectural review required. Compare current codebase "
        "with the initial design document. Consider: (1) Are these changes "
        "intentional? (2) Is the AI following the original architecture? "
        "(3) Should you reset to a known-good state?"
    ),
}

_BASELINE_PEDAGOGY = {
    "why": (
        "First snapshot recorded — this is the architectural baseline. "
        "Future scans will compare against this to detect drift."
    ),
    "recommendation": (
        "Run check_drift again after your next coding session to start "
        "tracking velocity. Aim for snapshots at session boundaries."
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────

def _find_highest_metric(metrics_delta: dict) -> str:
    """Find the metric with the highest % change."""
    if not metrics_delta:
        return "unknown"
    return max(
        metrics_delta,
        key=lambda k: metrics_delta[k].get("change_pct", 0),
    )


def _build_pedagogy(
    level: str,
    velocity: float,
    highest_metric: str,
    review_required: bool,
) -> dict:
    """Build contextual pedagogy for the velocity level."""
    if review_required:
        return _REVIEW_REQUIRED_PEDAGOGY

    template = VELOCITY_PEDAGOGY.get(level, VELOCITY_PEDAGOGY["normal"])
    return {
        "why": template["why"].format(
            velocity=velocity, highest_metric=highest_metric,
        ),
        "recommendation": template["recommendation"].format(
            velocity=velocity, highest_metric=highest_metric,
        ),
    }


# ── Core logic ────────────────────────────────────────────────────────

def check_drift(
    project_path: str,
    session_id: str | None = None,
    db_path: str | None = None,
) -> dict:
    """Take a project snapshot and compute drift velocity.

    Args:
        project_path: Path to the project directory.
        session_id: Optional session ID to associate with this snapshot.
        db_path: SQLite DB path override (for testing).

    Returns:
        Dict with status, velocity_score, velocity_level, trend,
        metrics_delta, consecutive_high, review_required, pedagogy.
    """
    try:
        validate_path(project_path, must_exist=True, must_be_dir=True)
    except PathValidationError as exc:
        return _error_result(str(exc))

    try:
        validate_optional_string(session_id, "session_id", max_length=256)
    except InputValidationError as exc:
        return _error_result(str(exc))

    tracker = DriftTracker(db_path=db_path)

    # Take snapshot
    snapshot = tracker.take_snapshot(project_path, session_id=session_id)
    if "error" in snapshot:
        return _error_result(snapshot["error"])

    # Compute velocity (needs >=2 snapshots)
    velocity = tracker.compute_velocity(project_path)

    if velocity is None:
        # First snapshot — baseline
        return {
            "status": "info",
            "is_baseline": True,
            "snapshot": snapshot["metrics"],
            "velocity_score": None,
            "velocity_level": None,
            "trend": None,
            "metrics_delta": None,
            "consecutive_high": 0,
            "review_required": False,
            "pedagogy": _BASELINE_PEDAGOGY,
        }

    level = velocity["velocity_level"]
    highest = _find_highest_metric(velocity["metrics_delta"])

    status = "pass" if level == "normal" else ("warn" if level == "warning" else "block")
    if velocity["review_required"]:
        status = "block"

    # Feed Learning Engine
    record_safe(session_id, "drift", {
        "velocity": velocity["velocity_score"],
        "highest_metric": highest,
    })

    return {
        "status": status,
        "is_baseline": False,
        "snapshot": snapshot["metrics"],
        "velocity_score": velocity["velocity_score"],
        "velocity_level": level,
        "trend": velocity["trend"],
        "metrics_delta": velocity["metrics_delta"],
        "consecutive_high": velocity["consecutive_high"],
        "review_required": velocity["review_required"],
        "pedagogy": _build_pedagogy(
            level, velocity["velocity_score"], highest,
            velocity["review_required"],
        ),
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "is_baseline": False,
        "snapshot": None,
        "velocity_score": None,
        "velocity_level": None,
        "trend": None,
        "metrics_delta": None,
        "consecutive_high": 0,
        "review_required": False,
        "error": message,
    }
