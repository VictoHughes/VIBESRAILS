"""Upgrade Advisor — analyzes dependencies and recommends upgrades."""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from ..guards_v2.dependency_audit import V2GuardIssue

_PYPI_TIMEOUT = 5

# Known packages with security-related releases
_SECURITY_PACKAGES = frozenset({
    "cryptography", "urllib3", "requests", "django", "flask",
    "jinja2", "pillow", "pyyaml", "certifi", "paramiko",
    "bcrypt", "jwt", "sqlalchemy", "psycopg2",
})


@dataclass
class _DepInfo:
    """Internal: parsed dependency with PyPI metadata."""

    name: str
    current: str | None
    latest: str | None
    priority: str  # "security", "major", "minor", "patch", "up-to-date"
    deprecated: bool
    source_file: str


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse version string into tuple of ints."""
    parts = re.split(r"[.\-_]", v)
    result: list[int] = []
    for p in parts:
        m = re.match(r"(\d+)", p)
        if m:
            result.append(int(m.group(1)))
        else:
            break
    return tuple(result) if result else (0,)


def _classify_update(
    current: str,
    latest: str,
    pkg_name: str,
) -> str:
    """Classify the update priority."""
    norm = re.sub(r"[-_.]+", "-", pkg_name).lower()
    if norm in _SECURITY_PACKAGES:
        cur = _parse_version(current)
        lat = _parse_version(latest)
        if cur != lat:
            return "security"

    cur = _parse_version(current)
    lat = _parse_version(latest)
    if cur == lat:
        return "up-to-date"
    if len(cur) >= 1 and len(lat) >= 1 and cur[0] != lat[0]:
        return "major"
    if len(cur) >= 2 and len(lat) >= 2 and cur[1] != lat[1]:
        return "minor"
    return "patch"


class UpgradeAdvisor:
    """Analyzes project dependencies and generates upgrade plans.

    Reads requirements.txt and pyproject.toml, queries PyPI for
    latest versions, and produces a prioritized upgrade report.
    """

    def __init__(self) -> None:
        self._cache: dict[str, dict | None] = {}

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan dependencies and return issues for outdated packages.

        Args:
            project_root: Path to the project root directory.

        Returns:
            List of V2GuardIssue for packages needing upgrades.
        """
        self._cache.clear()
        deps = self._collect_deps(project_root)
        issues: list[V2GuardIssue] = []
        for dep in deps:
            if dep.priority == "up-to-date":
                continue
            sev = "block" if dep.priority == "security" else "warn"
            if dep.deprecated:
                sev = "block"
            msg = (
                f"Upgrade {dep.name}: "
                f"{dep.current or 'unpinned'} -> {dep.latest or '?'} "
                f"({dep.priority})"
            )
            if dep.deprecated:
                msg += " [DEPRECATED]"
            issues.append(V2GuardIssue(
                guard="UpgradeAdvisor",
                severity=sev,
                message=msg,
                file=dep.source_file,
            ))
        return issues

    def generate_report(self, project_root: Path) -> str:
        """Generate a markdown upgrade report.

        Args:
            project_root: Path to the project root directory.

        Returns:
            Markdown-formatted report string.
        """
        deps = self._collect_deps(project_root)
        if not deps:
            return "# Upgrade Report\n\nNo dependencies found.\n"

        priority_order = {
            "security": 0, "major": 1, "minor": 2,
            "patch": 3, "up-to-date": 4,
        }
        deps.sort(key=lambda d: priority_order.get(d.priority, 5))

        lines = [
            "# Upgrade Report\n",
            "| Package | Current | Latest | Priority | Notes |",
            "|---------|---------|--------|----------|-------|",
        ]
        for dep in deps:
            notes = "DEPRECATED" if dep.deprecated else ""
            lines.append(
                f"| {dep.name} "
                f"| {dep.current or 'unpinned'} "
                f"| {dep.latest or '?'} "
                f"| {dep.priority} "
                f"| {notes} |"
            )
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_deps(self, project_root: Path) -> list[_DepInfo]:
        """Collect all dependencies with PyPI metadata."""
        raw: list[tuple[str, str | None, str]] = []

        req = project_root / "requirements.txt"
        if req.exists():
            raw.extend(self._parse_requirements(req))

        pyp = project_root / "pyproject.toml"
        if pyp.exists():
            raw.extend(self._parse_pyproject(pyp))

        deps: list[_DepInfo] = []
        seen: set[str] = set()
        for name, version, src in raw:
            norm = re.sub(r"[-_.]+", "-", name).lower()
            if norm in seen:
                continue
            seen.add(norm)
            pypi = self._fetch_pypi(norm)
            latest = None
            deprecated = False
            if pypi:
                latest = pypi.get("info", {}).get("version")
                desc = pypi.get("info", {}).get(
                    "summary", ""
                ) or ""
                classifiers = pypi.get("info", {}).get(
                    "classifiers", []
                ) or []
                deprecated = (
                    "deprecated" in desc.lower()
                    or any(
                        "inactive" in c.lower()
                        or "deprecated" in c.lower()
                        for c in classifiers
                    )
                )

            if version and latest:
                priority = _classify_update(version, latest, name)
            elif version is None and latest:
                priority = "major"
            else:
                priority = "up-to-date"

            deps.append(_DepInfo(
                name=name,
                current=version,
                latest=latest,
                priority=priority,
                deprecated=deprecated,
                source_file=src,
            ))
        return deps

    @staticmethod
    def _parse_requirements(
        filepath: Path,
    ) -> list[tuple[str, str | None, str]]:
        """Parse requirements.txt returning (name, version, file)."""
        results: list[tuple[str, str | None, str]] = []
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            line = re.sub(r"\[.*?\]", "", line)
            m = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", line)
            if m:
                results.append(
                    (m.group(1).strip(), m.group(2).strip(),
                     str(filepath))
                )
            else:
                m2 = re.match(r"^([A-Za-z0-9_.-]+)", line)
                if m2:
                    results.append(
                        (m2.group(1).strip(), None,
                         str(filepath))
                    )
        return results

    @staticmethod
    def _parse_pyproject(
        filepath: Path,
    ) -> list[tuple[str, str | None, str]]:
        """Parse pyproject.toml dependencies."""
        try:
            import tomllib
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                return []

        try:
            data = tomllib.loads(
                filepath.read_text(encoding="utf-8", errors="ignore")
            )
        except Exception:
            return []

        results: list[tuple[str, str | None, str]] = []
        deps = data.get("project", {}).get("dependencies", [])
        for dep in deps:
            dep = re.sub(r"\[.*?\]", "", dep.strip())
            m = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", dep)
            if m:
                results.append(
                    (m.group(1).strip(), m.group(2).strip(),
                     str(filepath))
                )
            else:
                m2 = re.match(r"^([A-Za-z0-9_.-]+)", dep)
                if m2:
                    results.append(
                        (m2.group(1).strip(), None,
                         str(filepath))
                    )
        return results

    def _fetch_pypi(self, normalized_name: str) -> dict | None:
        """Fetch package info from PyPI JSON API with caching."""
        if normalized_name in self._cache:
            return self._cache[normalized_name]
        url = f"https://pypi.org/pypi/{normalized_name}/json"
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(
                req, timeout=_PYPI_TIMEOUT,
            ) as resp:
                data = json.loads(resp.read())
                self._cache[normalized_name] = data
                return data
        except Exception:
            self._cache[normalized_name] = None
            return None
