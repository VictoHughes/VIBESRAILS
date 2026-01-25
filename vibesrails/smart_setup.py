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


def smart_setup(project_root: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Run smart setup analysis and optionally create config.

    Args:
        project_root: Project directory (defaults to cwd)
        dry_run: If True, only analyze without creating files

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
    print(f"{YELLOW}Project Analysis:{NC}")

    if project_types:
        print(f"  Type(s): {', '.join(project_types)}")
    else:
        print("  Type: Generic Python")

    if existing_configs:
        print(f"  Existing configs: {', '.join(existing_configs.keys())}")

    if has_secrets:
        print(f"  {RED}Secret patterns detected in code{NC}")

    if env_files:
        print(f"  Env files: {', '.join(f.name for f in env_files)}")

    print()

    # Generate config
    config_content = generate_config(
        project_types, has_secrets, env_files, existing_configs
    )

    result = {
        "project_root": str(project_root),
        "project_types": project_types,
        "existing_configs": list(existing_configs.keys()),
        "has_secrets": has_secrets,
        "env_files": [str(f) for f in env_files],
        "config_content": config_content,
    }

    if dry_run:
        print(f"{YELLOW}Generated config (dry run):{NC}")
        print("-" * 40)
        print(config_content)
        print("-" * 40)
    else:
        # Create config file
        config_path = project_root / "vibesrails.yaml"

        if config_path.exists():
            print(f"{YELLOW}vibesrails.yaml already exists{NC}")
            print("Use --force to overwrite")
            result["created"] = False
        else:
            config_path.write_text(config_content)
            print(f"{GREEN}Created vibesrails.yaml{NC}")
            result["created"] = True

            # Also install hook
            from .cli import install_hook
            install_hook()

    print()
    print(f"{GREEN}Smart Setup Complete{NC}")

    return result


def run_smart_setup_cli(force: bool = False, dry_run: bool = False) -> bool:
    """CLI entry point for smart setup."""
    try:
        result = smart_setup(dry_run=dry_run)
        return result.get("created", False) or dry_run
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return False
