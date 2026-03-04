"""Preflight check — verify project readiness before starting a coding session."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .cli_setup import find_config
from .guards_v2._git_helpers import run_git
from .scanner import load_config, validate_config
from .scanner_types import BLUE, GREEN, NC, RED, YELLOW

logger = logging.getLogger(__name__)

MAX_AHEAD_COMMITS = 10


@dataclass
class CheckResult:
    """Result of a single preflight check."""

    name: str
    status: Literal["ok", "warn", "block", "info"]
    message: str


def check_branch(root: Path) -> CheckResult:
    """Display current git branch."""
    ok, branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    if not ok:
        return CheckResult("Branch", "warn", "Not a git repository")
    return CheckResult("Branch", "info", branch)


def check_uncommitted(root: Path) -> CheckResult:
    """Check for uncommitted changes."""
    ok, output = run_git(["status", "--porcelain"], cwd=root)
    if not ok:
        return CheckResult("Uncommitted", "warn", "Could not check git status")
    dirty = [line for line in output.splitlines() if line.strip()]
    if dirty:
        count = len(dirty)
        return CheckResult(
            "Uncommitted",
            "warn",
            f"{count} uncommitted file{'s' if count != 1 else ''}"
            " — commit or stash before coding",
        )
    return CheckResult("Uncommitted", "ok", "Working tree clean")


def check_ahead_behind(root: Path) -> CheckResult:
    """Check commits ahead/behind main."""
    ok, output = run_git(
        ["rev-list", "--left-right", "--count", "main...HEAD"], cwd=root
    )
    if not ok:
        return CheckResult("Ahead/Behind", "info", "Could not compare with main")
    parts = output.split()
    if len(parts) != 2:
        return CheckResult("Ahead/Behind", "info", "Could not parse rev-list output")
    behind, ahead = int(parts[0]), int(parts[1])
    if ahead > MAX_AHEAD_COMMITS:
        return CheckResult(
            "Ahead/Behind",
            "warn",
            f"{ahead} commits ahead of main — consider merging",
        )
    msg = f"{ahead} ahead, {behind} behind main"
    return CheckResult("Ahead/Behind", "ok", msg)


def check_test_baseline(root: Path) -> CheckResult:
    """Run pytest to verify tests pass."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--timeout=60", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return CheckResult("Tests", "ok", "Test suite passing")
        return CheckResult("Tests", "block", "Tests failing — fix before starting new work")
    except subprocess.TimeoutExpired:
        return CheckResult("Tests", "block", "Tests timed out (>5min)")
    except FileNotFoundError:
        return CheckResult("Tests", "warn", "pytest not found")


def check_config_valid() -> CheckResult:
    """Validate vibesrails.yaml configuration."""
    config_path = find_config()
    if not config_path or not config_path.exists():
        return CheckResult("Config", "warn", "No vibesrails.yaml found — run: vibesrails --init")
    try:
        config = load_config(config_path)
    except ValueError as e:
        return CheckResult("Config", "block", f"Invalid config: {e}")
    if validate_config(config):
        return CheckResult("Config", "ok", f"Config valid ({config_path.name})")
    return CheckResult("Config", "block", f"Config validation failed ({config_path.name})")


def check_hook_installed(root: Path) -> CheckResult:
    """Check if pre-commit hook includes vibesrails."""
    hook_path = root / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        return CheckResult("Pre-commit hook", "warn", "No pre-commit hook — run: vibesrails --hook")
    try:
        content = hook_path.read_text()
    except OSError:
        return CheckResult("Pre-commit hook", "warn", "Could not read pre-commit hook")
    if "vibesrails" in content:
        return CheckResult("Pre-commit hook", "ok", "Pre-commit hook installed")
    return CheckResult("Pre-commit hook", "warn", "Pre-commit hook exists but missing vibesrails")


def check_decisions_md(root: Path) -> CheckResult:
    """Check if decisions.md exists."""
    candidates = [
        root / "docs" / "decisions.md",
        root / "decisions.md",
        root / ".vibesrails" / "decisions.md",
    ]
    for path in candidates:
        if path.exists():
            return CheckResult("decisions.md", "ok", f"Found {path.relative_to(root)}")
    return CheckResult("decisions.md", "warn", "No decisions.md found")


def check_assertions(root: Path) -> CheckResult:
    """Run assertion checks if configured."""
    config_path = find_config()
    if not config_path or not config_path.exists():
        return CheckResult("Assertions", "info", "No config — skipped")
    try:
        config = load_config(config_path)
    except ValueError:
        return CheckResult("Assertions", "info", "Config error — skipped")
    assertions_config = config.get("assertions", {})
    if not assertions_config:
        return CheckResult("Assertions", "info", "No assertions configured — skipped")

    from .assertions import run_assertions

    results = run_assertions(root, assertions_config)
    failures = sum(1 for r in results if r.status == "fail")
    passes = sum(1 for r in results if r.status == "ok")
    if failures:
        return CheckResult(
            "Assertions",
            "warn",
            f"{failures} assertion(s) failed, {passes} passed"
            " — run: vibesrails --check-assertions",
        )
    return CheckResult("Assertions", "ok", f"All {passes} assertion(s) passed")


def run_preflight(root: Path) -> list[CheckResult]:
    """Run all preflight checks and return results."""
    return [
        check_branch(root),
        check_uncommitted(root),
        check_ahead_behind(root),
        check_test_baseline(root),
        check_config_valid(),
        check_hook_installed(root),
        check_decisions_md(root),
        check_assertions(root),
    ]


_STATUS_ICONS = {
    "ok": f"{GREEN}✅",
    "warn": f"{YELLOW}⚠️ ",
    "block": f"{RED}❌",
    "info": f"{BLUE}ℹ️ ",
}


def format_report(results: list[CheckResult]) -> str:
    """Format preflight results as a colored terminal report."""
    lines = [
        f"{BLUE}╔══════════════════════════════════════════════╗{NC}",
        f"{BLUE}║     ✈️  VIBESRAILS PREFLIGHT CHECK           ║{NC}",
        f"{BLUE}╚══════════════════════════════════════════════╝{NC}",
        "",
    ]
    for r in results:
        icon = _STATUS_ICONS.get(r.status, "")
        lines.append(f"{icon} {r.name}: {r.message}{NC}")
    blockers = sum(1 for r in results if r.status == "block")
    warnings = sum(1 for r in results if r.status == "warn")
    lines.append("")
    lines.append("──────────────────────────────────────────────")
    if blockers:
        lines.append(f"{RED}Result: {blockers} blocker{'s' if blockers != 1 else ''}, {warnings} warning{'s' if warnings != 1 else ''}{NC}")
    elif warnings:
        lines.append(f"{YELLOW}Result: {warnings} warning{'s' if warnings != 1 else ''}{NC}")
    else:
        lines.append(f"{GREEN}Result: All clear — ready to code!{NC}")
    return "\n".join(lines)


def exit_code(results: list[CheckResult]) -> int:
    """Determine exit code: 0=clear, 1=warnings, 2=blockers."""
    if any(r.status == "block" for r in results):
        return 2
    if any(r.status == "warn" for r in results):
        return 1
    return 0
