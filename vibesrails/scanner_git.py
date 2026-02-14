"""Git-related utilities for vibesrails scanner."""

import subprocess
from pathlib import Path


def is_git_repo() -> bool:
    """Check if current directory is a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_staged_files() -> list[str]:
    """Get list of staged Python files."""
    # Validate git repository first
    if not is_git_repo():
        return []

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
    return [f for f in files if f and Path(f).exists()]
