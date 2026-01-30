"""
vibesrails Smart Setup - Advanced Pattern Functions.

Functions for advanced users who want to enter regex patterns manually.
"""

import logging
import re
from pathlib import Path

from ..scanner import GREEN, NC, RED, YELLOW

logger = logging.getLogger(__name__)


_REDOS_PATTERNS = [
    re.compile(r'\(\.\*\)\+'),
    re.compile(r'\(\.\+\)\+'),
    re.compile(r'\(\[.*\]\*\)\+'),
]


def _is_redos_risk(pattern: str) -> bool:
    """Check if pattern has ReDoS risk."""
    return any(d.search(pattern) for d in _REDOS_PATTERNS)


def _preview_matches_in_file(
    py_file: Path, compiled: re.Pattern, project_root: Path, max_lines: int,
) -> list[str]:
    """Find matching lines in a single file."""
    matches = []
    try:
        content = py_file.read_text(errors="ignore")
        for i, line in enumerate(content.split("\n"), 1):
            if len(line) > 500:
                continue
            if compiled.search(line):
                rel_path = py_file.relative_to(project_root)
                matches.append(f"  {rel_path}:{i}: {line[:60]}...")
                if len(matches) >= max_lines:
                    break
    except Exception:
        logger.debug("Failed to read file during pattern preview")
    return matches


def validate_and_preview_regex(pattern: str, project_root: Path) -> tuple[bool, list[str]]:
    """Validate regex and preview matches. Returns (is_valid, preview_lines)."""
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return False, [f"Regex invalide: {e}"]

    if _is_redos_risk(pattern):
        return False, ["Regex potentiellement dangereuse (ReDoS)"]

    matches = []
    files_checked = 0
    for py_file in project_root.rglob("*.py"):
        if files_checked >= 5:
            break
        file_matches = _preview_matches_in_file(py_file, compiled, project_root, 3)
        matches.extend(file_matches)
        if file_matches:
            files_checked += 1

    return True, matches


def _show_preview(preview: list[str]) -> None:
    """Display pattern match preview."""
    if preview:
        print(f"  {YELLOW}Apercu des matches ({len(preview)} trouve(s)):{NC}")
        for match in preview[:5]:
            print(f"  {match}")
        if len(preview) > 5:
            print(f"  ... et {len(preview) - 5} autres")
    else:
        print(f"  {YELLOW}Aucun match trouve dans le projet actuel{NC}")


def _prompt_single_pattern(project_root: Path, index: int) -> dict | None:
    """Prompt for a single pattern. Returns pattern dict or None."""
    pattern_input = input("\n  Regex a bloquer (ou Entree): ").strip()
    if not pattern_input:
        return None

    is_valid, preview = validate_and_preview_regex(pattern_input, project_root)
    if not is_valid:
        print(f"  {RED}{preview[0]}{NC}")
        return ...  # sentinel: invalid but continue

    _show_preview(preview)
    confirm = input("  Ajouter ce pattern? [O/n]: ").strip().lower()
    if confirm in ("n", "no", "non"):
        print(f"  {YELLOW}Pattern ignore{NC}")
        return ...

    message = input("  Message d'erreur: ").strip() or f"Pattern interdit: {pattern_input}"
    print(f"  {GREEN}+ Ajoute: {pattern_input}{NC}")
    return {"id": f"custom_{index}", "regex": pattern_input, "message": message}


def prompt_extra_patterns(project_root: Path | None = None) -> list[dict]:
    """Ask user for additional patterns to add with validation and preview."""
    if project_root is None:
        project_root = Path.cwd()

    extra_patterns = []
    print(f"\n{YELLOW}Patterns additionnels?{NC}")
    print("  Exemples: nom de projet, API keys specifiques, etc.")
    print("  (Entree vide pour continuer)")

    while True:
        try:
            result = _prompt_single_pattern(project_root, len(extra_patterns) + 1)
            if result is None:
                break
            if result is not ...:
                extra_patterns.append(result)
        except (EOFError, KeyboardInterrupt):
            print()
            break

    return extra_patterns
