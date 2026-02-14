"""Brief enforcer constants and classification — extracted from brief_enforcer.py."""

import re

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
REQUIRED_POINTS = 20.0  # 3 fields * 20 = 60
OPTIONAL_POINTS = 40.0 / 3  # ~13.33 per field, 3 fields = 40

MIN_FIELD_LENGTH = 10

# ── Vague patterns ───────────────────────────────────────────────────

VAGUE_PATTERNS = [
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

ACTION_VERBS = re.compile(
    r"\b(add|create|implement|build|remove|delete|refactor|extract|"
    r"migrate|replace|split|merge|move|rename|convert|validate|"
    r"check|test|scan|parse|generate|compute|calculate|return)\b",
    re.IGNORECASE,
)

FILE_PATTERN = re.compile(r"\b[\w/]+\.\w{1,4}\b")
TECH_PATTERN = re.compile(
    r"\b(timeout|retry|cache|async|sync|thread|queue|api|rest|"
    r"sql|orm|jwt|oauth|http|tcp|udp|ssl|tls|json|xml|yaml|"
    r"utf|ascii|regex|hash|encrypt|compress|index|schema)\b",
    re.IGNORECASE,
)


IMPROVEMENT_SUGGESTIONS = {
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


def classify_level(score: int) -> str:
    """Classify a brief score into a level."""
    if score < 40:
        return "insufficient"
    if score < 60:
        return "minimal"
    if score < 80:
        return "adequate"
    return "strong"
