"""Preflight check — verify project readiness before starting a coding session."""

import logging
import re
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
TEST_COUNT_DRIFT_PERCENT = 5


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


def _read_pyproject_version(root: Path) -> str | None:
    """Read version from pyproject.toml."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        content = pyproject.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        return match.group(1) if match else None
    except OSError:
        return None


def check_version_consistency(root: Path) -> CheckResult:
    """Check version string is consistent across key files."""
    version = _read_pyproject_version(root)
    if not version:
        return CheckResult("Version sync", "info", "No pyproject.toml — skipped")
    stale_files = []
    for name in ("README.md", "CHANGELOG.md"):
        path = root / name
        if not path.exists():
            continue
        try:
            if version not in path.read_text():
                stale_files.append(name)
        except OSError:
            continue
    if stale_files:
        return CheckResult(
            "Version sync",
            "warn",
            f"Version {version} missing from: {', '.join(stale_files)}",
        )
    return CheckResult("Version sync", "ok", f"Version {version} consistent")


def check_test_count_freshness(root: Path) -> CheckResult:
    """Compare declared test_count with actual pytest collection."""
    config_path = find_config()
    if not config_path or not config_path.exists():
        return CheckResult("Test count", "info", "No config — skipped")
    try:
        config = load_config(config_path)
    except ValueError:
        return CheckResult("Test count", "info", "Config error — skipped")
    declared = (config.get("assertions", {}).get("baselines", {}) or {}).get("test_count")
    if not declared:
        return CheckResult("Test count", "info", "No test_count baseline — skipped")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined = result.stdout + result.stderr
        match = re.search(r"(\d+)\s+tests?\s+collected", combined)
        if not match:
            return CheckResult("Test count", "info", "Could not parse pytest output")
        actual = int(match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return CheckResult("Test count", "info", "Could not collect tests")
    drift = abs(actual - declared) / max(declared, 1) * 100
    if drift > TEST_COUNT_DRIFT_PERCENT:
        return CheckResult(
            "Test count",
            "warn",
            f"Declared {declared}, actual {actual} ({drift:.0f}% drift)"
            " — update vibesrails.yaml assertions.baselines.test_count",
        )
    return CheckResult("Test count", "ok", f"Declared {declared}, actual {actual}")


def check_claude_md_freshness(root: Path) -> CheckResult:
    """Check if CLAUDE.md is in sync with code."""
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return CheckResult("CLAUDE.md sync", "info", "No CLAUDE.md — skipped")
    try:
        from .sync_claude import sync_claude

        existing = claude_md.read_text()
        regenerated = sync_claude(root, dry_run=True)
        if not regenerated:
            return CheckResult("CLAUDE.md sync", "info", "Could not regenerate — skipped")
        if existing == regenerated:
            return CheckResult("CLAUDE.md sync", "ok", "CLAUDE.md is up to date")
        return CheckResult(
            "CLAUDE.md sync",
            "warn",
            "CLAUDE.md is stale — run: vibesrails --sync-claude",
        )
    except (ImportError, OSError):
        return CheckResult("CLAUDE.md sync", "info", "Could not check — skipped")


def check_changelog_current(root: Path) -> CheckResult:
    """Check that CHANGELOG.md has an entry for current version."""
    version = _read_pyproject_version(root)
    if not version:
        return CheckResult("Changelog", "info", "No pyproject.toml — skipped")
    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        return CheckResult("Changelog", "warn", "No CHANGELOG.md found")
    try:
        content = changelog.read_text()
    except OSError:
        return CheckResult("Changelog", "info", "Could not read CHANGELOG.md")
    if f"[{version}]" in content:
        return CheckResult("Changelog", "ok", f"CHANGELOG.md has [{version}] entry")
    return CheckResult(
        "Changelog",
        "warn",
        f"CHANGELOG.md missing [{version}] entry",
    )


def check_session_mode(root: Path) -> list[CheckResult]:
    """Detect session mode and show threshold adjustments."""
    from .context import ContextAdapter, ContextDetector, ContextScorer, SessionMode

    results: list[CheckResult] = []
    detector = ContextDetector(root)

    # Check for manual override
    forced = detector.read_forced_mode()
    if forced:
        mode = SessionMode(forced)
        results.append(
            CheckResult("Session mode", "info", f"{forced.upper()} (forced via --mode)")
        )
    else:
        signals = detector.detect()
        score = ContextScorer().score(signals)
        mode = score.mode

        mode_labels = {
            SessionMode.RND: "R&D",
            SessionMode.MIXED: "Mixed",
            SessionMode.BUGFIX: "Bugfix",
        }
        label = mode_labels.get(mode, mode.value)
        conf = "high" if score.confidence >= 0.7 else "medium" if score.confidence >= 0.4 else "low"
        results.append(
            CheckResult(
                "Session mode",
                "info",
                f"{label} (score: {score.score:.2f}, confidence: {conf})",
            )
        )

    # Show threshold adjustments for non-MIXED modes
    if mode != SessionMode.MIXED:
        adapter = ContextAdapter()
        adjustments = adapter.format_adjustments(mode)
        for adj in adjustments:
            results.append(CheckResult("Threshold", "info", adj))

    return results


def run_preflight(root: Path) -> list[CheckResult]:
    """Run all preflight checks and return results."""
    results = [
        check_branch(root),
        check_uncommitted(root),
        check_ahead_behind(root),
        check_test_baseline(root),
        check_config_valid(),
        check_hook_installed(root),
        check_decisions_md(root),
        check_assertions(root),
        # Doc freshness checks
        check_version_consistency(root),
        check_test_count_freshness(root),
        check_claude_md_freshness(root),
        check_changelog_current(root),
    ]
    # Session context (returns list — may include threshold adjustments)
    results.extend(check_session_mode(root))
    return results


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
