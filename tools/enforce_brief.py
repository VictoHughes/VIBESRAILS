"""MCP tool: enforce_brief — validate pre-generation briefs.

Wraps core/brief_enforcer.py as an MCP-callable tool.
Enforces structured briefs before AI code generation to reduce
hallucinations and iteration cycles.
"""

from __future__ import annotations

import logging

from core.brief_enforcer import BriefEnforcer
from core.input_validator import (
    InputValidationError,
    validate_dict,
    validate_optional_string,
)
from core.learning_bridge import record_safe

logger = logging.getLogger(__name__)

# ── Pedagogy per level ───────────────────────────────────────────────

LEVEL_PEDAGOGY: dict[str, dict[str, str]] = {
    "insufficient": {
        "why": (
            "Ce brief est trop vague pour generer du code fiable. "
            "L'IA va combler les trous avec des suppositions — c'est la "
            "source #1 de bugs en vibe coding. "
            "Completez les champs manquants: {missing}."
        ),
        "recommendation": (
            "Before generating code, provide at minimum: "
            "(1) clear intent, (2) at least one constraint, "
            "(3) which files are affected."
        ),
    },
    "minimal": {
        "why": (
            "Brief passable mais risque. Champs a renforcer: {weak_fields}. "
            "Un brief plus detaille reduit de 60% les iterations de correction."
        ),
        "recommendation": (
            "Add optional fields (tradeoffs, rollback plan, dependencies) "
            "to improve the quality of generated code."
        ),
    },
    "adequate": {
        "why": (
            "Brief acceptable. Pour un resultat optimal, ajoutez: {suggestions}."
        ),
        "recommendation": (
            "Good brief. Consider adding tradeoffs or rollback strategy "
            "for even better results."
        ),
    },
    "strong": {
        "why": (
            "Brief solide. L'IA a suffisamment de contexte pour generer "
            "du code aligne avec votre intention."
        ),
        "recommendation": (
            "Excellent brief. Proceed with code generation — the AI has "
            "enough context to produce aligned code."
        ),
    },
}


# ── Helpers ───────────────────────────────────────────────────────────

def _build_pedagogy(
    level: str,
    missing_required: list[str],
    missing_optional: list[str],
    field_issues: dict,
    suggestions: list[str],
) -> dict:
    """Build contextual pedagogy for the brief quality level."""
    template = LEVEL_PEDAGOGY.get(level, LEVEL_PEDAGOGY["insufficient"])

    missing_str = ", ".join(missing_required) if missing_required else "none"
    weak_str = ", ".join(
        f for f, flags in field_issues.items() if flags
    ) if field_issues else "none"
    suggestions_str = "; ".join(suggestions[:3]) if suggestions else "none"

    return {
        "why": template["why"].format(
            missing=missing_str,
            weak_fields=weak_str,
            suggestions=suggestions_str,
        ),
        "recommendation": template["recommendation"],
    }


# ── Core logic ────────────────────────────────────────────────────────

def enforce_brief(
    brief: dict,
    session_id: str | None = None,
    strict: bool = False,
    db_path: str | None = None,
) -> dict:
    """Validate a pre-generation brief and return quality assessment.

    Args:
        brief: Dict with required/optional fields.
        session_id: Optional session ID for tracking.
        strict: If True, block if score < 60. If False, block only if score < 20.
        db_path: SQLite DB path override (for testing).

    Returns:
        Dict with status, score, level, missing_required, missing_optional,
        field_issues, suggestions, pedagogy.
    """
    # Validate inputs
    try:
        validate_dict(brief, "brief", max_keys=20)
        validate_optional_string(session_id, "session_id", max_length=256)
    except InputValidationError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "score": 0,
            "level": "insufficient",
            "missing_required": [],
            "missing_optional": [],
            "field_issues": {},
            "suggestions": [],
            "pedagogy": {},
        }

    enforcer = BriefEnforcer(db_path=db_path)

    validation = enforcer.validate_brief(brief)
    suggestions = enforcer.suggest_improvement(brief)

    score = validation["score"]
    level = validation["level"]

    # Store in history
    enforcer.store_brief(brief, score, level, session_id=session_id)

    # Determine status based on mode
    if strict:
        if score < 60:
            status = "block"
        else:
            status = "pass"
    else:
        if score < 20:
            status = "block"
        elif score < 60:
            status = "warn"
        else:
            status = "pass"

    # Feed Learning Engine
    record_safe(session_id, "brief_score", {"score": score})

    return {
        "status": status,
        "score": score,
        "level": level,
        "missing_required": validation["missing_required"],
        "missing_optional": validation["missing_optional"],
        "field_issues": validation["field_issues"],
        "suggestions": suggestions,
        "pedagogy": _build_pedagogy(
            level,
            validation["missing_required"],
            validation["missing_optional"],
            validation["field_issues"],
            suggestions,
        ),
    }
