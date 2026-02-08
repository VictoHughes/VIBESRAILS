"""MCP tool: monitor_entropy — track AI coding session entropy.

Wraps core/session_tracker.py as an MCP-callable tool.
Monitors session health via entropy scoring: duration, files modified,
violations, and LOC changes contribute to a risk score [0.0-1.0].
"""

from __future__ import annotations

import logging

from core.input_validator import (
    InputValidationError,
    validate_int,
    validate_list,
)
from core.session_tracker import SessionTracker, classify_entropy

logger = logging.getLogger(__name__)

# ── Pedagogy per entropy level ────────────────────────────────────────

ENTROPY_PEDAGOGY: dict[str, dict[str, str]] = {
    "safe": {
        "why": "Session under control. Good pace.",
        "recommendation": (
            "Keep going. Consider committing your work at regular intervals "
            "and running scans to maintain code quality."
        ),
    },
    "warning": {
        "why": (
            "Attention: {minutes:.0f}min of session. Studies show 88% hallucination "
            "rate after 20min of continuous AI sessions (Rev 2025, 1038 respondents). "
            "Consider a validation checkpoint."
        ),
        "recommendation": (
            "Commit your current work, run a full scan (scan_code + scan_senior), "
            "and review the AI-generated code before continuing."
        ),
    },
    "elevated": {
        "why": (
            "Session at risk. {files} files modified, {violations} violations detected. "
            "The likelihood of architectural inconsistencies is increasing."
        ),
        "recommendation": (
            "Commit the current state and launch a complete scan before continuing. "
            "Consider splitting your remaining work into a new session."
        ),
    },
    "critical": {
        "why": (
            "STOP recommended. Critical entropy ({score:.2f}). At this level, "
            "generated code has a high probability of containing architectural "
            "inconsistencies and hallucinated patterns."
        ),
        "recommendation": (
            "Action: git stash, review everything generated so far, then start "
            "a fresh session. Rule of thumb: 1 session = 1 feature = max 20 minutes."
        ),
    },
}


# ── Helpers ───────────────────────────────────────────────────────────

def _build_pedagogy(level: str, score: float, minutes: float, files: int, violations: int) -> dict:
    """Build contextual pedagogy for the current entropy level."""
    template = ENTROPY_PEDAGOGY.get(level, ENTROPY_PEDAGOGY["safe"])
    return {
        "why": template["why"].format(
            score=score, minutes=minutes, files=files, violations=violations
        ),
        "recommendation": template["recommendation"].format(
            score=score, minutes=minutes, files=files, violations=violations
        ),
    }


# ── Core logic ────────────────────────────────────────────────────────

def monitor_entropy(
    action: str,
    project_path: str | None = None,
    session_id: str | None = None,
    files_modified: list[str] | None = None,
    changes_loc: int | None = None,
    violations: int | None = None,
    db_path: str | None = None,
) -> dict:
    """Monitor AI coding session entropy.

    Args:
        action: "start", "update", "status", or "end".
        project_path: Project path (required for "start").
        session_id: Session ID (required for "update", "status", "end").
        files_modified: List of modified file paths (for "update").
        changes_loc: Lines of code changed (for "update").
        violations: Number of violations detected (for "update").
        db_path: SQLite DB path override (for testing).

    Returns:
        Dict with status, session_id, entropy_score, entropy_level,
        session_duration_minutes, pedagogy.
    """
    valid_actions = ("start", "update", "status", "end")
    if action not in valid_actions:
        return _error_result(
            f"Invalid action: {action!r}. Must be one of: {', '.join(valid_actions)}"
        )

    # Validate inputs
    try:
        if changes_loc is not None:
            validate_int(changes_loc, "changes_loc", min_val=0, max_val=1_000_000)
        if violations is not None:
            validate_int(violations, "violations", min_val=0, max_val=100_000)
        if files_modified is not None:
            validate_list(files_modified, "files_modified", max_items=10_000, item_type=str)
    except InputValidationError as exc:
        return _error_result(str(exc))

    tracker = SessionTracker(db_path=db_path)

    if action == "start":
        return _handle_start(tracker, project_path)
    elif action == "update":
        return _handle_update(tracker, session_id, files_modified, changes_loc, violations)
    elif action == "status":
        return _handle_status(tracker, session_id)
    else:  # end
        return _handle_end(tracker, session_id)


def _handle_start(tracker: SessionTracker, project_path: str | None) -> dict:
    """Handle action=start."""
    if not project_path:
        return _error_result("project_path is required for action='start'")

    sid = tracker.start_session(project_path)
    return {
        "status": "ok",
        "session_id": sid,
        "entropy_score": 0.0,
        "entropy_level": "safe",
        "session_duration_minutes": 0.0,
        "pedagogy": _build_pedagogy("safe", 0.0, 0.0, 0, 0),
    }


def _handle_update(
    tracker: SessionTracker,
    session_id: str | None,
    files_modified: list[str] | None,
    changes_loc: int | None,
    violations: int | None,
) -> dict:
    """Handle action=update."""
    if not session_id:
        return _error_result("session_id is required for action='update'")

    try:
        entropy = tracker.update_session(
            session_id,
            files_modified=files_modified,
            changes_loc=changes_loc or 0,
            violations=violations or 0,
        )
    except ValueError as exc:
        return _error_result(str(exc))

    session = tracker.get_session(session_id)
    level = classify_entropy(entropy)

    return {
        "status": "ok",
        "session_id": session_id,
        "entropy_score": round(entropy, 4),
        "entropy_level": level,
        "session_duration_minutes": session["duration_minutes"] if session else 0.0,
        "pedagogy": _build_pedagogy(
            level, entropy,
            session["duration_minutes"] if session else 0.0,
            len(session["files_modified"]) if session else 0,
            session["violations_count"] if session else 0,
        ),
    }


def _handle_status(tracker: SessionTracker, session_id: str | None) -> dict:
    """Handle action=status."""
    if not session_id:
        return _error_result("session_id is required for action='status'")

    session = tracker.get_session(session_id)
    if session is None:
        return _error_result(f"Session not found: {session_id}")

    try:
        entropy = tracker.get_entropy(session_id)
    except ValueError as exc:
        return _error_result(str(exc))

    level = classify_entropy(entropy)

    return {
        "status": "ok",
        "session_id": session_id,
        "entropy_score": round(entropy, 4),
        "entropy_level": level,
        "session_duration_minutes": session["duration_minutes"],
        "files_modified": session["files_modified"],
        "total_changes_loc": session["total_changes_loc"],
        "violations_count": session["violations_count"],
        "pedagogy": _build_pedagogy(
            level, entropy,
            session["duration_minutes"],
            len(session["files_modified"]),
            session["violations_count"],
        ),
    }


def _handle_end(tracker: SessionTracker, session_id: str | None) -> dict:
    """Handle action=end."""
    if not session_id:
        return _error_result("session_id is required for action='end'")

    try:
        summary = tracker.end_session(session_id)
    except ValueError as exc:
        return _error_result(str(exc))

    level = summary["entropy_level"]
    entropy = summary["final_entropy"]

    return {
        "status": "ok",
        "session_id": session_id,
        "entropy_score": entropy,
        "entropy_level": level,
        "session_duration_minutes": summary["duration_minutes"],
        "session_summary": summary,
        "pedagogy": _build_pedagogy(
            level, entropy,
            summary["duration_minutes"],
            len(summary["files_modified"]),
            summary["violations_count"],
        ),
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "session_id": None,
        "entropy_score": None,
        "entropy_level": None,
        "session_duration_minutes": None,
        "error": message,
    }
