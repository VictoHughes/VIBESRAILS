"""
vibesrails Smart Setup - Auto-configuration for Claude Code.

Analyzes project structure and creates optimized vibesrails.yaml automatically.
"""

import os
from pathlib import Path
from typing import Any

from .scanner import RED, YELLOW, GREEN, BLUE, NC


# Project type detection patterns
PROJECT_SIGNATURES = {
    "fastapi": {
        "files": ["main.py", "app.py", "api.py"],
        "imports": ["fastapi", "FastAPI"],
        "pack": "@vibesrails/fastapi-pack",
    },
    "django": {
        "files": ["manage.py", "settings.py", "wsgi.py"],
        "imports": ["django"],
        "pack": "@vibesrails/django-pack",
    },
    "flask": {
        "files": ["app.py", "wsgi.py"],
        "imports": ["flask", "Flask"],
        "pack": "@vibesrails/web-pack",
    },
    "cli": {
        "files": ["cli.py", "__main__.py"],
        "imports": ["argparse", "click", "typer"],
        "pack": None,
    },
}

# Secret patterns to detect in existing code
SECRET_INDICATORS = [
    r"api[_-]?key\s*=",
    r"password\s*=\s*[\"']",
    r"secret\s*=\s*[\"']",
    r"token\s*=\s*[\"']",
    r"AWS_",
    r"OPENAI_",
    r"ANTHROPIC_",
]

# Predefined protection categories for vibe coders (no regex knowledge needed)
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


def detect_project_type(project_root: Path) -> list[str]:
    """Detect project type(s) based on files and imports."""
    detected = []

    for project_type, signatures in PROJECT_SIGNATURES.items():
        # Check for signature files
        for sig_file in signatures["files"]:
            if list(project_root.rglob(sig_file)):
                detected.append(project_type)
                break

        # Check for imports in Python files
        if project_type not in detected:
            for py_file in project_root.rglob("*.py"):
                try:
                    content = py_file.read_text(errors="ignore")
                    for imp in signatures["imports"]:
                        if f"import {imp}" in content or f"from {imp}" in content:
                            detected.append(project_type)
                            break
                except Exception:
                    continue
                if project_type in detected:
                    break

    return list(set(detected))


def detect_existing_configs(project_root: Path) -> dict[str, Path]:
    """Detect existing config files that might have patterns."""
    configs = {}

    config_patterns = [
        ("pyproject.toml", "pyproject"),
        ("setup.py", "setup"),
        (".pre-commit-config.yaml", "pre-commit"),
        ("ruff.toml", "ruff"),
        (".flake8", "flake8"),
        ("mypy.ini", "mypy"),
    ]

    for filename, key in config_patterns:
        path = project_root / filename
        if path.exists():
            configs[key] = path

    return configs


def detect_secrets_risk(project_root: Path) -> bool:
    """Check if project has potential secret handling."""
    import re

    for py_file in project_root.rglob("*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            for pattern in SECRET_INDICATORS:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        except Exception:
            continue

    return False


def detect_env_files(project_root: Path) -> list[Path]:
    """Detect .env files that should be protected."""
    env_patterns = [".env", ".env.local", ".env.prod", ".env.development"]
    found = []

    for pattern in env_patterns:
        path = project_root / pattern
        if path.exists():
            found.append(path)

    return found


# =============================================================================
# VIBE CODER FUNCTIONS - No regex knowledge needed
# =============================================================================

def scan_for_secrets(project_root: Path) -> dict[str, list[dict]]:
    """Scan project and find actual secrets, grouped by category.

    Returns dict like:
    {
        "api_keys": [{"file": "main.py", "line": 10, "preview": "sk-abc..."}],
        "passwords": [...],
    }
    """
    import re

    found = {category: [] for category in VIBE_PROTECTIONS}

    for py_file in project_root.rglob("*.py"):
        # Skip virtual environments and cache
        if any(part in py_file.parts for part in [".venv", "venv", "__pycache__", ".git", "node_modules"]):
            continue

        try:
            content = py_file.read_text(errors="ignore")
            rel_path = py_file.relative_to(project_root)

            for line_num, line in enumerate(content.split("\n"), 1):
                # Skip comments and very long lines
                if line.strip().startswith("#") or len(line) > 500:
                    continue
                # Skip lines with vibesrails: ignore
                if "vibesrails: ignore" in line:
                    continue

                for category, config in VIBE_PROTECTIONS.items():
                    for pattern_info in config["patterns"]:
                        try:
                            match = re.search(pattern_info["regex"], line)
                            if match:
                                # Mask the secret for preview
                                secret = match.group(0)
                                if len(secret) > 8:
                                    masked = secret[:4] + "..." + secret[-4:]
                                else:
                                    masked = secret[:2] + "***"

                                found[category].append({
                                    "file": str(rel_path),
                                    "line": line_num,
                                    "preview": masked,
                                    "pattern_id": pattern_info["id"],
                                })
                        except re.error:
                            continue
        except Exception:
            continue

    # Remove empty categories
    return {k: v for k, v in found.items() if v}


def natural_language_to_pattern(description: str, project_name: str | None = None) -> dict | None:
    """Convert natural language description to a blocking pattern.

    Examples:
    - "mon nom de domaine mycompany.com" → regex for mycompany.com
    - "le nom du projet" → regex for project name
    - "emails de l'entreprise" → regex for @company.com
    """
    import re

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
            "id": f"project_name",
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


def prompt_vibe_protections(project_root: Path) -> list[dict]:
    """Vibe-coder-friendly protection setup - no regex knowledge needed.

    1. Shows found secrets and offers to block them
    2. Offers predefined protection categories
    3. Accepts natural language for custom patterns
    """
    selected_patterns = []
    project_name = project_root.name

    print(f"\n{BLUE}=== Protection du code (mode simple) ==={NC}")

    # Step 1: Scan for existing secrets
    print(f"\n{YELLOW}Analyse du projet...{NC}")
    found_secrets = scan_for_secrets(project_root)

    if found_secrets:
        total = sum(len(v) for v in found_secrets.values())
        print(f"\n{RED}⚠️  J'ai trouvé {total} secret(s) potentiel(s):{NC}")

        for category, secrets in found_secrets.items():
            cat_name = VIBE_PROTECTIONS[category]["name"]
            print(f"\n  {YELLOW}{cat_name}:{NC}")
            for secret in secrets[:3]:  # Show max 3 per category
                print(f"    • {secret['file']}:{secret['line']} → {secret['preview']}")
            if len(secrets) > 3:
                print(f"    ... et {len(secrets) - 3} autres")

        print()
        if prompt_user(f"{GREEN}Activer la protection pour ces catégories?{NC}", default="y"):
            for category in found_secrets.keys():
                selected_patterns.extend(VIBE_PROTECTIONS[category]["patterns"])
            print(f"  {GREEN}✓ Protections activées{NC}")
    else:
        print(f"  {GREEN}✓ Aucun secret détecté dans le code{NC}")

    # Step 2: Offer additional protections
    print(f"\n{YELLOW}Protections supplémentaires disponibles:{NC}")

    available_categories = [cat for cat in VIBE_PROTECTIONS if cat not in found_secrets]

    for i, category in enumerate(available_categories, 1):
        cat_name = VIBE_PROTECTIONS[category]["name"]
        print(f"  {i}. {cat_name}")

    if available_categories:
        print(f"  0. Aucune")
        print()
        choice = input("  Ajouter des protections (numéros séparés par virgule, ou 0): ").strip()

        if choice and choice != "0":
            try:
                indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
                for idx in indices:
                    if 1 <= idx <= len(available_categories):
                        category = available_categories[idx - 1]
                        selected_patterns.extend(VIBE_PROTECTIONS[category]["patterns"])
                        print(f"  {GREEN}✓ {VIBE_PROTECTIONS[category]['name']}{NC}")
            except ValueError:
                pass

    # Step 3: Natural language custom patterns
    print(f"\n{YELLOW}Protection personnalisée (langage naturel):{NC}")
    print("  Exemples: 'mycompany.com', 'le nom du projet', '@entreprise.fr'")
    print("  (Entrée vide pour terminer)")

    while True:
        try:
            user_input = input(f"\n  Que veux-tu protéger? ").strip()
            if not user_input:
                break

            pattern = natural_language_to_pattern(user_input, project_name)

            if pattern:
                print(f"  {BLUE}→ Je vais bloquer: {pattern['regex']}{NC}")
                if prompt_user("  Confirmer?", default="y"):
                    selected_patterns.append(pattern)
                    print(f"  {GREEN}✓ Ajouté{NC}")
            else:
                print(f"  {YELLOW}Je n'ai pas compris. Essaie avec une valeur précise entre guillemets.{NC}")
                print(f"  Exemple: \"motdepasse123\" ou \"api.mycompany.com\"")

        except (EOFError, KeyboardInterrupt):
            print()
            break

    return selected_patterns


def generate_config(
    project_types: list[str],
    has_secrets: bool,
    env_files: list[Path],
    existing_configs: dict[str, Path],
) -> str:
    """Generate optimized vibesrails.yaml content."""

    lines = [
        "# vibesrails.yaml - Auto-generated configuration",
        "# Detected project structure and optimized patterns",
        "",
        'version: "1.0"',
        "",
    ]

    # Extends section
    extends = ["@vibesrails/security-pack"]  # Always include security

    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in extends:
            extends.append(pack)

    if len(extends) == 1:
        lines.append(f'extends: "{extends[0]}"')
    else:
        lines.append("extends:")
        for pack in extends:
            lines.append(f'  - "{pack}"')

    lines.append("")

    # Guardian section (enabled for Claude Code)
    lines.extend([
        "# AI Coding Safety (auto-enabled in Claude Code)",
        "guardian:",
        "  enabled: true",
        "  auto_detect: true",
        "  warnings_as_blocking: false",
        "",
    ])

    # Project-specific patterns
    if has_secrets or env_files:
        lines.extend([
            "# Project-specific patterns",
            "blocking:",
        ])

        if env_files:
            lines.extend([
                "  - id: env_file_content",
                "    name: \"Env File Content\"",
                '    regex: "^[A-Z_]+=.{10,}"',
                '    scope: [".env*"]',
                '    message: "Ne pas commiter les fichiers .env"',
                "",
            ])

    # Complexity settings
    lines.extend([
        "# Quality settings",
        "complexity:",
        "  max_file_lines: 300",
        "  max_function_lines: 50",
    ])

    return "\n".join(lines)


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


def validate_and_preview_regex(pattern: str, project_root: Path) -> tuple[bool, list[str]]:
    """Validate regex and preview matches in project.

    Returns (is_valid, list of matching lines preview).
    """
    import re

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
            pattern_input = input(f"\n  Regex a bloquer (ou Entree): ").strip()
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
            confirm = input(f"  Ajouter ce pattern? [O/n]: ").strip().lower()
            if confirm in ("n", "no", "non"):
                print(f"  {YELLOW}Pattern ignore{NC}")
                continue

            message = input(f"  Message d'erreur: ").strip()
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


def get_package_data_path(relative_path: str) -> Path | None:
    """Get path to a file in the package data."""
    try:
        import importlib.resources as resources
        # Python 3.9+
        with resources.files("vibesrails").joinpath(relative_path) as p:
            if p.exists():
                return Path(p)
    except Exception:
        pass

    # Fallback: relative to this file
    pkg_path = Path(__file__).parent / relative_path
    if pkg_path.exists():
        return pkg_path
    return None


def generate_claude_md() -> str:
    """Generate CLAUDE.md content for Claude Code integration."""
    # Try to load from template
    template_path = get_package_data_path("claude_integration/CLAUDE.md.template")
    if template_path and template_path.exists():
        return template_path.read_text()

    # Fallback to hardcoded content
    return '''# vibesrails - Instructions Claude Code

## Ce projet utilise vibesrails

vibesrails scanne automatiquement chaque commit pour detecter:
- Secrets hardcodes (API keys, passwords, tokens)
- Injections SQL
- Patterns dangereux

## Regles a suivre

1. **Ne jamais hardcoder de secrets**
   ```python
   # MAUVAIS - vibesrails va bloquer
   api_key = "sk-1234567890"  # vibesrails: ignore (example)

   # BON
   import os
   api_key = os.environ.get("API_KEY")
   ```

2. **Si vibesrails bloque un faux positif**
   ```python
   code = "example"  # vibesrails: ignore
   ```

3. **Commandes utiles**
   ```bash
   vibesrails --all    # Scanner tout le projet
   vibesrails --fix    # Auto-corriger les patterns simples
   vibesrails --show   # Voir les patterns actifs
   ```

## Guardian Mode

vibesrails detecte automatiquement Claude Code et active le mode Guardian:
- Verifications plus strictes pour le code genere par AI
- Les warnings peuvent devenir des blocks

## Configuration

Fichier: `vibesrails.yaml`
'''


def install_claude_hooks(project_root: Path) -> bool:
    """Install Claude Code hooks for vibesrails integration."""
    import json

    hooks_source = get_package_data_path("claude_integration/hooks.json")
    if not hooks_source or not hooks_source.exists():
        return False

    # Claude Code hooks go in .claude/settings.local.json or project root
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(exist_ok=True)

    hooks_dest = claude_dir / "hooks.json"

    # Load source hooks
    source_hooks = json.loads(hooks_source.read_text())

    # If hooks file exists, merge; otherwise create
    if hooks_dest.exists():
        existing = json.loads(hooks_dest.read_text())
        # Merge hooks
        for event, handlers in source_hooks.get("hooks", {}).items():
            if event not in existing.get("hooks", {}):
                existing.setdefault("hooks", {})[event] = handlers
            else:
                # Check if vibesrails hook already exists
                existing_commands = [h.get("command", "") for h in existing["hooks"][event]]
                for handler in handlers:
                    if "vibesrails" in handler.get("command", "") and \
                       not any("vibesrails" in cmd for cmd in existing_commands):
                        existing["hooks"][event].append(handler)
        hooks_dest.write_text(json.dumps(existing, indent=2))
    else:
        hooks_dest.write_text(json.dumps(source_hooks, indent=2))

    return True


def generate_config_with_extras(
    project_types: list[str],
    has_secrets: bool,
    env_files: list[Path],
    existing_configs: dict[str, Path],
    extra_patterns: list[dict],
) -> str:
    """Generate optimized vibesrails.yaml content with extra patterns."""

    lines = [
        "# vibesrails.yaml - Configuration generee par Smart Setup",
        "# Modifiez selon vos besoins",
        "",
        'version: "1.0"',
        "",
    ]

    # Extends section
    extends = ["@vibesrails/security-pack"]  # Always include security

    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in extends:
            extends.append(pack)

    if len(extends) == 1:
        lines.append(f'extends: "{extends[0]}"')
    else:
        lines.append("extends:")
        for pack in extends:
            lines.append(f'  - "{pack}"')

    lines.append("")

    # Guardian section (enabled for Claude Code)
    lines.extend([
        "# AI Coding Safety (auto-enabled in Claude Code)",
        "guardian:",
        "  enabled: true",
        "  auto_detect: true",
        "  warnings_as_blocking: false",
        "",
    ])

    # Project-specific patterns
    has_blocking = has_secrets or env_files or extra_patterns
    if has_blocking:
        lines.extend([
            "# Project-specific patterns",
            "blocking:",
        ])

        if env_files:
            lines.extend([
                "  - id: env_file_content",
                "    name: \"Env File Content\"",
                '    regex: "^[A-Z_]+=.{10,}"',
                '    scope: [".env*"]',
                '    message: "Ne pas commiter les fichiers .env"',
                "",
            ])

        # Add extra patterns from user
        for pattern in extra_patterns:
            lines.extend([
                f"  - id: {pattern['id']}",
                f"    name: \"Custom Pattern\"",
                f'    regex: "{pattern["regex"]}"',
                f'    message: "{pattern["message"]}"',
                "",
            ])

    # Complexity settings
    lines.extend([
        "# Quality settings",
        "complexity:",
        "  max_file_lines: 300",
        "  max_function_lines: 50",
    ])

    return "\n".join(lines)


def smart_setup(
    project_root: Path | None = None,
    dry_run: bool = False,
    interactive: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Run smart setup analysis with user confirmation.

    Args:
        project_root: Project directory (defaults to cwd)
        dry_run: If True, only analyze without creating files
        interactive: If True, ask for user confirmation
        force: If True, overwrite existing config

    Returns:
        Analysis results dict
    """
    if project_root is None:
        project_root = Path.cwd()

    project_root = Path(project_root).resolve()

    print(f"{BLUE}vibesrails Smart Setup{NC}")
    print("=" * 40)
    print(f"Analyzing: {project_root.name}/")
    print()

    # Detect project characteristics
    project_types = detect_project_type(project_root)
    existing_configs = detect_existing_configs(project_root)
    has_secrets = detect_secrets_risk(project_root)
    env_files = detect_env_files(project_root)

    # Report findings
    print(f"{YELLOW}Analyse du projet:{NC}")

    if project_types:
        print(f"  Type(s) detecte(s): {', '.join(project_types)}")
    else:
        print("  Type: Python generique")

    packs_to_use = ["@vibesrails/security-pack"]
    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in packs_to_use:
            packs_to_use.append(pack)

    print(f"  Packs a inclure: {', '.join(packs_to_use)}")

    if existing_configs:
        print(f"  Configs existants: {', '.join(existing_configs.keys())}")

    if has_secrets:
        print(f"  {RED}! Patterns de secrets detectes dans le code{NC}")

    if env_files:
        print(f"  Fichiers .env: {', '.join(f.name for f in env_files)}")

    # Check if config already exists
    config_path = project_root / "vibesrails.yaml"
    if config_path.exists() and not force:
        print(f"\n{YELLOW}vibesrails.yaml existe deja{NC}")
        if interactive:
            if not prompt_user("Ecraser la configuration existante?", default="n"):
                print(f"{YELLOW}Setup annule{NC}")
                return {"created": False, "reason": "exists"}
        else:
            print("Utilisez --force pour ecraser")
            return {"created": False, "reason": "exists"}

    # Interactive: ask for protections (vibe coder mode by default)
    extra_patterns = []
    if interactive and not dry_run:
        print(f"\n{YELLOW}Mode de configuration:{NC}")
        print("  1. Simple (recommandé) - Je te guide, pas besoin de connaître les regex")
        print("  2. Avancé - Tu entres les regex toi-même")
        print("  3. Passer - Utiliser la config par défaut")

        mode = input("\n  Choix [1/2/3]: ").strip()

        if mode == "1":
            extra_patterns = prompt_vibe_protections(project_root)
        elif mode == "2":
            extra_patterns = prompt_extra_patterns(project_root)
        # mode 3 or other = skip

    # Generate config
    config_content = generate_config_with_extras(
        project_types, has_secrets, env_files, existing_configs, extra_patterns
    )

    # Show preview
    print(f"\n{YELLOW}Configuration proposee:{NC}")
    print("-" * 40)
    print(config_content)
    print("-" * 40)

    result = {
        "project_root": str(project_root),
        "project_types": project_types,
        "existing_configs": list(existing_configs.keys()),
        "has_secrets": has_secrets,
        "env_files": [str(f) for f in env_files],
        "extra_patterns": extra_patterns,
        "config_content": config_content,
    }

    if dry_run:
        print(f"\n{YELLOW}(Mode dry-run - aucun fichier cree){NC}")
        result["created"] = False
        return result

    # Final confirmation
    if interactive:
        print()
        if not prompt_user(f"{GREEN}Creer vibesrails.yaml et installer le hook?{NC}"):
            print(f"{YELLOW}Setup annule{NC}")
            result["created"] = False
            return result

    # Create config file
    config_path.write_text(config_content)
    print(f"\n{GREEN}Cree: vibesrails.yaml{NC}")
    result["created"] = True

    # Install hook
    from .cli import install_hook
    install_hook()

    # Create or update CLAUDE.md for Claude Code integration
    claude_md_path = project_root / "CLAUDE.md"
    claude_md_content = generate_claude_md()

    if claude_md_path.exists():
        # Append vibesrails section if not already present
        existing_content = claude_md_path.read_text()
        if "vibesrails" not in existing_content.lower():
            claude_md_path.write_text(existing_content + "\n\n" + claude_md_content)
            print(f"{GREEN}Mis a jour: CLAUDE.md (section vibesrails ajoutee){NC}")
        else:
            print(f"{YELLOW}CLAUDE.md existe deja avec instructions vibesrails{NC}")
    else:
        claude_md_path.write_text(claude_md_content)
        print(f"{GREEN}Cree: CLAUDE.md (instructions pour Claude Code){NC}")

    result["claude_md_created"] = True

    # Offer Claude Code hooks installation
    result["hooks_installed"] = False
    if interactive:
        print()
        if prompt_user(f"{BLUE}Installer les hooks Claude Code (integration avancee)?{NC}", default="y"):
            if install_claude_hooks(project_root):
                print(f"{GREEN}Cree: .claude/hooks.json (hooks Claude Code){NC}")
                result["hooks_installed"] = True
            else:
                print(f"{YELLOW}Hooks non disponibles dans cette installation{NC}")
    else:
        # Non-interactive: install hooks by default
        if install_claude_hooks(project_root):
            print(f"{GREEN}Cree: .claude/hooks.json (hooks Claude Code){NC}")
            result["hooks_installed"] = True

    print()
    print(f"{GREEN}Smart Setup termine!{NC}")
    print(f"\nFichiers crees:")
    print(f"  - vibesrails.yaml (configuration)")
    print(f"  - .git/hooks/pre-commit (scan automatique)")
    print(f"  - CLAUDE.md (instructions Claude Code)")
    if result["hooks_installed"]:
        print(f"  - .claude/hooks.json (integration Claude Code)")
    print(f"\nProchaines etapes:")
    print(f"  1. Commitez normalement - vibesrails scanne automatiquement")
    print(f"  2. Pour scanner tout: vibesrails --all")

    return result


def run_smart_setup_cli(force: bool = False, dry_run: bool = False) -> bool:
    """CLI entry point for smart setup."""
    try:
        # Check if running in interactive terminal
        interactive = os.isatty(0)  # stdin is a terminal

        result = smart_setup(
            dry_run=dry_run,
            interactive=interactive,
            force=force,
        )
        return result.get("created", False) or dry_run
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return False
