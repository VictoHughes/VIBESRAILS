"""Pre-Generation Discipline — enforce structured briefs before code generation.

Scores briefs 0-100 on required (intent, constraints, affects) and optional
(tradeoffs, rollback, dependencies) fields. Levels: insufficient (<40),
minimal (40-59), adequate (60-79), strong (80+).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

from .brief_enforcer_patterns import (  # noqa: I001
    ACTION_VERBS as _ACTION_VERBS,
)
from .brief_enforcer_patterns import (
    FILE_PATTERN as _FILE_PATTERN,
)
from .brief_enforcer_patterns import (
    MIN_FIELD_LENGTH as _MIN_FIELD_LENGTH,
)
from .brief_enforcer_patterns import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    classify_level,
)
from .brief_enforcer_patterns import (
    OPTIONAL_POINTS as _OPTIONAL_POINTS,
)
from .brief_enforcer_patterns import (
    REQUIRED_POINTS as _REQUIRED_POINTS,
)
from .brief_enforcer_patterns import (
    TECH_PATTERN as _TECH_PATTERN,
)
from .brief_enforcer_patterns import (
    VAGUE_PATTERNS as _VAGUE_PATTERNS,
)

logger = logging.getLogger(__name__)


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
        """Generate improvement suggestions for a brief."""
        from .brief_enforcer_patterns import IMPROVEMENT_SUGGESTIONS

        validation = self.validate_brief(brief)
        suggestions: list[str] = []

        for field in validation["missing_required"]:
            if field in IMPROVEMENT_SUGGESTIONS:
                suggestions.append(f"[REQUIRED] {field}: {IMPROVEMENT_SUGGESTIONS[field]}")

        for field in validation["missing_optional"]:
            if field in IMPROVEMENT_SUGGESTIONS:
                suggestions.append(f"[OPTIONAL] {field}: {IMPROVEMENT_SUGGESTIONS[field]}")

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
        conn = sqlite3.connect(str(self._db_path), timeout=10)
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
        conn = sqlite3.connect(str(self._db_path), timeout=10)
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
