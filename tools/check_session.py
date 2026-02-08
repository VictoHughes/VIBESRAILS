"""MCP tool: check_session — detect AI coding sessions and guardian status.

Wraps vibesrails AI Guardian as an MCP-callable tool.
Detects whether the current session is AI-assisted, identifies the agent,
and reports guardian mode configuration.
"""

from __future__ import annotations

import logging

from core.guardian import (
    AI_ENV_MARKERS,
    get_ai_agent_name,
    get_guardian_stats,
    is_ai_session,
)

logger = logging.getLogger(__name__)

# ── Pedagogy ──────────────────────────────────────────────────────────

SESSION_PEDAGOGY = {
    "ai_detected": {
        "why": (
            "AI coding tools (Claude Code, Cursor, Copilot, Aider…) set environment "
            "variables when active. Detecting the session lets VibesRails apply "
            "stricter rules automatically — because AI-generated code needs more "
            "scrutiny, not less."
        ),
        "recommendation": (
            "When an AI session is detected, enable Guardian Mode to escalate "
            "warnings and run Senior Guards automatically."
        ),
    },
    "no_ai_detected": {
        "why": (
            "No AI coding environment variables were found. This doesn't guarantee "
            "the code wasn't AI-generated — it only means no active AI tool session "
            "is detected right now."
        ),
        "recommendation": (
            "You can still run senior guards manually with scan_senior to check "
            "for AI-generated code patterns."
        ),
    },
}


# ── Core logic ────────────────────────────────────────────────────────

def check_session() -> dict:
    """Check if the current session is AI-assisted and return guardian status.

    Returns:
        Dict with keys: is_ai_session, agent_name, env_markers_checked,
        guardian_stats, pedagogy.
    """
    ai_session = is_ai_session()
    agent_name = get_ai_agent_name()

    # Get guardian block stats (from log file)
    stats = get_guardian_stats()

    pedagogy_key = "ai_detected" if ai_session else "no_ai_detected"
    pedagogy = SESSION_PEDAGOGY[pedagogy_key]

    return {
        "is_ai_session": ai_session,
        "agent_name": agent_name,
        "env_markers_checked": AI_ENV_MARKERS,
        "guardian_stats": {
            "total_blocks": stats["total_blocks"],
            "by_pattern": stats["by_pattern"],
            "by_agent": stats["by_agent"],
        },
        "pedagogy": {
            "why": pedagogy["why"],
            "recommendation": pedagogy["recommendation"],
        },
    }
