"""
vibesrails Smart Setup - Project Detection.

Functions to detect project type, configs, secrets, and architecture.
"""

import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

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


# =============================================================================
# PROJECT TYPE DETECTION
# =============================================================================


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
                    logger.debug("Failed to read file during project detection")
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
    for py_file in project_root.rglob("*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            for pattern in SECRET_INDICATORS:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
        except Exception:
            logger.debug("Failed to read file during secret detection")
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
# LANGUAGE DETECTION
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


# =============================================================================
# ARCHITECTURE DETECTION
# =============================================================================


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
    tool_info = ARCHITECTURE_TOOLS.get(language)
    if not tool_info:
        return False

    if language == "python":
        return shutil.which("lint-imports") is not None
    elif language in ("javascript", "typescript"):
        # Check if dependency-cruiser is in node_modules
        return Path("node_modules/.bin/depcruise").exists()
    return False
