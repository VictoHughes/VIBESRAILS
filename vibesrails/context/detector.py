"""Context detector — collects raw signals from git and filesystem."""

from __future__ import annotations

import logging
from pathlib import Path

from ..guards_v2._git_helpers import run_git
from .mode import ContextSignals

logger = logging.getLogger(__name__)

# Branch prefix → type mapping
_BRANCH_TYPES: dict[str, str] = {
    "feat/": "feature",
    "feature/": "feature",
    "spike/": "spike",
    "exp/": "spike",
    "experiment/": "spike",
    "fix/": "fix",
    "bug/": "fix",
    "bugfix/": "fix",
    "hotfix/": "fix",
    "patch/": "fix",
}

# Session mode override file
_MODE_FILE = ".vibesrails/.session_mode"


def _classify_branch(name: str) -> str:
    """Classify a branch name into a type based on its prefix."""
    lower = name.lower()
    for prefix, branch_type in _BRANCH_TYPES.items():
        if lower.startswith(prefix):
            return branch_type
    return "unknown"


def _parse_diff_stat(diff_output: str) -> tuple[float | None, int | None]:
    """Parse git diff --stat output to extract files_created_ratio and diff_spread.

    Returns:
        (files_created_ratio, diff_spread) — both None if no parseable data.
    """
    lines = [line.strip() for line in diff_output.strip().splitlines() if line.strip()]
    if not lines:
        return None, None

    # Last line is summary: "3 files changed, 100 insertions(+), 20 deletions(-)"
    # File lines look like: "path/to/file.py | 10 +++---"
    file_lines = lines[:-1] if len(lines) > 1 else []
    if not file_lines:
        return None, None

    dirs: set[str] = set()
    create_count = 0
    total_count = len(file_lines)

    for line in file_lines:
        # Extract file path (before the |)
        parts = line.split("|")
        if not parts:
            continue
        file_path = parts[0].strip()
        # Collect unique parent dirs
        parent = str(Path(file_path).parent)
        if parent != ".":
            dirs.add(parent)
        else:
            dirs.add("root")

        # Detect created files: only insertions, no deletions
        if len(parts) > 1:
            stat_part = parts[1].strip()
            if "+" in stat_part and "-" not in stat_part:
                create_count += 1

    ratio = create_count / total_count if total_count > 0 else None
    spread = len(dirs) if dirs else None
    return ratio, spread


class ContextDetector:
    """Collects raw context signals from git and filesystem."""

    def __init__(self, root: Path):
        self.root = root

    def detect(self) -> ContextSignals:
        """Collect all available signals. Missing signals are None."""
        signals = ContextSignals()

        # Signal 1: Branch name + type
        ok, branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=self.root)
        if ok and branch:
            signals.branch_name = branch.strip()
            signals.branch_type = _classify_branch(signals.branch_name)

        # Signal 2: Uncommitted files count
        ok, output = run_git(["status", "--porcelain"], cwd=self.root)
        if ok:
            dirty = [line for line in output.splitlines() if line.strip()]
            signals.uncommitted_count = len(dirty)

        # Signal 3: Files created ratio + diff spread (from last commit)
        ok, diff_output = run_git(["diff", "--stat", "HEAD~1"], cwd=self.root)
        if ok and diff_output:
            ratio, spread = _parse_diff_stat(diff_output)
            signals.files_created_ratio = ratio
            signals.diff_spread = spread

        # Signal 4: Commit frequency (commits in last hour)
        ok, log_output = run_git(
            ["log", "--oneline", "--since=1.hour.ago"], cwd=self.root
        )
        if ok:
            commits = [line for line in log_output.splitlines() if line.strip()]
            signals.commit_frequency = len(commits)

        return signals

    def read_forced_mode(self) -> str | None:
        """Read manual mode override from .vibesrails/.session_mode."""
        mode_file = self.root / _MODE_FILE
        if not mode_file.exists():
            return None
        try:
            content = mode_file.read_text().strip().lower()
            if content in ("rnd", "bugfix", "auto"):
                return content if content != "auto" else None
            return None
        except OSError:
            return None

    @staticmethod
    def write_forced_mode(root: Path, mode: str) -> None:
        """Write mode override to .vibesrails/.session_mode."""
        mode_dir = root / ".vibesrails"
        mode_dir.mkdir(exist_ok=True)
        mode_file = mode_dir / ".session_mode"
        if mode == "auto":
            # Remove override
            if mode_file.exists():
                mode_file.unlink()
            return
        mode_file.write_text(mode + "\n")
