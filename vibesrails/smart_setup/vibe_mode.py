"""
vibesrails Smart Setup - Vibe Coder Mode.

User-friendly pattern setup without requiring regex knowledge.
"""

import logging
import re
from pathlib import Path

from ..scanner import BLUE, GREEN, NC, RED, YELLOW
from ._vibe_patterns import SKIP_DIRS as _SKIP_DIRS
from ._vibe_patterns import VIBE_PROTECTIONS
from .i18n import LANG, msg

logger = logging.getLogger(__name__)


# =============================================================================
# SECRET SCANNING
# =============================================================================


def _mask_secret(secret: str) -> str:
    """Mask a secret string for safe display."""
    if len(secret) > 8:
        return secret[:4] + "..." + secret[-4:]
    return secret[:2] + "***"


def _should_skip_line(line: str) -> bool:
    """Check if a line should be skipped during scanning."""
    return (
        line.strip().startswith("#")
        or len(line) > 500
        or "vibesrails: ignore" in line
    )


def _scan_line(line: str, rel_path: str, line_num: int, found: dict) -> None:
    """Scan a single line against all patterns, appending matches to found."""
    for category, config in VIBE_PROTECTIONS.items():
        for pattern_info in config["patterns"]:
            try:
                match = re.search(pattern_info["regex"], line)
            except re.error:
                continue
            if match:
                found[category].append({
                    "file": rel_path,
                    "line": line_num,
                    "preview": _mask_secret(match.group(0)),
                    "pattern_id": pattern_info["id"],
                })


def scan_for_secrets(project_root: Path) -> dict[str, list[dict]]:
    """Scan project and find actual secrets, grouped by category.

    Returns dict like:
    {
        "api_keys": [{"file": "main.py", "line": 10, "preview": "sk-abc..."}],
        "passwords": [...],
    }
    """
    found = {category: [] for category in VIBE_PROTECTIONS}

    for py_file in project_root.rglob("*.py"):
        if any(part in py_file.parts for part in _SKIP_DIRS):
            continue
        try:
            content = py_file.read_text(errors="ignore")
            rel_path = str(py_file.relative_to(project_root))
            for line_num, line in enumerate(content.split("\n"), 1):
                if _should_skip_line(line):
                    continue
                _scan_line(line, rel_path, line_num, found)
        except Exception:
            logger.debug("Failed to read file during secret scan")
            continue

    return {k: v for k, v in found.items() if v}


# =============================================================================
# NATURAL LANGUAGE TO PATTERN
# =============================================================================


def natural_language_to_pattern(description: str, project_name: str | None = None) -> dict | None:
    """Convert natural language description to a blocking pattern.

    Examples:
    - "mon nom de domaine mycompany.com" → regex for mycompany.com
    - "le nom du projet" → regex for project name
    - "emails de l'entreprise" → regex for @company.com
    """
    description_lower = description.lower()

    # Extract quoted strings or specific values
    quoted = re.findall(r'["\']([^"\']+)["\']', description)

    # Domain/URL patterns
    domains = re.findall(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', description)

    # Email patterns
    emails = re.findall(r'@([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', description)

    if quoted:
        # User specified exact string
        value = quoted[0]
        escaped = re.escape(value)
        return {
            "id": f"custom_{value[:10].replace(' ', '_')}",
            "regex": escaped,
            "message": f"Valeur protégée: {value}",
        }

    if domains:
        domain = domains[0]
        escaped = re.escape(domain)
        return {
            "id": f"domain_{domain.replace('.', '_')}",
            "regex": escaped,
            "message": f"Domaine protégé: {domain}",
        }

    if emails:
        domain = emails[0]
        escaped = re.escape(f"@{domain}")
        return {
            "id": f"email_{domain.replace('.', '_')}",
            "regex": escaped,
            "message": f"Email domaine protégé: @{domain}",
        }

    # Project name reference
    if project_name and any(word in description_lower for word in ["projet", "project", "nom du"]):
        escaped = re.escape(project_name)
        return {
            "id": "project_name",
            "regex": escaped,
            "message": f"Nom du projet protégé: {project_name}",
        }

    # Generic: treat the whole input as something to block
    words = description.split()
    if len(words) <= 3:
        # Short input - probably a value to block
        escaped = re.escape(description)
        return {
            "id": f"custom_{description[:10].replace(' ', '_')}",
            "regex": escaped,
            "message": f"Valeur protégée: {description}",
        }

    return None


# =============================================================================
# INTERACTIVE PROMPTS
# =============================================================================


def prompt_user(question: str, default: str = "y") -> bool:
    """Prompt user for yes/no confirmation."""
    suffix = " [Y/n] " if default.lower() == "y" else " [y/N] "
    try:
        response = input(question + suffix).strip().lower()
        if not response:
            return default.lower() == "y"
        return response in ("y", "yes", "o", "oui")
    except (EOFError, KeyboardInterrupt):
        logger.info("")
        return False


def _prompt_secret_protections(found_secrets: dict) -> list[dict]:
    """Show found secrets and prompt user to enable protections for them."""
    selected = []

    if found_secrets:
        total = sum(len(v) for v in found_secrets.values())
        logger.info(f"\n{RED}⚠️  {msg('found_secrets', count=total)}{NC}")

        for category, secrets in found_secrets.items():
            cat_name = VIBE_PROTECTIONS[category]["name"]
            logger.info(f"\n  {YELLOW}{cat_name}:{NC}")
            for secret in secrets[:3]:
                logger.info(f"    • {secret['file']}:{secret['line']} → {secret['preview']}")
            if len(secrets) > 3:
                remaining = len(secrets) - 3
                more = "and" if LANG == "en" else "et"
                others = "others" if LANG == "en" else "autres"
                logger.info(f"    ... {more} {remaining} {others}")

        logger.info("")
        if prompt_user(f"{GREEN}{msg('enable_protection')}{NC}", default="y"):
            for category in found_secrets.keys():
                selected.extend(VIBE_PROTECTIONS[category]["patterns"])
            logger.info(f"  {GREEN}✓ {msg('protections_enabled')}{NC}")
    else:
        logger.info(f"  {GREEN}✓ {msg('no_secrets_found')}{NC}")

    return selected


def _prompt_additional_categories(found_secrets: dict) -> list[dict]:
    """Offer additional protection categories not already found."""
    selected = []
    logger.info(f"\n{YELLOW}{msg('additional_protections')}{NC}")

    available_categories = [cat for cat in VIBE_PROTECTIONS if cat not in found_secrets]

    for i, category in enumerate(available_categories, 1):
        cat_name = VIBE_PROTECTIONS[category]["name"]
        logger.info(f"  {i}. {cat_name}")

    if available_categories:
        logger.info(f"  0. {msg('none')}")
        logger.info("")
        choice = input(f"  {msg('add_protections')}: ").strip()

        if choice and choice != "0":
            try:
                indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
                for idx in indices:
                    if 1 <= idx <= len(available_categories):
                        category = available_categories[idx - 1]
                        selected.extend(VIBE_PROTECTIONS[category]["patterns"])
                        logger.info(f"  {GREEN}✓ {VIBE_PROTECTIONS[category]['name']}{NC}")
            except ValueError:
                pass  # ignore non-numeric input, re-prompt

    return selected


def _prompt_custom_patterns(project_name: str) -> list[dict]:
    """Prompt for natural language custom patterns."""
    selected = []
    logger.info(f"\n{YELLOW}{msg('custom_protection')}{NC}")
    examples = "'mycompany.com', 'project name', '@company.com'" if LANG == "en" else "'mycompany.com', 'le nom du projet', '@entreprise.fr'"
    logger.info(f"  {msg('examples')}: {examples}")
    logger.info(f"  {msg('empty_to_finish')}")

    while True:
        try:
            user_input = input(f"\n  {msg('what_to_protect')} ").strip()
            if not user_input:
                break

            pattern = natural_language_to_pattern(user_input, project_name)

            if pattern:
                logger.info(f"  {BLUE}→ {msg('will_block')}: {_mask_secret(pattern['regex'])}{NC}")
                if prompt_user(f"  {msg('confirm')}", default="y"):
                    selected.append(pattern)
                    logger.info(f"  {GREEN}✓ {msg('added')}{NC}")
            else:
                logger.info(f"  {YELLOW}{msg('not_understood')}{NC}")
                example = '"password123" or "api.mycompany.com"' if LANG == "en" else '"motdepasse123" ou "api.mycompany.com"'
                logger.info(f"  {msg('example')}: {example}")

        except (EOFError, KeyboardInterrupt):
            logger.info("")
            break

    return selected


def prompt_vibe_protections(project_root: Path) -> list[dict]:
    """Vibe-coder-friendly protection setup - no regex knowledge needed."""
    selected_patterns = []
    project_name = project_root.name

    logger.info(f"\n{BLUE}{msg('protection_mode')}{NC}")

    logger.info(f"\n{YELLOW}{msg('analyzing_project')}{NC}")
    found_secrets = scan_for_secrets(project_root)

    selected_patterns.extend(_prompt_secret_protections(found_secrets))
    selected_patterns.extend(_prompt_additional_categories(found_secrets))
    selected_patterns.extend(_prompt_custom_patterns(project_name))

    return selected_patterns
