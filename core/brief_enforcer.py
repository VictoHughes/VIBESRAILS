"""Pre-Generation Discipline — enforce structured briefs before code generation.

Validates that AI coding briefs contain sufficient context to produce
reliable code. Scores briefs on required + optional fields, detects
vague/lazy prompts, and suggests improvements.

Scoring:
  Required fields (intent, constraints, affects): 20 points each = max 60
  Optional fields (tradeoffs, rollback, dependencies): ~13.33 each = max 40
  Total: 0-100

Levels:
  0-39:  insufficient (block) — brief too vague
  40-59: minimal (warn) — passable but risky
  60-79: adequate (pass) — acceptable
  80-100: strong (pass) — solid brief
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

logger = logging.getLogger(__name__)

# ── Field definitions ────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "intent": "What should the AI generate?",
    "constraints": "What constraints or limits apply?",
    "affects": "Which files or modules are impacted?",
}

OPTIONAL_FIELDS = {
    "tradeoffs": "What tradeoffs are acceptable?",
    "rollback": "How to undo if something breaks?",
    "dependencies": "What existing dependencies are relevant?",
}

# Points per field
_REQUIRED_POINTS = 20.0  # 3 fields * 20 = 60
_OPTIONAL_POINTS = 40.0 / 3  # ~13.33 per field, 3 fields = 40

_MIN_FIELD_LENGTH = 10

# ── Vague patterns ───────────────────────────────────────────────────

_VAGUE_PATTERNS = [
    re.compile(r"^fix\s+it\b", re.IGNORECASE),
    re.compile(r"^make\s+it\s+work\b", re.IGNORECASE),
    re.compile(r"^do\s+(the|this)\s+thing\b", re.IGNORECASE),
    re.compile(r"^just\s+(do|fix|make)\b", re.IGNORECASE),
    re.compile(r"^update\s+it\b", re.IGNORECASE),
    re.compile(r"^change\s+it\b", re.IGNORECASE),
    re.compile(r"^handle\s+it\b", re.IGNORECASE),
    re.compile(r"^idk\b", re.IGNORECASE),
    re.compile(r"^whatever\b", re.IGNORECASE),
]

_ACTION_VERBS = re.compile(
    r"\b(add|create|implement|build|remove|delete|refactor|extract|"
    r"migrate|replace|split|merge|move|rename|convert|validate|"
    r"check|test|scan|parse|generate|compute|calculate|return)\b",
    re.IGNORECASE,
)

_FILE_PATTERN = re.compile(r"\b[\w/]+\.\w{1,4}\b")
_TECH_PATTERN = re.compile(
    r"\b(timeout|retry|cache|async|sync|thread|queue|api|rest|"
    r"sql|orm|jwt|oauth|http|tcp|udp|ssl|tls|json|xml|yaml|"
    r"utf|ascii|regex|hash|encrypt|compress|index|schema)\b",
    re.IGNORECASE,
)


# ── Classification ───────────────────────────────────────────────────

def classify_level(score: int) -> str:
    """Classify a brief score into a level."""
    if score < 40:
        return "insufficient"
    if score < 60:
        return "minimal"
    if score < 80:
        return "adequate"
    return "strong"


# ── BriefEnforcer ────────────────────────────────────────────────────


class BriefEnforcer:
    """Validates and scores pre-generation briefs."""

    def __init__(self, db_path: str | None = None):
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        migrate(db_path=str(self._db_path))

    # ── Validate ─────────────────────────────────────────────────

    def validate_brief(self, brief: dict) -> dict:
        """Validate a brief and return detailed scoring.

        Args:
            brief: Dict with required/optional fields.

        Returns:
            Dict with score, level, missing_required, missing_optional,
            field_issues.
        """
        score = 0.0
        missing_required: list[str] = []
        missing_optional: list[str] = []
        field_issues: dict[str, list[str]] = {}

        # Score required fields
        for field in REQUIRED_FIELDS:
            value = brief.get(field)
            if field in ("constraints", "affects"):
                # These are list fields
                quality = self._score_list_field(value, field)
            else:
                quality = self.score_quality(
                    value if isinstance(value, str) else "", field
                )

            if quality["score"] == 0:
                missing_required.append(field)
            else:
                score += quality["score"] * _REQUIRED_POINTS

            if quality["flags"]:
                field_issues[field] = quality["flags"]

        # Score optional fields
        for field in OPTIONAL_FIELDS:
            value = brief.get(field)
            if field == "dependencies":
                quality = self._score_list_field(value, field)
            else:
                quality = self.score_quality(
                    value if isinstance(value, str) else "", field
                )

            if quality["score"] == 0:
                missing_optional.append(field)
            else:
                score += quality["score"] * _OPTIONAL_POINTS

            if quality["flags"]:
                field_issues[field] = quality["flags"]

        final_score = min(100, round(score))
        level = classify_level(final_score)

        return {
            "score": final_score,
            "level": level,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "field_issues": field_issues,
        }

    # ── Score quality ────────────────────────────────────────────

    def score_quality(self, text: str, field_name: str) -> dict:
        """Score the quality of a single text field.

        Returns:
            {"score": float 0-1, "flags": list[str]}
        """
        if not text or not text.strip():
            return {"score": 0.0, "flags": ["empty"]}

        text = text.strip()
        flags: list[str] = []

        # Check for vague patterns
        for pattern in _VAGUE_PATTERNS:
            if pattern.search(text):
                return {"score": 0.0, "flags": ["too_vague"]}

        # Check minimum length
        if len(text) < _MIN_FIELD_LENGTH:
            return {"score": 0.0, "flags": ["too_short"]}

        # Base score
        base = 0.6

        # Bonus: action verb detected
        if _ACTION_VERBS.search(text):
            base += 0.15
        else:
            flags.append("no_action")

        # Bonus: file references
        if _FILE_PATTERN.search(text):
            base += 0.15

        # Bonus: technical terms
        if _TECH_PATTERN.search(text):
            base += 0.10

        return {"score": min(1.0, base), "flags": flags}

    def _score_list_field(self, value: list | str | None, field_name: str) -> dict:
        """Score a list-type field (constraints, affects, dependencies)."""
        if value is None:
            return {"score": 0.0, "flags": ["empty"]}

        if isinstance(value, str):
            # Accept string, treat as single-item list
            value = [value]

        if not isinstance(value, list) or len(value) == 0:
            return {"score": 0.0, "flags": ["empty"]}

        # Filter out empty/short items
        valid_items = [
            item for item in value
            if isinstance(item, str) and len(item.strip()) >= 3
        ]

        if len(valid_items) == 0:
            return {"score": 0.0, "flags": ["too_short"]}

        # Score based on quality of items
        flags: list[str] = []
        base = 0.6

        # More items = better
        if len(valid_items) >= 2:
            base += 0.2
        if len(valid_items) >= 3:
            base += 0.1

        # Check for specificity
        all_text = " ".join(valid_items)
        if _FILE_PATTERN.search(all_text):
            base += 0.1

        return {"score": min(1.0, base), "flags": flags}

    # ── Suggestions ──────────────────────────────────────────────

    def suggest_improvement(self, brief: dict) -> list[str]:
        """Generate improvement suggestions for a brief.

        Returns a list of actionable questions/tips.
        """
        validation = self.validate_brief(brief)
        suggestions: list[str] = []

        _SUGGESTIONS = {
            "intent": "Decris en une phrase ce que le code doit faire.",
            "constraints": (
                "Quelles sont les limites ? (perf, compat, taille, "
                "no external deps...)"
            ),
            "affects": "Quels fichiers ou modules seront modifies ?",
            "tradeoffs": (
                "Quel compromis acceptes-tu ? "
                "(vitesse vs lisibilite, simplicite vs flexibilite...)"
            ),
            "rollback": (
                "Comment annuler si ca casse ? "
                "(git revert, feature flag, migration down...)"
            ),
            "dependencies": (
                "Quelles dependances existantes sont concernees ? "
                "(packages, modules internes, APIs...)"
            ),
        }

        for field in validation["missing_required"]:
            if field in _SUGGESTIONS:
                suggestions.append(f"[REQUIRED] {field}: {_SUGGESTIONS[field]}")

        for field in validation["missing_optional"]:
            if field in _SUGGESTIONS:
                suggestions.append(f"[OPTIONAL] {field}: {_SUGGESTIONS[field]}")

        for field, flags in validation["field_issues"].items():
            if "too_vague" in flags:
                suggestions.append(
                    f"[FIX] {field}: trop vague — soyez plus specifique."
                )
            if "no_action" in flags and field == "intent":
                suggestions.append(
                    f"[FIX] {field}: ajoutez un verbe d'action "
                    "(create, add, refactor, remove...)."
                )

        return suggestions

    # ── History ──────────────────────────────────────────────────

    def store_brief(
        self, brief: dict, score: int, level: str,
        session_id: str | None = None,
    ) -> int:
        """Store a brief evaluation in history. Returns the row ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "INSERT INTO brief_history "
                "(session_id, brief_json, score, level, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, json.dumps(brief), score, level, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_history(self, session_id: str | None = None) -> list[dict]:
        """Retrieve brief history, optionally filtered by session."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            if session_id:
                cursor = conn.execute(
                    "SELECT id, session_id, brief_json, score, level, created_at "
                    "FROM brief_history WHERE session_id = ? ORDER BY created_at LIMIT 1000",
                    (session_id,),
                )
            else:
                cursor = conn.execute(
                    "SELECT id, session_id, brief_json, score, level, created_at "
                    "FROM brief_history ORDER BY created_at LIMIT 1000",
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0], "session_id": r[1],
                    "brief": json.loads(r[2]), "score": r[3],
                    "level": r[4], "created_at": r[5],
                }
                for r in rows
            ]
        finally:
            conn.close()
