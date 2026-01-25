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


def prompt_extra_patterns() -> list[dict]:
    """Ask user for additional patterns to add."""
    extra_patterns = []

    print(f"\n{YELLOW}Patterns additionnels?{NC}")
    print("  Exemples: nom de projet, API keys specifiques, etc.")
    print("  (Entree vide pour continuer)")

    while True:
        try:
            pattern_input = input(f"\n  Regex a bloquer (ou Entree): ").strip()
            if not pattern_input:
                break

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

    # Interactive: ask for extra patterns
    extra_patterns = []
    if interactive and not dry_run:
        if prompt_user("\nAjouter des patterns personnalises?", default="n"):
            extra_patterns = prompt_extra_patterns()

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
