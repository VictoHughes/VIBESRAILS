"""Registry helpers for hallucination checking — extracted from hallucination_deep.py."""

from __future__ import annotations

import sqlite3
from difflib import get_close_matches
from pathlib import Path


def check_bloom_filter(package_name: str, ecosystem: str) -> bool | None:
    """Check bloom filter file. Returns None if file doesn't exist."""
    bloom_dir = Path.home() / ".vibesrails" / "packages"
    bloom_file = bloom_dir / f"{ecosystem}.bloom"
    if not bloom_file.is_file():
        return None
    try:
        data = bloom_file.read_text()
        packages = {p.strip().lower() for p in data.splitlines() if p.strip()}
        return package_name.lower() in packages
    except OSError:
        return None


def find_similar(package_name: str, ecosystem: str, db_path: str) -> list[str]:
    """Find similar package names for slopsquatting detection."""
    known = get_known_packages(ecosystem, db_path)
    if not known:
        return []
    matches = get_close_matches(
        package_name.lower(), known, n=3, cutoff=0.75
    )
    return [m for m in matches if m != package_name.lower()]


def check_in_project_deps(package_name: str, project_path: Path) -> bool:
    """Check if package is listed in requirements.txt or pyproject.toml."""
    pkg_lower = package_name.lower().replace("-", "_")

    # requirements.txt
    req_file = project_path / "requirements.txt"
    if req_file.is_file():
        for line in req_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            dep = line.split("==")[0].split(">=")[0].split("<=")[0]
            dep = dep.split("[")[0].split(">")[0].split("<")[0].split("~=")[0]
            dep = dep.split("!=")[0].strip()
            if dep.lower().replace("-", "_") == pkg_lower:
                return True

    # pyproject.toml (simple parse — look for dependencies list)
    pyproject = project_path / "pyproject.toml"
    if pyproject.is_file():
        content = pyproject.read_text()
        for line in content.splitlines():
            stripped = line.strip().strip('"').strip("'").strip(",")
            dep = stripped.split("==")[0].split(">=")[0].split("<=")[0]
            dep = dep.split("[")[0].split(">")[0].split("<")[0].split("~=")[0]
            dep = dep.split("!=")[0].strip().strip('"').strip("'")
            if dep.lower().replace("-", "_") == pkg_lower:
                return True

    return False


def get_known_packages(ecosystem: str, db_path: str) -> list[str]:
    """Get known packages from bloom filter or cache."""
    # Try bloom file
    bloom_dir = Path.home() / ".vibesrails" / "packages"
    bloom_file = bloom_dir / f"{ecosystem}.bloom"
    if bloom_file.is_file():
        try:
            data = bloom_file.read_text()
            return [p.strip().lower() for p in data.splitlines() if p.strip()]
        except OSError:
            pass

    # Fallback: packages from cache
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        cursor = conn.execute(
            "SELECT package_name FROM package_cache "
            "WHERE ecosystem = ? AND exists_flag = 1 LIMIT 10000",
            (ecosystem,),
        )
        return [row[0].lower() for row in cursor.fetchall()]
    finally:
        conn.close()
