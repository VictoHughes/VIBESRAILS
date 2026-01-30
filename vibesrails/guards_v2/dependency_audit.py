"""Dependency Audit Guard — Detects risky, abandoned, or typosquatted packages."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class V2GuardIssue:
    """An issue detected by a v2 guard."""

    guard: str
    severity: Literal["info", "warn", "block"]
    message: str
    file: str | None = None
    line: int | None = None


def _levenshtein(s1: str, s2: str) -> int:
    """Re-export from dependency_audit_checks."""
    from .dependency_audit_checks import _levenshtein as _impl
    return _impl(s1, s2)


def _normalize_pkg_name(name: str) -> str:
    """Re-export from dependency_audit_checks."""
    from .dependency_audit_checks import normalize_pkg_name
    return normalize_pkg_name(name)


class DependencyAuditGuard:
    """Scans project dependencies for security and quality issues.

    Checks for abandoned packages, typosquatting, known CVEs, and
    unpinned dependencies across requirements.txt, pyproject.toml,
    and setup.py files.
    """

    def __init__(self) -> None:
        self._pypi_cache: dict[str, dict | None] = {}

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan all dependency files in the project root."""
        self._pypi_cache.clear()
        issues: list[V2GuardIssue] = []

        req_file = project_root / "requirements.txt"
        if req_file.exists():
            issues.extend(self.scan_requirements_file(req_file))

        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            issues.extend(self._scan_pyproject(pyproject))

        setup_py = project_root / "setup.py"
        if setup_py.exists():
            issues.extend(self._scan_setup_py(setup_py))

        return issues

    def scan_requirements_file(
        self, filepath: Path
    ) -> list[V2GuardIssue]:
        """Scan a requirements.txt file for dependency issues."""
        from . import dependency_audit_checks as chk
        issues: list[V2GuardIssue] = []
        text = filepath.read_text(
            encoding="utf-8", errors="ignore"
        )
        for lineno, line in enumerate(
            text.splitlines(), start=1
        ):
            line = line.strip()
            if (
                not line
                or line.startswith("#")
                or line.startswith("-")
            ):
                continue
            pkg, version = self._parse_requirement(line)
            if pkg:
                issues.extend(
                    chk.check_package(
                        pkg, version, str(filepath),
                        lineno, self._pypi_cache,
                    )
                )
        return issues

    def _scan_pyproject(
        self, filepath: Path
    ) -> list[V2GuardIssue]:
        """Scan pyproject.toml for dependency issues."""
        from . import dependency_audit_checks as chk
        issues: list[V2GuardIssue] = []
        try:
            import tomllib
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                return issues
        try:
            data = tomllib.loads(
                filepath.read_text(
                    encoding="utf-8", errors="ignore"
                )
            )
        except Exception:
            return issues
        deps = data.get("project", {}).get(
            "dependencies", []
        )
        for i, dep in enumerate(deps):
            pkg, version = self._parse_requirement(dep)
            if pkg:
                issues.extend(
                    chk.check_package(
                        pkg, version, str(filepath),
                        i + 1, self._pypi_cache,
                    )
                )
        return issues

    def _scan_setup_py(
        self, filepath: Path
    ) -> list[V2GuardIssue]:
        """Scan setup.py install_requires."""
        from . import dependency_audit_checks as chk
        issues: list[V2GuardIssue] = []
        text = filepath.read_text(
            encoding="utf-8", errors="ignore"
        )
        match = re.search(
            r"install_requires\s*=\s*\[([^\]]*)\]",
            text, re.DOTALL,
        )
        if not match:
            return issues
        block = match.group(1)
        for raw in re.findall(
            r"""['"]([^'"]+)['"]""", block
        ):
            pkg, version = self._parse_requirement(raw)
            if pkg:
                issues.extend(
                    chk.check_package(
                        pkg, version, str(filepath),
                        None, self._pypi_cache,
                    )
                )
        return issues

    @staticmethod
    def _parse_requirement(
        line: str,
    ) -> tuple[str, str | None]:
        """Parse a requirement line into (name, version)."""
        line = line.strip()
        if not line:
            return ("", None)
        line = re.sub(r"\[.*?\]", "", line)
        m = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", line)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        m2 = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if m2:
            return (m2.group(1).strip(), None)
        return ("", None)

    def run_pip_audit(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run pip-audit if available."""
        from . import dependency_audit_checks as chk
        return chk.run_pip_audit(project_root)
