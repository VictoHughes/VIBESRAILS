"""
vibesrails Smart Setup - Vibe Coder Mode.

User-friendly pattern setup without requiring regex knowledge.
"""

import logging
import re
from pathlib import Path

from ..scanner import BLUE, GREEN, NC, RED, YELLOW
from .i18n import LANG, msg

logger = logging.getLogger(__name__)

# =============================================================================
# PREDEFINED PROTECTION CATEGORIES
# =============================================================================

VIBE_PROTECTIONS = {
    "api_keys": {
        "name": "Clés API (OpenAI, Anthropic, AWS, Google...)",
        "patterns": [
            {"id": "openai_key", "regex": r"sk-[a-zA-Z0-9]{20,}", "message": "Clé OpenAI détectée"},
            {"id": "anthropic_key", "regex": r"sk-ant-[a-zA-Z0-9-]{20,}", "message": "Clé Anthropic détectée"},
            {"id": "aws_key", "regex": r"AKIA[0-9A-Z]{16}", "message": "Clé AWS détectée"},
            {"id": "google_key", "regex": r"AIza[0-9A-Za-z-_]{35}", "message": "Clé Google API détectée"},
            {"id": "github_token", "regex": r"ghp_[a-zA-Z0-9]{36}", "message": "Token GitHub détecté"},
            {"id": "generic_api_key", "regex": r"['\"][a-zA-Z0-9]{32,}['\"]", "message": "Possible clé API détectée"},
        ],
    },
    "passwords": {
        "name": "Mots de passe hardcodés",
        "patterns": [
            {"id": "password_assign", "regex": r"password\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcodé"},
            {"id": "pwd_assign", "regex": r"pwd\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcodé"},
            {"id": "passwd_assign", "regex": r"passwd\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcodé"},
        ],
    },
    "tokens": {
        "name": "Tokens et secrets",
        "patterns": [
            {"id": "bearer_token", "regex": r"Bearer\s+[a-zA-Z0-9._-]+", "message": "Bearer token détecté"},
            {"id": "jwt_token", "regex": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "message": "JWT token détecté"},
            {"id": "secret_assign", "regex": r"secret\s*=\s*['\"][^'\"]+['\"]", "message": "Secret hardcodé"},
        ],
    },
    "urls": {
        "name": "URLs avec credentials",
        "patterns": [
            {"id": "url_with_creds", "regex": r"://[^:]+:[^@]+@", "message": "URL avec credentials détectée"},
            {"id": "localhost_creds", "regex": r"localhost:[0-9]+.*password", "message": "Credentials localhost"},
        ],
    },
}


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


_SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules"}


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
        print()
        return False


def _prompt_secret_protections(found_secrets: dict) -> list[dict]:
    """Show found secrets and prompt user to enable protections for them."""
    selected = []

    if found_secrets:
        total = sum(len(v) for v in found_secrets.values())
        print(f"\n{RED}⚠️  {msg('found_secrets', count=total)}{NC}")

        for category, secrets in found_secrets.items():
            cat_name = VIBE_PROTECTIONS[category]["name"]
            print(f"\n  {YELLOW}{cat_name}:{NC}")
            for secret in secrets[:3]:
                print(f"    • {secret['file']}:{secret['line']} → {secret['preview']}")
            if len(secrets) > 3:
                remaining = len(secrets) - 3
                more = "and" if LANG == "en" else "et"
                others = "others" if LANG == "en" else "autres"
                print(f"    ... {more} {remaining} {others}")

        print()
        if prompt_user(f"{GREEN}{msg('enable_protection')}{NC}", default="y"):
            for category in found_secrets.keys():
                selected.extend(VIBE_PROTECTIONS[category]["patterns"])
            print(f"  {GREEN}✓ {msg('protections_enabled')}{NC}")
    else:
        print(f"  {GREEN}✓ {msg('no_secrets_found')}{NC}")

    return selected


def _prompt_additional_categories(found_secrets: dict) -> list[dict]:
    """Offer additional protection categories not already found."""
    selected = []
    print(f"\n{YELLOW}{msg('additional_protections')}{NC}")

    available_categories = [cat for cat in VIBE_PROTECTIONS if cat not in found_secrets]

    for i, category in enumerate(available_categories, 1):
        cat_name = VIBE_PROTECTIONS[category]["name"]
        print(f"  {i}. {cat_name}")

    if available_categories:
        print(f"  0. {msg('none')}")
        print()
        choice = input(f"  {msg('add_protections')}: ").strip()

        if choice and choice != "0":
            try:
                indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
                for idx in indices:
                    if 1 <= idx <= len(available_categories):
                        category = available_categories[idx - 1]
                        selected.extend(VIBE_PROTECTIONS[category]["patterns"])
                        print(f"  {GREEN}✓ {VIBE_PROTECTIONS[category]['name']}{NC}")
            except ValueError:
                pass  # ignore non-numeric input, re-prompt

    return selected


def _prompt_custom_patterns(project_name: str) -> list[dict]:
    """Prompt for natural language custom patterns."""
    selected = []
    print(f"\n{YELLOW}{msg('custom_protection')}{NC}")
    examples = "'mycompany.com', 'project name', '@company.com'" if LANG == "en" else "'mycompany.com', 'le nom du projet', '@entreprise.fr'"
    print(f"  {msg('examples')}: {examples}")
    print(f"  {msg('empty_to_finish')}")

    while True:
        try:
            user_input = input(f"\n  {msg('what_to_protect')} ").strip()
            if not user_input:
                break

            pattern = natural_language_to_pattern(user_input, project_name)

            if pattern:
                print(f"  {BLUE}→ {msg('will_block')}: {pattern['regex']}{NC}")
                if prompt_user(f"  {msg('confirm')}", default="y"):
                    selected.append(pattern)
                    print(f"  {GREEN}✓ {msg('added')}{NC}")
            else:
                print(f"  {YELLOW}{msg('not_understood')}{NC}")
                example = '"password123" or "api.mycompany.com"' if LANG == "en" else '"motdepasse123" ou "api.mycompany.com"'
                print(f"  {msg('example')}: {example}")

        except (EOFError, KeyboardInterrupt):
            print()
            break

    return selected


def prompt_vibe_protections(project_root: Path) -> list[dict]:
    """Vibe-coder-friendly protection setup - no regex knowledge needed."""
    selected_patterns = []
    project_name = project_root.name

    print(f"\n{BLUE}{msg('protection_mode')}{NC}")

    print(f"\n{YELLOW}{msg('analyzing_project')}{NC}")
    found_secrets = scan_for_secrets(project_root)

    selected_patterns.extend(_prompt_secret_protections(found_secrets))
    selected_patterns.extend(_prompt_additional_categories(found_secrets))
    selected_patterns.extend(_prompt_custom_patterns(project_name))

    return selected_patterns
