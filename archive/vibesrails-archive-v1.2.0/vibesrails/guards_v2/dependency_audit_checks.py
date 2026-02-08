"""Dependency Audit Checks — Typosquat, abandoned, and CVE detection."""

import json
import logging
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

# Top 100 popular PyPI packages for typosquatting detection
POPULAR_PACKAGES: list[str] = [
    "requests", "flask", "django", "numpy", "pandas", "scipy",
    "matplotlib", "pillow", "sqlalchemy", "fastapi", "pydantic",
    "httpx", "boto3", "celery", "redis", "psycopg2", "cryptography",
    "bcrypt", "jwt", "jinja2", "click", "pytest", "setuptools",
    "wheel", "pip", "six", "urllib3", "certifi", "idna", "charset-normalizer",
    "packaging", "typing-extensions", "tomli", "colorama", "pyyaml",
    "attrs", "pluggy", "platformdirs", "filelock", "virtualenv",
    "pytz", "python-dateutil", "beautifulsoup4", "lxml", "scrapy",
    "selenium", "paramiko", "fabric", "ansible", "salt",
    "tornado", "gunicorn", "uvicorn", "starlette", "aiohttp",
    "twisted", "gevent", "greenlet", "eventlet", "sanic",
    "black", "isort", "flake8", "mypy", "pylint",
    "ruff", "bandit", "coverage", "tox", "nox",
    "sphinx", "mkdocs", "docutils", "pygments", "rich",
    "typer", "argparse", "fire", "invoke", "plumbum",
    "tensorflow", "torch", "keras", "scikit-learn", "xgboost",
    "lightgbm", "catboost", "transformers", "spacy", "nltk",
    "opencv-python", "imageio", "scikit-image", "mahotas", "albumentations",
    "sqlmodel", "peewee", "tortoise-orm", "mongoengine", "pymongo",
    "psutil", "watchdog", "schedule", "apscheduler", "dramatiq",
    "arrow", "pendulum", "dateparser", "babel", "chardet",
]

# Known-bad package versions (fallback when pip-audit unavailable)
KNOWN_BAD_VERSIONS: dict[str, list[str]] = {
    "urllib3": ["1.24", "1.24.1"],
    "requests": ["2.19.0"],
    "django": ["3.0", "3.0.1", "3.0.2", "2.2", "2.2.1"],
    "flask": ["0.12", "0.12.1"],
    "jinja2": ["2.10", "2.10.1"],
    "cryptography": ["2.2", "2.3"],
    "pillow": ["6.0.0", "6.1.0", "6.2.0"],
    "pyyaml": ["5.1", "5.1.1", "5.1.2"],
}

_ABANDONED_YEARS = 2
_PYPI_TIMEOUT = 5
_LEVENSHTEIN_THRESHOLD = 2


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row
    return prev_row[-1]


def normalize_pkg_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def check_typosquatting(normalized_name: str) -> str | None:
    """Return the popular package name if typosquatting is detected."""
    for popular in POPULAR_PACKAGES:
        pop_norm = normalize_pkg_name(popular)
        if normalized_name == pop_norm:
            # exact match with popular package, not a typo
            return None
        dist = _levenshtein(normalized_name, pop_norm)
        if dist <= _LEVENSHTEIN_THRESHOLD and dist > 0:
            return popular
    return None


def _find_latest_release_date(releases: dict) -> datetime | None:
    """Find the most recent upload date across all releases."""
    latest: datetime | None = None
    for rel_files in releases.values():
        for f in rel_files:
            upload = f.get("upload_time_iso_8601") or f.get("upload_time")
            if not upload:
                continue
            dt = datetime.fromisoformat(upload.replace("Z", "+00:00"))
            if latest is None or dt > latest:
                latest = dt
    return latest


def check_abandoned(
    pkg: str,
    norm: str,
    filepath: str,
    lineno: int | None,
    pypi_cache: dict[str, dict | None],
) -> V2GuardIssue | None:
    """Check if package has had no release in >2 years via PyPI API."""
    pypi_data = fetch_pypi(norm, pypi_cache)
    if pypi_data is None:
        return None
    try:
        info = pypi_data.get("info", {})
        latest_date = _find_latest_release_date(pypi_data.get("releases", {}))
        if latest_date is None:
            return None
        age = datetime.now(timezone.utc) - latest_date
        if age.days > _ABANDONED_YEARS * 365:
            years = round(age.days / 365, 1)
            return V2GuardIssue(
                guard="DependencyAuditGuard", severity="warn",
                message=f"Possibly abandoned: {pkg} — last release {years} years ago ({info.get('version', '?')}).",
                file=filepath, line=lineno,
            )
    except Exception:
        pass  # PyPI date parsing failed, skip abandoned check
    return None


def fetch_pypi(
    normalized_name: str,
    cache: dict[str, dict | None],
) -> dict | None:
    """Fetch package metadata from PyPI JSON API with caching."""
    if normalized_name in cache:
        return cache[normalized_name]
    url = f"https://pypi.org/pypi/{normalized_name}/json"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=_PYPI_TIMEOUT) as resp:
            data = json.loads(resp.read())
            cache[normalized_name] = data
            return data
    except Exception:
        cache[normalized_name] = None
        return None


def _make_issue(severity: str, message: str, filepath: str, lineno: int | None) -> V2GuardIssue:
    """Create a DependencyAuditGuard issue."""
    return V2GuardIssue(guard="DependencyAuditGuard", severity=severity, message=message, file=filepath, line=lineno)


def check_package(
    pkg: str, version: str | None, filepath: str,
    lineno: int | None, pypi_cache: dict[str, dict | None],
) -> list[V2GuardIssue]:
    """Run all checks on a single package."""
    issues: list[V2GuardIssue] = []
    norm = normalize_pkg_name(pkg)

    if version is None:
        issues.append(_make_issue("warn", f"Unpinned dependency: {pkg}. Pin with == for reproducibility.", filepath, lineno))

    typo = check_typosquatting(norm)
    if typo:
        issues.append(_make_issue("block", f"Possible typosquatting: '{pkg}' is very similar to popular package '{typo}'. Verify this is intentional.", filepath, lineno))

    if version and version in KNOWN_BAD_VERSIONS.get(norm, []):
        issues.append(_make_issue("block", f"Known vulnerable version: {pkg}=={version}. Upgrade to a patched release.", filepath, lineno))

    abandoned_issue = check_abandoned(pkg, norm, filepath, lineno, pypi_cache)
    if abandoned_issue:
        issues.append(abandoned_issue)

    return issues


def run_pip_audit(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Run pip-audit if available."""
    issues: list[V2GuardIssue] = []
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        return issues
    try:
        result = subprocess.run(
            ["pip-audit", "-r", str(req_file), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root),
        )
        if result.returncode != 0 and not result.stdout:
            return issues
        data = json.loads(result.stdout)
        vulns = data.get("dependencies", [])
        for dep in vulns:
            for vuln in dep.get("vulns", []):
                issues.append(V2GuardIssue(
                    guard="DependencyAuditGuard",
                    severity="block",
                    message=(
                        f"CVE {vuln.get('id', '?')}: {dep['name']} "
                        f"{dep.get('version', '?')} — "
                        f"{vuln.get('description', '')[:120]}"
                    ),
                    file=str(req_file),
                ))
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ):
        pass  # pip-audit unavailable or returned invalid data
    return issues
