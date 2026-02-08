"""mutmut integration for MutationGuard.

Handles subprocess calls to mutmut and output parsing.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "MutationGuard"
WARN_THRESHOLD = 0.60
BLOCK_THRESHOLD = 0.30


def scan_with_mutmut(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Run mutation testing using mutmut if available.

    Args:
        project_root: Root path of the project.

    Returns:
        List of guard issues found.
    """
    if not shutil.which("mutmut"):
        return [V2GuardIssue(
            guard=GUARD_NAME,
            severity="info",
            message="mutmut not installed — skipping",
        )]

    src_dir = "src"
    if not (project_root / src_dir).exists():
        src_dir = project_root.name

    tests_dir = "tests"
    if not (project_root / tests_dir).exists():
        tests_dir = "test"

    try:
        subprocess.run(
            [
                "mutmut", "run",
                f"--paths-to-mutate={src_dir}",
                f"--tests-dir={tests_dir}",
            ],
            capture_output=True,
            timeout=600,
            cwd=str(project_root),
        )
    except (subprocess.TimeoutExpired, OSError):
        return [V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message="mutmut run timed out or failed",
        )]

    return _parse_mutmut_results(project_root)


def _parse_mutmut_results(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Parse mutmut results output."""
    issues: list[V2GuardIssue] = []
    try:
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root),
        )
    except (subprocess.TimeoutExpired, OSError):
        return [V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message="Failed to parse mutmut results",
        )]

    output = result.stdout
    survived = output.count("Survived")
    killed = output.count("Killed")
    total = survived + killed

    if total == 0:
        return issues

    score = killed / total
    if score < BLOCK_THRESHOLD:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="block",
            message=(
                f"mutmut: mutation score {score:.0%} "
                f"({killed}/{total}) — tests unreliable"
            ),
        ))
    elif score < WARN_THRESHOLD:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message=(
                f"mutmut: mutation score {score:.0%} "
                f"({killed}/{total}) — tests weak"
            ),
        ))
    return issues
