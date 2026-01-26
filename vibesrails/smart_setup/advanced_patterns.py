"""
vibesrails Smart Setup - Advanced Pattern Functions.

Functions for advanced users who want to enter regex patterns manually.
"""

import re
from pathlib import Path

from ..scanner import GREEN, NC, RED, YELLOW


def validate_and_preview_regex(pattern: str, project_root: Path) -> tuple[bool, list[str]]:
    """Validate regex and preview matches in project.

    Returns (is_valid, list of matching lines preview).
    """
    # 1. Validate regex compiles
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return False, [f"Regex invalide: {e}"]

    # 2. Check for ReDoS patterns (catastrophic backtracking)
    dangerous_patterns = [
        r'\(\.\*\)\+',      # (.*)+
        r'\(\.\+\)\+',      # (.+)+
        r'\(\[.*\]\*\)\+',  # ([...]*)+
    ]
    for danger in dangerous_patterns:
        if re.search(danger, pattern):
            return False, ["Regex potentiellement dangereuse (ReDoS)"]

    # 3. Preview matches (max 5 files, 3 lines per file)
    matches = []
    files_checked = 0
    max_files = 5
    max_lines_per_file = 3

    for py_file in project_root.rglob("*.py"):
        if files_checked >= max_files:
            break
        try:
            content = py_file.read_text(errors="ignore")
            file_matches = 0
            for i, line in enumerate(content.split("\n"), 1):
                if len(line) > 500:  # Skip very long lines
                    continue
                if compiled.search(line):
                    rel_path = py_file.relative_to(project_root)
                    matches.append(f"  {rel_path}:{i}: {line[:60]}...")
                    file_matches += 1
                    if file_matches >= max_lines_per_file:
                        break
            if file_matches > 0:
                files_checked += 1
        except Exception:
            continue

    return True, matches


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
            pattern_input = input("\n  Regex a bloquer (ou Entree): ").strip()
            if not pattern_input:
                break

            # Validate and preview
            is_valid, preview = validate_and_preview_regex(pattern_input, project_root)

            if not is_valid:
                print(f"  {RED}{preview[0]}{NC}")
                continue

            # Show preview
            if preview:
                print(f"  {YELLOW}Apercu des matches ({len(preview)} trouve(s)):{NC}")
                for match in preview[:5]:
                    print(f"  {match}")
                if len(preview) > 5:
                    print(f"  ... et {len(preview) - 5} autres")
            else:
                print(f"  {YELLOW}Aucun match trouve dans le projet actuel{NC}")

            # Confirm
            confirm = input("  Ajouter ce pattern? [O/n]: ").strip().lower()
            if confirm in ("n", "no", "non"):
                print(f"  {YELLOW}Pattern ignore{NC}")
                continue

            message = input("  Message d'erreur: ").strip()
            if not message:
                message = f"Pattern interdit: {pattern_input}"

            pattern_id = f"custom_{len(extra_patterns) + 1}"
            extra_patterns.append({
                "id": pattern_id,
                "regex": pattern_input,
                "message": message,
            })
            print(f"  {GREEN}+ Ajoute: {pattern_input}{NC}")

        except (EOFError, KeyboardInterrupt):
            print()
            break

    return extra_patterns
