"""
vibesrails Smart Setup - Auto-configuration for Claude Code.

Analyzes project structure and creates optimized vibesrails.yaml automatically.
"""

import os
from pathlib import Path
from typing import Any

from .scanner import RED, YELLOW, GREEN, BLUE, NC


# =============================================================================
# INTERNATIONALIZATION (i18n) - Default: English, Auto-detect French
# =============================================================================

def _detect_language() -> str:
    """Detect user language from environment. Default: English."""
    lang = os.environ.get("LANG", "").lower()
    lang_var = os.environ.get("LANGUAGE", "").lower()
    # Check for French
    if lang.startswith("fr") or lang_var.startswith("fr"):
        return "fr"
    return "en"

LANG = _detect_language()

# Message translations
MESSAGES = {
    "en": {
        "smart_setup": "vibesrails Smart Setup",
        "analyzing": "Analyzing",
        "project_analysis": "Project analysis:",
        "detected_types": "Detected type(s)",
        "generic_python": "Generic Python",
        "packs_to_include": "Packs to include",
        "existing_configs": "Existing configs",
        "secret_patterns_detected": "! Secret patterns detected in code",
        "env_files": ".env files",
        "config_exists": "vibesrails.yaml already exists",
        "overwrite_config": "Overwrite existing configuration?",
        "setup_cancelled": "Setup cancelled",
        "use_force": "Use --force to overwrite",
        "config_mode": "Configuration mode:",
        "mode_simple": "Simple (recommended) - I'll guide you, no regex knowledge needed",
        "mode_advanced": "Advanced - Enter regex patterns yourself",
        "mode_skip": "Skip - Use default config",
        "choice": "Choice",
        "proposed_config": "Proposed configuration:",
        "create_config": "Create vibesrails.yaml and install hook?",
        "created": "Created",
        "updated": "Updated",
        "install_hooks": "Install Claude Code hooks (advanced integration)?",
        "hooks_not_available": "Hooks not available in this installation",
        "setup_complete": "Smart Setup complete!",
        "files_created": "Files created",
        "config_file": "configuration",
        "auto_scan": "automatic scan",
        "claude_instructions": "Claude Code instructions",
        "claude_hooks": "Claude Code integration",
        "next_steps": "Next steps",
        "commit_normally": "Commit normally - vibesrails scans automatically",
        "scan_all": "To scan everything",
        # Vibe coder messages
        "protection_mode": "=== Code Protection (simple mode) ===",
        "analyzing_project": "Analyzing project...",
        "found_secrets": "I found {count} potential secret(s):",
        "no_secrets_found": "No secrets detected in code",
        "enable_protection": "Enable protection for these categories?",
        "protections_enabled": "Protections enabled",
        "additional_protections": "Additional protections available:",
        "none": "None",
        "add_protections": "Add protections (comma-separated numbers, or 0)",
        "custom_protection": "Custom protection (natural language):",
        "examples": "Examples",
        "empty_to_finish": "(empty to finish)",
        "what_to_protect": "What do you want to protect?",
        "will_block": "I will block",
        "confirm": "Confirm?",
        "added": "Added",
        "not_understood": "I didn't understand. Try with a specific value in quotes.",
        "example": "Example",
        "pattern_ignored": "Pattern ignored",
        # Regex validation
        "invalid_regex": "Invalid regex",
        "dangerous_regex": "Potentially dangerous regex (ReDoS)",
        "preview_matches": "Preview of matches ({count} found):",
        "no_matches": "No matches found in current project",
        "add_pattern": "Add this pattern?",
        "regex_to_block": "Regex to block (or Enter)",
        "error_message": "Error message",
        "forbidden_pattern": "Forbidden pattern",
        "additional_patterns": "Additional patterns?",
        "custom_patterns": "Add custom patterns?",
        # Architecture messages
        "arch_detected": "Architecture detected",
        "arch_layers": "layers",
        "arch_suggest": "Enable architecture checking (import-linter)?",
        "arch_install_cmd": "Install command",
        "arch_config_created": "Architecture config created",
        "arch_simple_project": "Simple project - architecture check not needed",
        "arch_tool_missing": "Architecture tool not installed (optional)",
        "arch_will_check": "Pre-commit will check: security + architecture",
    },
    "fr": {
        "smart_setup": "vibesrails Smart Setup",
        "analyzing": "Analyse",
        "project_analysis": "Analyse du projet:",
        "detected_types": "Type(s) detecte(s)",
        "generic_python": "Python generique",
        "packs_to_include": "Packs a inclure",
        "existing_configs": "Configs existants",
        "secret_patterns_detected": "! Patterns de secrets detectes dans le code",
        "env_files": "Fichiers .env",
        "config_exists": "vibesrails.yaml existe deja",
        "overwrite_config": "Ecraser la configuration existante?",
        "setup_cancelled": "Setup annule",
        "use_force": "Utilisez --force pour ecraser",
        "config_mode": "Mode de configuration:",
        "mode_simple": "Simple (recommande) - Je te guide, pas besoin de connaitre les regex",
        "mode_advanced": "Avance - Tu entres les regex toi-meme",
        "mode_skip": "Passer - Utiliser la config par defaut",
        "choice": "Choix",
        "proposed_config": "Configuration proposee:",
        "create_config": "Creer vibesrails.yaml et installer le hook?",
        "created": "Cree",
        "updated": "Mis a jour",
        "install_hooks": "Installer les hooks Claude Code (integration avancee)?",
        "hooks_not_available": "Hooks non disponibles dans cette installation",
        "setup_complete": "Smart Setup termine!",
        "files_created": "Fichiers crees",
        "config_file": "configuration",
        "auto_scan": "scan automatique",
        "claude_instructions": "instructions Claude Code",
        "claude_hooks": "integration Claude Code",
        "next_steps": "Prochaines etapes",
        "commit_normally": "Commitez normalement - vibesrails scanne automatiquement",
        "scan_all": "Pour scanner tout",
        # Vibe coder messages
        "protection_mode": "=== Protection du code (mode simple) ===",
        "analyzing_project": "Analyse du projet...",
        "found_secrets": "J'ai trouve {count} secret(s) potentiel(s):",
        "no_secrets_found": "Aucun secret detecte dans le code",
        "enable_protection": "Activer la protection pour ces categories?",
        "protections_enabled": "Protections activees",
        "additional_protections": "Protections supplementaires disponibles:",
        "none": "Aucune",
        "add_protections": "Ajouter des protections (numeros separes par virgule, ou 0)",
        "custom_protection": "Protection personnalisee (langage naturel):",
        "examples": "Exemples",
        "empty_to_finish": "(Entree vide pour terminer)",
        "what_to_protect": "Que veux-tu proteger?",
        "will_block": "Je vais bloquer",
        "confirm": "Confirmer?",
        "added": "Ajoute",
        "not_understood": "Je n'ai pas compris. Essaie avec une valeur precise entre guillemets.",
        "example": "Exemple",
        "pattern_ignored": "Pattern ignore",
        # Regex validation
        "invalid_regex": "Regex invalide",
        "dangerous_regex": "Regex potentiellement dangereuse (ReDoS)",
        "preview_matches": "Apercu des matches ({count} trouve(s)):",
        "no_matches": "Aucun match trouve dans le projet actuel",
        "add_pattern": "Ajouter ce pattern?",
        "regex_to_block": "Regex a bloquer (ou Entree)",
        "error_message": "Message d'erreur",
        "forbidden_pattern": "Pattern interdit",
        "additional_patterns": "Patterns additionnels?",
        "custom_patterns": "Ajouter des patterns personnalises?",
        # Architecture messages
        "arch_detected": "Architecture detectee",
        "arch_layers": "couches",
        "arch_suggest": "Activer la verification d'architecture (import-linter)?",
        "arch_install_cmd": "Commande d'installation",
        "arch_config_created": "Config architecture creee",
        "arch_simple_project": "Projet simple - verification architecture non necessaire",
        "arch_tool_missing": "Outil architecture non installe (optionnel)",
        "arch_will_check": "Pre-commit verifiera: securite + architecture",
    },
}

def msg(key: str, **kwargs) -> str:
    """Get translated message."""
    text = MESSAGES.get(LANG, MESSAGES["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


# Architecture tools by language
ARCHITECTURE_TOOLS = {
    "python": {
        "tool": "import-linter",
        "install": "pip install import-linter",
        "config_file": ".importlinter",
        "run_cmd": "lint-imports",
    },
    "javascript": {
        "tool": "dependency-cruiser",
        "install": "npm install -D dependency-cruiser",
        "config_file": ".dependency-cruiser.js",
        "run_cmd": "npx depcruise src",
    },
    "typescript": {
        "tool": "dependency-cruiser",
        "install": "npm install -D dependency-cruiser",
        "config_file": ".dependency-cruiser.js",
        "run_cmd": "npx depcruise src",
    },
}

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
# ARCHITECTURE CHECKING
# =============================================================================

def detect_project_language(project_root: Path) -> str:
    """Detect primary project language."""
    # Check for Python
    py_files = list(project_root.rglob("*.py"))
    py_count = len([f for f in py_files if ".venv" not in str(f) and "venv" not in str(f)])

    # Check for JS/TS
    js_files = list(project_root.rglob("*.js")) + list(project_root.rglob("*.jsx"))
    ts_files = list(project_root.rglob("*.ts")) + list(project_root.rglob("*.tsx"))
    js_count = len([f for f in js_files if "node_modules" not in str(f)])
    ts_count = len([f for f in ts_files if "node_modules" not in str(f)])

    if ts_count > js_count and ts_count > py_count:
        return "typescript"
    if js_count > py_count:
        return "javascript"
    return "python"


def detect_architecture_complexity(project_root: Path) -> dict:
    """Detect if project is complex enough to need architecture checking.

    Returns dict with:
    - needs_arch: bool
    - reason: str
    - directories: list of main source directories
    - language: str
    """
    language = detect_project_language(project_root)

    # Find source directories (potential layers)
    src_dirs = set()
    layer_keywords = ["domain", "api", "infra", "infrastructure", "core", "services",
                      "models", "views", "controllers", "handlers", "adapters"]

    for item in project_root.iterdir():
        if item.is_dir() and not item.name.startswith(".") and item.name not in [
            "venv", ".venv", "node_modules", "__pycache__", "dist", "build", "tests", "test"
        ]:
            src_dirs.add(item.name)
            # Check subdirectories
            for subdir in item.iterdir():
                if subdir.is_dir() and subdir.name in layer_keywords:
                    src_dirs.add(f"{item.name}/{subdir.name}")

    # Detect layers
    detected_layers = [d for d in src_dirs if any(kw in d.lower() for kw in layer_keywords)]

    # Decision logic
    needs_arch = len(detected_layers) >= 2 or len(src_dirs) >= 4

    if needs_arch:
        reason = f"Detected {len(detected_layers)} architectural layers"
    else:
        reason = "Simple project structure"

    return {
        "needs_arch": needs_arch,
        "reason": reason,
        "directories": list(src_dirs),
        "layers": detected_layers,
        "language": language,
    }


def check_architecture_tool_installed(language: str) -> bool:
    """Check if the architecture tool for the language is installed."""
    import shutil

    tool_info = ARCHITECTURE_TOOLS.get(language)
    if not tool_info:
        return False

    tool = tool_info["tool"]
    if language == "python":
        return shutil.which("lint-imports") is not None
    elif language in ("javascript", "typescript"):
        # Check if dependency-cruiser is in node_modules
        return Path("node_modules/.bin/depcruise").exists()
    return False


def generate_importlinter_config(project_root: Path, layers: list[str]) -> str:
    """Generate .importlinter config based on detected layers."""
    # Find the root package name
    root_package = None
    for item in project_root.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            root_package = item.name
            break

    if not root_package:
        root_package = project_root.name.replace("-", "_")

    lines = [
        "[importlinter]",
        f"root_package = {root_package}",
        "",
    ]

    # Generate contracts based on detected layers
    contract_num = 1

    # Domain independence (if domain layer exists)
    domain_layers = [l for l in layers if "domain" in l.lower() or "core" in l.lower()]
    if domain_layers:
        for layer in domain_layers:
            layer_module = layer.replace("/", ".")
            lines.extend([
                f"[importlinter:contract:{contract_num}]",
                f"name = {layer} has no external dependencies",
                "type = independence",
                f"modules = {root_package}.{layer_module}",
                "",
            ])
            contract_num += 1

    # Layer contract (if multiple layers)
    if len(layers) >= 2:
        # Sort layers by typical dependency order
        layer_order = ["api", "handler", "controller", "service", "infra", "infrastructure", "adapter", "domain", "core", "model"]
        sorted_layers = sorted(layers, key=lambda l: next((i for i, kw in enumerate(layer_order) if kw in l.lower()), 99))

        lines.extend([
            f"[importlinter:contract:{contract_num}]",
            "name = Architectural layers",
            "type = layers",
            "layers =",
        ])
        for layer in sorted_layers:
            layer_module = layer.replace("/", ".")
            lines.append(f"    {root_package}.{layer_module}")
        lines.append("")

    return "\n".join(lines)


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

    print(f"\n{BLUE}{msg('protection_mode')}{NC}")

    # Step 1: Scan for existing secrets
    print(f"\n{YELLOW}{msg('analyzing_project')}{NC}")
    found_secrets = scan_for_secrets(project_root)

    if found_secrets:
        total = sum(len(v) for v in found_secrets.values())
        print(f"\n{RED}⚠️  {msg('found_secrets', count=total)}{NC}")

        for category, secrets in found_secrets.items():
            cat_name = VIBE_PROTECTIONS[category]["name"]
            print(f"\n  {YELLOW}{cat_name}:{NC}")
            for secret in secrets[:3]:  # Show max 3 per category
                print(f"    • {secret['file']}:{secret['line']} → {secret['preview']}")
            if len(secrets) > 3:
                remaining = len(secrets) - 3
                more = "and" if LANG == "en" else "et"
                others = "others" if LANG == "en" else "autres"
                print(f"    ... {more} {remaining} {others}")

        print()
        if prompt_user(f"{GREEN}{msg('enable_protection')}{NC}", default="y"):
            for category in found_secrets.keys():
                selected_patterns.extend(VIBE_PROTECTIONS[category]["patterns"])
            print(f"  {GREEN}✓ {msg('protections_enabled')}{NC}")
    else:
        print(f"  {GREEN}✓ {msg('no_secrets_found')}{NC}")

    # Step 2: Offer additional protections
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
                        selected_patterns.extend(VIBE_PROTECTIONS[category]["patterns"])
                        print(f"  {GREEN}✓ {VIBE_PROTECTIONS[category]['name']}{NC}")
            except ValueError:
                pass

    # Step 3: Natural language custom patterns
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
                    selected_patterns.append(pattern)
                    print(f"  {GREEN}✓ {msg('added')}{NC}")
            else:
                print(f"  {YELLOW}{msg('not_understood')}{NC}")
                example = '"password123" or "api.mycompany.com"' if LANG == "en" else '"motdepasse123" ou "api.mycompany.com"'
                print(f"  {msg('example')}: {example}")

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
    architecture: dict | None = None,
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

    # Project-specific patterns (only add if there are actual patterns)
    has_actual_patterns = env_files or extra_patterns
    if has_actual_patterns:
        lines.extend([
            "# Project-specific patterns",
            "blocking:",
        ])

        if env_files:
            env_msg = "Do not commit .env files" if LANG == "en" else "Ne pas commiter les fichiers .env"
            lines.extend([
                "  - id: env_file_content",
                "    name: \"Env File Content\"",
                '    regex: "^[A-Z_]+=.{10,}"',
                '    scope: [".env*"]',
                f'    message: "{env_msg}"',
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

    # Architecture settings (if enabled)
    if architecture and architecture.get("enabled"):
        tool_info = ARCHITECTURE_TOOLS.get(architecture.get("language", "python"), {})
        lines.extend([
            "# Architecture checking (pre-commit)",
            "architecture:",
            "  enabled: true",
            f"  tool: {tool_info.get('tool', 'import-linter')}",
            f"  config: {tool_info.get('config_file', '.importlinter')}",
            "  # Fails silently if tool not installed",
            f"  # Install: {tool_info.get('install', 'pip install import-linter')}",
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

    print(f"{BLUE}{msg('smart_setup')}{NC}")
    print("=" * 40)
    print(f"{msg('analyzing')}: {project_root.name}/")
    print()

    # Detect project characteristics
    project_types = detect_project_type(project_root)
    existing_configs = detect_existing_configs(project_root)
    has_secrets = detect_secrets_risk(project_root)
    env_files = detect_env_files(project_root)
    arch_info = detect_architecture_complexity(project_root)

    # Report findings
    print(f"{YELLOW}{msg('project_analysis')}{NC}")

    if project_types:
        print(f"  {msg('detected_types')}: {', '.join(project_types)}")
    else:
        print(f"  Type: {msg('generic_python')}")

    packs_to_use = ["@vibesrails/security-pack"]
    for proj_type in project_types:
        pack = PROJECT_SIGNATURES.get(proj_type, {}).get("pack")
        if pack and pack not in packs_to_use:
            packs_to_use.append(pack)

    print(f"  {msg('packs_to_include')}: {', '.join(packs_to_use)}")

    if existing_configs:
        print(f"  {msg('existing_configs')}: {', '.join(existing_configs.keys())}")

    if has_secrets:
        print(f"  {RED}{msg('secret_patterns_detected')}{NC}")

    if env_files:
        print(f"  {msg('env_files')}: {', '.join(f.name for f in env_files)}")

    # Show architecture info
    if arch_info["needs_arch"]:
        print(f"  {BLUE}{msg('arch_detected')}: {len(arch_info['layers'])} {msg('arch_layers')}{NC}")
        for layer in arch_info["layers"][:5]:
            print(f"    • {layer}")
    else:
        print(f"  {msg('arch_simple_project')}")

    # Check if config already exists
    config_path = project_root / "vibesrails.yaml"
    if config_path.exists() and not force:
        print(f"\n{YELLOW}{msg('config_exists')}{NC}")
        if interactive:
            if not prompt_user(msg('overwrite_config'), default="n"):
                print(f"{YELLOW}{msg('setup_cancelled')}{NC}")
                return {"created": False, "reason": "exists"}
        else:
            print(msg('use_force'))
            return {"created": False, "reason": "exists"}

    # Interactive: ask for protections (vibe coder mode by default)
    extra_patterns = []
    if interactive and not dry_run:
        print(f"\n{YELLOW}{msg('config_mode')}{NC}")
        print(f"  1. {msg('mode_simple')}")
        print(f"  2. {msg('mode_advanced')}")
        print(f"  3. {msg('mode_skip')}")

        mode = input(f"\n  {msg('choice')} [1/2/3]: ").strip()

        if mode == "1":
            extra_patterns = prompt_vibe_protections(project_root)
        elif mode == "2":
            extra_patterns = prompt_extra_patterns(project_root)
        # mode 3 or other = skip

    # Architecture checking (offer if complex project)
    architecture_config = None
    if arch_info["needs_arch"] and interactive and not dry_run:
        print()
        if prompt_user(f"{BLUE}{msg('arch_suggest')}{NC}", default="y"):
            architecture_config = {
                "enabled": True,
                "language": arch_info["language"],
                "layers": arch_info["layers"],
            }
            tool_info = ARCHITECTURE_TOOLS.get(arch_info["language"], {})
            print(f"  {GREEN}✓ {msg('arch_will_check')}{NC}")
            print(f"  {msg('arch_install_cmd')}: {tool_info.get('install', 'pip install import-linter')}")

    # Generate config
    config_content = generate_config_with_extras(
        project_types, has_secrets, env_files, existing_configs, extra_patterns,
        architecture=architecture_config
    )

    # Show preview
    print(f"\n{YELLOW}{msg('proposed_config')}{NC}")
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
        "architecture": architecture_config,
    }

    if dry_run:
        dry_run_msg = "(Dry-run mode - no files created)" if LANG == "en" else "(Mode dry-run - aucun fichier cree)"
        print(f"\n{YELLOW}{dry_run_msg}{NC}")
        result["created"] = False
        return result

    # Final confirmation
    if interactive:
        print()
        if not prompt_user(f"{GREEN}{msg('create_config')}{NC}"):
            print(f"{YELLOW}{msg('setup_cancelled')}{NC}")
            result["created"] = False
            return result

    # Create config file
    config_path.write_text(config_content)
    print(f"\n{GREEN}{msg('created')}: vibesrails.yaml{NC}")
    result["created"] = True

    # Create architecture config if enabled
    if architecture_config and architecture_config.get("enabled"):
        lang = architecture_config.get("language", "python")
        if lang == "python":
            importlinter_path = project_root / ".importlinter"
            if not importlinter_path.exists():
                importlinter_content = generate_importlinter_config(
                    project_root, architecture_config.get("layers", [])
                )
                importlinter_path.write_text(importlinter_content)
                print(f"{GREEN}{msg('created')}: .importlinter ({msg('arch_config_created')}){NC}")
        result["architecture_config_created"] = True

    # Install hook (with architecture support)
    from .cli import install_hook
    install_hook(architecture_enabled=architecture_config is not None)

    # Create or update CLAUDE.md for Claude Code integration
    claude_md_path = project_root / "CLAUDE.md"
    claude_md_content = generate_claude_md()

    if claude_md_path.exists():
        # Append vibesrails section if not already present
        existing_content = claude_md_path.read_text()
        if "vibesrails" not in existing_content.lower():
            claude_md_path.write_text(existing_content + "\n\n" + claude_md_content)
            print(f"{GREEN}{msg('updated')}: CLAUDE.md ({msg('claude_instructions')}){NC}")
        else:
            existing_msg = "CLAUDE.md already has vibesrails instructions" if LANG == "en" else "CLAUDE.md existe deja avec instructions vibesrails"
            print(f"{YELLOW}{existing_msg}{NC}")
    else:
        claude_md_path.write_text(claude_md_content)
        print(f"{GREEN}{msg('created')}: CLAUDE.md ({msg('claude_instructions')}){NC}")

    result["claude_md_created"] = True

    # Offer Claude Code hooks installation
    result["hooks_installed"] = False
    if interactive:
        print()
        if prompt_user(f"{BLUE}{msg('install_hooks')}{NC}", default="y"):
            if install_claude_hooks(project_root):
                print(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
                result["hooks_installed"] = True
            else:
                print(f"{YELLOW}{msg('hooks_not_available')}{NC}")
    else:
        # Non-interactive: install hooks by default
        if install_claude_hooks(project_root):
            print(f"{GREEN}{msg('created')}: .claude/hooks.json ({msg('claude_hooks')}){NC}")
            result["hooks_installed"] = True

    print()
    print(f"{GREEN}{msg('setup_complete')}{NC}")
    print(f"\n{msg('files_created')}:")
    print(f"  - vibesrails.yaml ({msg('config_file')})")
    print(f"  - .git/hooks/pre-commit ({msg('auto_scan')})")
    print(f"  - CLAUDE.md ({msg('claude_instructions')})")
    if result["hooks_installed"]:
        print(f"  - .claude/hooks.json ({msg('claude_hooks')})")
    print(f"\n{msg('next_steps')}:")
    print(f"  1. {msg('commit_normally')}")
    print(f"  2. {msg('scan_all')}: vibesrails --all")
    print(f"\n{BLUE}A.B.H.A.M.H{NC}")

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
