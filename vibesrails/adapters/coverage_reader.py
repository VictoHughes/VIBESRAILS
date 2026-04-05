"""
Coverage reader for VibesRails.

Reads pre-generated coverage.json (output of `coverage json`) without
running pytest. Pure JSON file reader for fast gate checks.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CoverageReport:
    """Parsed coverage report from coverage.json."""

    total_percent: float
    total_statements: int
    total_covered: int
    files: dict[str, float] = field(default_factory=dict)  # path -> percent

    def files_below(self, threshold: float) -> dict[str, float]:
        """Return files whose coverage is strictly below the given threshold."""
        return {path: pct for path, pct in self.files.items() if pct < threshold}


def _find_coverage_json(root: Path) -> Path | None:
    """Locate coverage.json under root or root/htmlcov/."""
    candidates = [
        root / "coverage.json",
        root / "htmlcov" / "coverage.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def read_coverage(root: Path) -> CoverageReport | None:
    """
    Read coverage.json from root (or root/htmlcov/) and return a CoverageReport.

    Returns None on missing file, invalid JSON, or parse error.
    """
    coverage_path = _find_coverage_json(root)
    if coverage_path is None:
        return None

    try:
        data = json.loads(coverage_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None

    try:
        totals = data["totals"]
        total_percent = float(totals["percent_covered"])
        total_statements = int(totals["num_statements"])
        total_covered = int(totals["covered_lines"])

        files: dict[str, float] = {}
        for path, file_data in data.get("files", {}).items():
            pct = file_data.get("summary", {}).get("percent_covered")
            if pct is not None:
                files[path] = float(pct)

        return CoverageReport(
            total_percent=total_percent,
            total_statements=total_statements,
            total_covered=total_covered,
            files=files,
        )
    except (KeyError, TypeError, ValueError):
        return None


def is_coverage_stale(root: Path) -> bool:
    """
    Return True if coverage.json is missing or older than the last git commit.

    - True  → file missing
    - True  → coverage.json mtime < last git commit timestamp
    - False → coverage.json is fresh (at or after last git commit)
    """
    coverage_path = _find_coverage_json(root)
    if coverage_path is None:
        return True

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0 or not result.stdout.strip():
            # Not a git repo or no commits — treat as fresh
            return False

        last_commit_ts = int(result.stdout.strip())
        coverage_mtime = coverage_path.stat().st_mtime
        return coverage_mtime < last_commit_ts
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return False
