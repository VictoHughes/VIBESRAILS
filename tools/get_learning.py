"""MCP tool: get_learning — cross-session developer profiling.

Provides 4 actions: profile, insights, session_summary, record.
Aggregates events from all VibesRails tools into actionable insights.
"""

from __future__ import annotations

import logging

from core.input_validator import (
    InputValidationError,
    validate_dict,
    validate_enum,
    validate_optional_string,
)
from core.learning_engine import VALID_EVENT_TYPES, LearningEngine

logger = logging.getLogger(__name__)

# ── Pedagogy ─────────────────────────────────────────────────────────

_PROFILE_PEDAGOGY = {
    "why": (
        "Votre profil developpeur sur {sessions_count} sessions. "
        "Ce profil se construit automatiquement a chaque utilisation "
        "de VibesRails."
    ),
    "how_to_fix": "Continuez a utiliser les outils pour affiner votre profil.",
    "prevention": "Un profil complet aide a identifier vos points faibles recurrents.",
}

_INSIGHTS_PEDAGOGY = {
    "why": (
        "Recommandations basees sur votre historique. Ces insights "
        "se precisent avec le nombre de sessions analysees."
    ),
    "how_to_fix": "Suivez les recommandations dans l'ordre de priorite.",
    "prevention": "Consultez regulierement vos insights pour une amelioration continue.",
}

_NO_DATA_PEDAGOGY = {
    "why": (
        "Pas encore assez de donnees. Utilisez les outils VibesRails "
        "pendant quelques sessions pour construire votre profil."
    ),
    "how_to_fix": "Lancez scan_code, enforce_brief, check_drift sur votre projet.",
    "prevention": "Les insights se precisent apres 3+ sessions.",
}

_RECORD_PEDAGOGY = {
    "why": "Evenement enregistre. Le profil developpeur a ete mis a jour.",
    "how_to_fix": "Les outils VibesRails enregistrent automatiquement les evenements.",
    "prevention": "Plus il y a d'evenements, plus le profil est precis.",
}


def get_learning(
    action: str,
    session_id: str | None = None,
    event_type: str | None = None,
    event_data: dict | None = None,
    db_path: str | None = None,
) -> dict:
    """Cross-session developer profiling.

    Args:
        action: "profile", "insights", "session_summary", or "record".
        session_id: Required for "session_summary" and "record".
        event_type: Required for "record". One of: violation, brief_score,
            drift, hallucination, config_issue, injection.
        event_data: Required for "record". Event payload dict.
        db_path: Optional database path (for testing).

    Returns:
        Dict with status, data, and pedagogy.
    """
    # Validate inputs
    _valid_actions = {"profile", "insights", "session_summary", "record"}
    try:
        validate_enum(action, "action", choices=_valid_actions)
        validate_optional_string(session_id, "session_id", max_length=256)
        if event_type is not None:
            validate_optional_string(event_type, "event_type", max_length=100)
        if event_data is not None:
            validate_dict(event_data, "event_data")
    except InputValidationError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "data": {},
            "pedagogy": _NO_DATA_PEDAGOGY,
        }

    try:
        engine = LearningEngine(db_path=db_path)

        if action == "profile":
            profile = engine.get_profile()
            sessions = profile.get("sessions_count", 0)
            pedagogy = _NO_DATA_PEDAGOGY if profile.get("status") == "no_data" else {
                **_PROFILE_PEDAGOGY,
                "why": _PROFILE_PEDAGOGY["why"].format(sessions_count=sessions),
            }
            return {
                "status": "pass" if profile.get("status") == "ok" else "info",
                "data": profile,
                "pedagogy": pedagogy,
            }

        if action == "insights":
            profile = engine.get_profile()
            if profile.get("status") == "no_data":
                return {
                    "status": "info",
                    "data": [],
                    "pedagogy": _NO_DATA_PEDAGOGY,
                }
            insights = engine.get_insights()
            return {
                "status": "pass",
                "data": insights,
                "pedagogy": _INSIGHTS_PEDAGOGY,
            }

        if action == "session_summary":
            if not session_id:
                return {
                    "status": "error",
                    "error": "session_id is required for action 'session_summary'.",
                    "data": {},
                    "pedagogy": _NO_DATA_PEDAGOGY,
                }
            summary = engine.get_session_summary(session_id)
            return {
                "status": "pass" if summary["events_count"] > 0 else "info",
                "data": summary,
                "pedagogy": _INSIGHTS_PEDAGOGY,
            }

        if action == "record":
            if not session_id:
                return {
                    "status": "error",
                    "error": "session_id is required for action 'record'.",
                    "data": {},
                    "pedagogy": _NO_DATA_PEDAGOGY,
                }
            if not event_type:
                return {
                    "status": "error",
                    "error": (
                        "event_type is required for action 'record'. "
                        f"Valid types: {sorted(VALID_EVENT_TYPES)}"
                    ),
                    "data": {},
                    "pedagogy": _NO_DATA_PEDAGOGY,
                }
            if event_data is None:
                return {
                    "status": "error",
                    "error": "event_data is required for action 'record'.",
                    "data": {},
                    "pedagogy": _NO_DATA_PEDAGOGY,
                }
            engine.record_event(session_id, event_type, event_data)
            return {
                "status": "pass",
                "data": {"recorded": True, "event_type": event_type},
                "pedagogy": _RECORD_PEDAGOGY,
            }

        return {
            "status": "error",
            "error": (
                f"Invalid action '{action}'. "
                "Must be one of: profile, insights, session_summary, record."
            ),
            "data": {},
            "pedagogy": _NO_DATA_PEDAGOGY,
        }

    except Exception:
        logger.exception("get_learning error")
        return {
            "status": "error",
            "error": "Internal error. Check server logs.",
            "data": {},
            "pedagogy": _NO_DATA_PEDAGOGY,
        }
