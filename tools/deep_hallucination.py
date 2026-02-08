"""MCP tool: deep_hallucination — multi-level import hallucination analysis.

Wraps core/hallucination_deep.py as an MCP-callable tool.
Parses imports from a Python file and verifies them at up to 4 levels:
  Level 1: Module importable locally?
  Level 2: Package exists on PyPI? (slopsquatting detection)
  Level 3: Specific symbol exists in the package?
  Level 4: Symbol available in the installed version?
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass

from core.hallucination_deep import DeepHallucinationChecker
from core.input_validator import InputValidationError, validate_enum, validate_int
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path

logger = logging.getLogger(__name__)


# ── Parsed import representation ─────────────────────────────────────

@dataclass
class _ParsedImport:
    """An import extracted from AST."""

    module: str        # top-level module (e.g. "requests")
    full_module: str   # full dotted path (e.g. "requests.adapters")
    symbols: list[str] # imported names (e.g. ["HTTPAdapter"])
    line: int


# ── Pedagogy templates ───────────────────────────────────────────────

def _pedagogy_level1(module: str) -> dict:
    return {
        "why": (
            f"L'import '{module}' n'existe pas dans l'environnement. "
            "Ton IA a probablement invente ce module. Verifie sur PyPI."
        ),
        "how_to_fix": f"pip install {module} — or remove the import if it's hallucinated.",
        "prevention": "Always verify unfamiliar imports before using AI-generated code.",
    }


def _pedagogy_level2(package: str, similar: list[str]) -> dict:
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


def _pedagogy_slopsquatting(package: str, similar: list[str]) -> dict:
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


def _pedagogy_level3(package: str, symbol: str, available: list[str]) -> dict:
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


def _pedagogy_level4(package: str, symbol: str, version: str | None) -> dict:
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


# ── Import parser ────────────────────────────────────────────────────

def _parse_imports(source: str) -> list[_ParsedImport]:
    """Extract imports from Python source code via AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports: list[_ParsedImport] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(_ParsedImport(
                    module=alias.name.split(".")[0],
                    full_module=alias.name,
                    symbols=[],
                    line=node.lineno,
                ))
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0 or not node.module:
                continue  # Skip relative imports
            symbols = [a.name for a in (node.names or [])]
            imports.append(_ParsedImport(
                module=node.module.split(".")[0],
                full_module=node.module,
                symbols=symbols,
                line=node.lineno,
            ))

    return imports


# ── Core logic ────────────────────────────────────────────────────────

def deep_hallucination(
    file_path: str,
    max_level: int = 2,
    ecosystem: str = "pypi",
    db_path: str | None = None,
) -> dict:
    """Analyze a Python file for hallucinated imports at multiple verification levels.

    Args:
        file_path: Path to the Python file to analyze.
        max_level: Maximum verification level (1-4, default 2).
        ecosystem: Package ecosystem ("pypi", default "pypi").
        db_path: SQLite DB path override (for testing).

    Returns:
        Dict with status, imports_checked, hallucinations, verified,
        unverifiable, pedagogy.
    """
    # Validate inputs
    try:
        validate_enum(ecosystem, "ecosystem", choices={"pypi"})
        validate_int(max_level, "max_level", min_val=1, max_val=4)
    except InputValidationError as exc:
        return _error_result(str(exc))

    max_level = max(1, min(4, max_level))

    try:
        fp = validate_path(
            file_path, must_exist=True, must_be_file=True,
            max_size_mb=10, allowed_extensions={".py"},
        )
    except PathValidationError as exc:
        return _error_result(str(exc))

    try:
        source = fp.read_text()
    except OSError as exc:
        return _error_result(f"Cannot read file: {exc}")

    imports = _parse_imports(source)
    if not imports:
        return {
            "status": "pass",
            "imports_checked": 0,
            "hallucinations": [],
            "verified": [],
            "unverifiable": [],
            "pedagogy": {
                "why": "No imports found in this file.",
                "recommendation": "Nothing to verify.",
            },
        }

    checker = DeepHallucinationChecker(
        db_path=db_path, project_path=str(fp.parent),
    )

    hallucinations: list[dict] = []
    verified: list[dict] = []
    unverifiable: list[dict] = []

    for imp in imports:
        result = _check_import(checker, imp, max_level, ecosystem)
        if result["category"] == "hallucination":
            hallucinations.append(result)
        elif result["category"] == "verified":
            verified.append(result)
        else:
            unverifiable.append(result)

    status = "block" if hallucinations else "pass"

    # Feed Learning Engine
    for h in hallucinations:
        record_safe(None, "hallucination", {"module": h["module"]})

    return {
        "status": status,
        "imports_checked": len(imports),
        "hallucinations": hallucinations,
        "verified": verified,
        "unverifiable": unverifiable,
        "pedagogy": {
            "why": (
                f"Checked {len(imports)} imports up to level {max_level}. "
                f"Found {len(hallucinations)} hallucination(s)."
            ),
            "recommendation": (
                "Review each hallucinated import and remove or replace it."
                if hallucinations
                else "All verified imports look legitimate."
            ),
        },
    }


def _check_import(
    checker: DeepHallucinationChecker,
    imp: _ParsedImport,
    max_level: int,
    ecosystem: str,
) -> dict:
    """Run multi-level checks on a single import."""
    base = {"module": imp.full_module, "line": imp.line}

    # ── Level 1 ──
    exists_locally = checker.check_import_exists(imp.module)
    if not exists_locally:
        if max_level < 2:
            return {
                **base,
                "category": "hallucination",
                "failed_level": 1,
                "reason": f"Module '{imp.module}' not importable locally",
                "similar_packages": [],
                "pedagogy": _pedagogy_level1(imp.module),
            }

        # ── Level 2 ──
        registry = checker.check_package_registry(imp.module, ecosystem)
        if registry["exists"] is False:
            similar = registry["similar_packages"]
            is_slopsquat = len(similar) > 0
            return {
                **base,
                "category": "hallucination",
                "failed_level": 2,
                "reason": (
                    f"Package '{imp.module}' not found on {ecosystem}"
                    + (f" (similar: {', '.join(similar)})" if similar else "")
                ),
                "similar_packages": similar,
                "pedagogy": (
                    _pedagogy_slopsquatting(imp.module, similar)
                    if is_slopsquat
                    else _pedagogy_level2(imp.module, similar)
                ),
            }
        if registry["exists"] is None:
            return {
                **base,
                "category": "unverifiable",
                "failed_level": None,
                "reason": "Registry unavailable (offline)",
                "similar_packages": [],
                "pedagogy": _pedagogy_level1(imp.module),
            }

        # Package exists on registry but not installed locally
        # If max_level <= 2, mark as verified at registry level
        if max_level <= 2:
            return {
                **base,
                "category": "verified",
                "verified_level": 2,
                "reason": f"Package exists on {ecosystem} (not installed locally)",
            }

    # At this point: import exists locally OR was found on registry
    # ── Level 3: Symbol check ──
    if max_level >= 3 and imp.symbols:
        for symbol in imp.symbols:
            sym_result = checker.check_symbol_exists(imp.full_module, symbol)
            if sym_result["status"] == "not_found":
                return {
                    **base,
                    "category": "hallucination",
                    "failed_level": 3,
                    "reason": f"'{symbol}' not found in '{imp.full_module}'",
                    "similar_packages": [],
                    "available_symbols": sym_result["available_symbols"],
                    "pedagogy": _pedagogy_level3(
                        imp.full_module, symbol, sym_result["available_symbols"]
                    ),
                }
            if sym_result["status"] == "unverifiable":
                return {
                    **base,
                    "category": "unverifiable",
                    "failed_level": None,
                    "reason": f"Cannot verify '{symbol}' — {sym_result['reason']}",
                    "similar_packages": [],
                    "pedagogy": _pedagogy_level1(imp.module),
                }

    # ── Level 4: Version compat ──
    if max_level >= 4 and imp.symbols:
        for symbol in imp.symbols:
            vc = checker.check_version_compat(imp.module, symbol)
            if not vc["compatible"]:
                return {
                    **base,
                    "category": "hallucination",
                    "failed_level": 4,
                    "reason": vc["reason"] or f"Version incompatible for '{symbol}'",
                    "similar_packages": [],
                    "pedagogy": _pedagogy_level4(
                        imp.module, symbol, vc["installed_version"]
                    ),
                }

    # All checks passed
    return {
        **base,
        "category": "verified",
        "verified_level": max_level,
        "reason": None,
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "imports_checked": 0,
        "hallucinations": [],
        "verified": [],
        "unverifiable": [],
        "error": message,
    }
