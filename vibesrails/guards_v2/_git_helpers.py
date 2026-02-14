"""Git workflow constants and helpers — extracted from git_workflow.py."""

import re
import subprocess
from pathlib import Path

VALID_BRANCH_PREFIXES = (
    "feature/",
    "fix/",
    "chore/",
    "docs/",
    "refactor/",
)

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|refactor|test|docs|chore|style|perf|ci|build)"
    r"(\([a-zA-Z0-9_\-]+\))?:\s.+"
)

MAX_UNRELATED_DIRS = 3

# Patterns for files/dirs that should never be tracked in git
# Each entry: (glob pattern for git ls-files matching, description)
TRACKED_FILE_BLOCKLIST: list[tuple[str, str]] = [
    (".vibesrails/metrics/", "vibesrails metrics (local state)"),
    (".vibesrails/guardian.log", "guardian log (local state)"),
    (".claude/settings.local.json", "Claude local settings"),
    (".coverage", "coverage data"),
    ("htmlcov/", "HTML coverage report"),
    (".pytest_cache/", "pytest cache"),
    ("__pycache__/", "Python bytecode cache"),
    ("*.egg-info/", "egg-info build artifact"),
    ("dist/", "distribution build"),
    ("build/", "build directory"),
    (".DS_Store", "macOS metadata"),
    ("*.pyc", "compiled bytecode"),
]


def run_git(
    args: list[str],
    cwd: Path,
) -> tuple[bool, str]:
    """Run a git command, return (success, stdout)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""
