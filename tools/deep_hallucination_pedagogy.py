"""Pedagogy + helpers for deep_hallucination — extracted from deep_hallucination.py."""

from __future__ import annotations


def error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "imports_checked": 0,
        "hallucinations": [],
        "verified": [],
        "unverifiable": [],
        "error": message,
    }


def pedagogy_level1(module: str) -> dict:
    return {
        "why": (
            f"L'import '{module}' n'existe pas dans l'environnement. "
            "Ton IA a probablement invente ce module. Verifie sur PyPI."
        ),
        "how_to_fix": f"pip install {module} — or remove the import if it's hallucinated.",
        "prevention": "Always verify unfamiliar imports before using AI-generated code.",
    }


def pedagogy_level2(package: str, similar: list[str]) -> dict:
    return {
        "why": (
            f"Le package '{package}' n'existe pas sur PyPI. C'est une "
            "hallucination classique des LLMs. "
            f"Packages similaires: {', '.join(similar) if similar else 'aucun'}."
        ),
        "how_to_fix": (
            f"Remove '{package}' from your imports. "
            + (f"Did you mean: {', '.join(similar)}?" if similar else "Search PyPI for alternatives.")
        ),
        "prevention": "Cross-reference AI-suggested packages on pypi.org before installing.",
    }


def pedagogy_slopsquatting(package: str, similar: list[str]) -> dict:
    return {
        "why": (
            f"ATTENTION: '{package}' n'existe pas mais "
            f"'{', '.join(similar)}' oui. Un attaquant pourrait enregistrer "
            f"'{package}' comme malware (slopsquatting). Ne l'installez PAS."
        ),
        "how_to_fix": (
            f"Do NOT install '{package}'. Use the correct package name: "
            f"{', '.join(similar)}."
        ),
        "prevention": (
            "Slopsquatting exploits LLM typos in package names. "
            "Always copy package names from the official registry, never from AI output."
        ),
    }


def pedagogy_level3(package: str, symbol: str, available: list[str]) -> dict:
    return {
        "why": (
            f"Le package '{package}' existe mais '{symbol}' n'y est pas. "
            f"Symboles disponibles: {', '.join(available[:5])}. "
            "L'IA a invente cette API."
        ),
        "how_to_fix": (
            f"Check {package}'s documentation for the correct API. "
            f"Available: {', '.join(available[:5])}..."
        ),
        "prevention": "Always verify function/class names against official documentation.",
    }


def pedagogy_level4(package: str, symbol: str, version: str | None) -> dict:
    return {
        "why": (
            f"'{symbol}' n'existe pas dans {package} v{version or '?'}. "
            "The AI may have referenced an API from a different version."
        ),
        "how_to_fix": (
            f"Check which version of {package} introduced '{symbol}'. "
            f"Currently installed: v{version or 'unknown'}."
        ),
        "prevention": "Pin package versions and verify API availability for your version.",
    }
