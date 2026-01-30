"""Pre-Deploy Guard — Comprehensive pre-deployment checklist."""

import logging
from pathlib import Path

from . import pre_deploy_checks as checks
from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)


def _read_init_version(project_root: Path) -> str | None:
    """Re-export from pre_deploy_checks."""
    return checks.read_init_version(project_root)


def _read_pyproject_version(project_root: Path) -> str | None:
    """Re-export from pre_deploy_checks."""
    return checks.read_pyproject_version(project_root)


class PreDeployGuard:
    """Runs a comprehensive pre-deployment checklist.

    Checks: pytest pass, coverage threshold, blocking TODOs,
    print() debug, .env.example, dependency audit, version
    consistency, and CHANGELOG.md presence.
    """

    def __init__(
        self, coverage_threshold: int = 80
    ) -> None:
        self.coverage_threshold = coverage_threshold

    def run_all(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run every pre-deploy check."""
        issues: list[V2GuardIssue] = []
        issues.extend(
            checks.check_pytest(
                project_root, self.coverage_threshold
            )
        )
        issues.extend(
            checks.check_blocking_todos(project_root)
        )
        issues.extend(
            checks.check_print_debug(project_root)
        )
        issues.extend(
            checks.check_env_example(project_root)
        )
        issues.extend(
            checks.check_dependency_audit(project_root)
        )
        issues.extend(
            checks.check_version_consistency(project_root)
        )
        issues.extend(
            checks.check_changelog(project_root)
        )
        return issues

    def generate_report(
        self, issues: list[V2GuardIssue]
    ) -> str:
        """Generate a markdown report from issues."""
        if not issues:
            return (
                "# Pre-Deploy Checklist\n\n"
                "All checks passed. Ready to deploy."
            )

        blocks = [
            i for i in issues if i.severity == "block"
        ]
        warns = [
            i for i in issues if i.severity == "warn"
        ]
        infos = [
            i for i in issues if i.severity == "info"
        ]

        lines = ["# Pre-Deploy Checklist\n"]
        lines.append(
            f"**{len(issues)} issue(s) found** "
            f"({len(blocks)} blocking, "
            f"{len(warns)} warnings, "
            f"{len(infos)} info)\n"
        )

        if blocks:
            lines.append("## Blocking Issues\n")
            for issue in blocks:
                loc = checks.format_location(issue)
                lines.append(f"- {issue.message}{loc}")
            lines.append("")

        if warns:
            lines.append("## Warnings\n")
            for issue in warns:
                loc = checks.format_location(issue)
                lines.append(f"- {issue.message}{loc}")
            lines.append("")

        if infos:
            lines.append("## Info\n")
            for issue in infos:
                loc = checks.format_location(issue)
                lines.append(f"- {issue.message}{loc}")
            lines.append("")

        return "\n".join(lines)

    def _parse_coverage(self, output: str) -> int | None:
        """Extract total coverage % from pytest-cov output."""
        return checks.parse_coverage(output)

    def _check_pytest(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        return checks.check_pytest(
            project_root, self.coverage_threshold
        )

    def _check_blocking_todos(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        return checks.check_blocking_todos(project_root)

    def _check_version_consistency(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        return checks.check_version_consistency(project_root)

    def _check_changelog(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        return checks.check_changelog(project_root)
