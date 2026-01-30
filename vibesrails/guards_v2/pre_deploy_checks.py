"""Pre-Deploy Checks — Individual check implementations."""

import logging
import re
import subprocess
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "pre-deploy"

_BLOCKING_TODO_RE = re.compile(
    r"#\s*(?:TODO|FIXME)\s*.*?\b(?:BLOCK|CRITICAL)\b",
    re.IGNORECASE,
)

_COV_PERCENT_RE = re.compile(r"TOTAL\s+\d+\s+\d+\s+(\d+)%")


def _run_pytest(project_root: Path) -> subprocess.CompletedProcess | V2GuardIssue:
    """Run pytest and return result or a blocking issue on failure."""
    try:
        return subprocess.run(
            ["python", "-m", "pytest", "tests/",
             f"--cov={guess_package(project_root)}",
             "--cov-report=term", "--timeout=60", "-q"],
            capture_output=True, text=True, timeout=120,
            cwd=str(project_root),
        )
    except FileNotFoundError:
        return V2GuardIssue(guard=GUARD_NAME, severity="block", message="pytest not found — cannot verify tests")
    except subprocess.TimeoutExpired:
        return V2GuardIssue(guard=GUARD_NAME, severity="block", message="pytest timed out after 120s")


def check_pytest(
    project_root: Path, coverage_threshold: int,
) -> list[V2GuardIssue]:
    """Run pytest and check exit code + coverage."""
    result = _run_pytest(project_root)
    if isinstance(result, V2GuardIssue):
        return [result]

    issues: list[V2GuardIssue] = []
    if result.returncode != 0:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME, severity="block",
            message=f"pytest failed with exit code {result.returncode}",
        ))

    cov = parse_coverage(result.stdout + result.stderr)
    if cov is not None and cov < coverage_threshold:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME, severity="block",
            message=f"Coverage {cov}% is below threshold {coverage_threshold}%",
        ))
    return issues


def parse_coverage(output: str) -> int | None:
    """Extract total coverage % from pytest-cov output."""
    match = _COV_PERCENT_RE.search(output)
    if match:
        return int(match.group(1))
    return None


def check_blocking_todos(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Find TODO/FIXME with BLOCK or CRITICAL."""
    issues: list[V2GuardIssue] = []
    for py_file in sorted(project_root.rglob("*.py")):
        if is_excluded(py_file):
            continue
        try:
            text = py_file.read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue
        for lineno, line in enumerate(
            text.splitlines(), 1
        ):
            if _BLOCKING_TODO_RE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        f"Blocking TODO/FIXME: "
                        f"{line.strip()[:80]}"
                    ),
                    file=str(py_file),
                    line=lineno,
                ))
    return issues


def check_print_debug(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Delegate print() detection to ObservabilityGuard."""
    try:
        from .observability import ObservabilityGuard
        guard = ObservabilityGuard()
        return guard.scan(project_root)
    except Exception:
        return []


def check_env_example(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Delegate .env.example check to EnvSafetyGuard."""
    try:
        from .env_safety import EnvSafetyGuard
        guard = EnvSafetyGuard()
        return guard.scan(project_root)
    except Exception:
        return []


def check_dependency_audit(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Delegate dependency audit to DependencyAuditGuard."""
    try:
        from .dependency_audit import DependencyAuditGuard
        guard = DependencyAuditGuard()
        return guard.scan(project_root)
    except Exception:
        return []


def check_version_consistency(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Check __init__.py version matches pyproject.toml."""
    issues: list[V2GuardIssue] = []
    init_version = read_init_version(project_root)
    pyproject_version = read_pyproject_version(project_root)

    if init_version is None:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message="No __version__ found in __init__.py",
        ))
        return issues

    if pyproject_version is None:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message="No version found in pyproject.toml",
        ))
        return issues

    if init_version != pyproject_version:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="block",
            message=(
                f"Version mismatch: __init__.py="
                f"{init_version} vs "
                f"pyproject.toml={pyproject_version}"
            ),
        ))

    return issues


def check_changelog(
    project_root: Path,
) -> list[V2GuardIssue]:
    """Check CHANGELOG.md exists and has current version."""
    issues: list[V2GuardIssue] = []
    changelog = project_root / "CHANGELOG.md"

    if not changelog.exists():
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message="CHANGELOG.md missing",
        ))
        return issues

    init_version = read_init_version(project_root)
    if init_version is None:
        return issues

    try:
        text = changelog.read_text(
            encoding="utf-8", errors="ignore"
        )
    except OSError:
        return issues

    if init_version not in text:
        issues.append(V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message=(
                f"CHANGELOG.md has no entry for "
                f"version {init_version}"
            ),
        ))

    return issues


# -- Helpers --

def format_location(issue: V2GuardIssue) -> str:
    """Format file:line suffix for report."""
    if issue.file and issue.line:
        return f" (`{issue.file}:{issue.line}`)"
    if issue.file:
        return f" (`{issue.file}`)"
    return ""


def is_excluded(path: Path) -> bool:
    """Skip venvs, hidden dirs, __pycache__."""
    _skip = {"venv", ".venv", "node_modules", "site-packages", "__pycache__"}
    return any(p.startswith(".") or p in _skip for p in path.parts)


def guess_package(project_root: Path) -> str:
    """Guess the main package name from project root."""
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text()
            m = re.search(
                r'name\s*=\s*["\']([^"\']+)["\']', text
            )
            if m:
                return m.group(1).replace("-", "_")
        except OSError:
            pass  # pyproject.toml unreadable, fall through to directory scan
    for child in sorted(project_root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            return child.name
    return "src"


def read_init_version(project_root: Path) -> str | None:
    """Read __version__ from the package __init__.py."""
    pkg = guess_package(project_root)
    init_file = project_root / pkg / "__init__.py"
    if not init_file.exists():
        return None
    try:
        text = init_file.read_text(
            encoding="utf-8", errors="ignore"
        )
    except OSError:
        return None
    m = re.search(
        r'__version__\s*=\s*["\']([^"\']+)["\']', text
    )
    return m.group(1) if m else None


def read_pyproject_version(project_root: Path) -> str | None:
    """Read version from pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(
            encoding="utf-8", errors="ignore"
        )
    except OSError:
        return None
    m = re.search(
        r'version\s*=\s*["\']([^"\']+)["\']', text
    )
    return m.group(1) if m else None
