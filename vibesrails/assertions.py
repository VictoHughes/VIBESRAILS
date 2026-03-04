"""Assertions system — validate project truths against decisions.

Checks three categories from vibesrails.yaml `assertions:` section:
- values: grep code for expected literal values
- rules: structural checks (fail_closed, single_entry_point)
- baselines: compare metrics against expected thresholds
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .scanner_types import BLUE, GREEN, NC, RED

logger = logging.getLogger(__name__)

_SKIP_DIRS = (
    "__pycache__", ".venv", "venv", "node_modules",
    ".git", "build", "dist", ".egg",
)


@dataclass
class AssertionResult:
    """Result of a single assertion check."""

    category: str  # "values", "rules", "baselines"
    name: str
    status: Literal["ok", "fail"]
    message: str
    details: list[str] = field(default_factory=list)


def _collect_python_files(root: Path) -> list[Path]:
    """Collect Python files, skipping common non-project dirs."""
    files = []
    for py_file in root.rglob("*.py"):
        if any(p in str(py_file) for p in _SKIP_DIRS):
            continue
        files.append(py_file)
    return files


# ── Values ──────────────────────────────────────────────────────


def check_values(root: Path, values: dict) -> list[AssertionResult]:
    """Check that declared values appear in project code."""
    results = []
    if not values:
        return results

    py_files = _collect_python_files(root)

    for key, expected in values.items():
        expected_str = str(expected)
        found_in = []
        for py_file in py_files:
            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if expected_str in content:
                found_in.append(str(py_file.relative_to(root)))

        if found_in:
            results.append(AssertionResult(
                category="values",
                name=key,
                status="ok",
                message=f"{key} = {expected_str!r} found in {len(found_in)} file(s)",
                details=found_in[:5],
            ))
        else:
            results.append(AssertionResult(
                category="values",
                name=key,
                status="fail",
                message=f"{key} = {expected_str!r} not found in any Python file",
            ))

    return results


# ── Rules ───────────────────────────────────────────────────────


def _check_rule_fail_closed(root: Path) -> AssertionResult:
    """Check that except blocks don't silently pass (fail-closed pattern)."""
    violations = []
    for py_file in _collect_python_files(root):
        try:
            lines = py_file.read_text().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r"except\s.*:\s*$", stripped) or stripped == "except:":
                # Check if next non-empty line is just `pass`
                for next_line in lines[i:]:
                    next_stripped = next_line.strip()
                    if not next_stripped:
                        continue
                    if next_stripped == "pass":
                        rel = py_file.relative_to(root)
                        violations.append(f"{rel}:{i}")
                    break

    if violations:
        return AssertionResult(
            category="rules",
            name="fail_closed",
            status="fail",
            message=f"{len(violations)} silent exception handler(s) — errors must not be swallowed",
            details=violations[:10],
        )
    return AssertionResult(
        category="rules",
        name="fail_closed",
        status="ok",
        message="No silent exception handlers found",
    )


def _check_rule_single_entry_point(root: Path) -> AssertionResult:
    """Check that only one if __name__ == '__main__' exists in src code."""
    entry_points = []
    for py_file in _collect_python_files(root):
        # Skip test files
        if "test" in py_file.name:
            continue
        try:
            content = py_file.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content):
            entry_points.append(str(py_file.relative_to(root)))

    if len(entry_points) <= 1:
        return AssertionResult(
            category="rules",
            name="single_entry_point",
            status="ok",
            message=f"{len(entry_points)} entry point(s) found",
            details=entry_points,
        )
    return AssertionResult(
        category="rules",
        name="single_entry_point",
        status="fail",
        message=f"{len(entry_points)} entry points — expected at most 1",
        details=entry_points[:10],
    )


_RULE_CHECKERS = {
    "fail_closed": _check_rule_fail_closed,
    "single_entry_point": _check_rule_single_entry_point,
}


def check_rules(root: Path, rules: dict) -> list[AssertionResult]:
    """Run structural rule checks."""
    results = []
    if not rules:
        return results

    for rule_name, enabled in rules.items():
        if not enabled:
            continue
        checker = _RULE_CHECKERS.get(rule_name)
        if checker:
            results.append(checker(root))
        else:
            results.append(AssertionResult(
                category="rules",
                name=rule_name,
                status="fail",
                message=f"Unknown rule: {rule_name}",
            ))

    return results


# ── Baselines ───────────────────────────────────────────────────


def _get_test_count(root: Path) -> int | None:
    """Run pytest --collect-only to count tests."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "--timeout=30"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Summary line like "2080 tests collected in 0.86s"
        combined = result.stdout + "\n" + result.stderr
        for line in reversed(combined.splitlines()):
            match = re.search(r"(\d+)\s+tests?\s", line)
            if match:
                return int(match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def check_baselines(root: Path, baselines: dict) -> list[AssertionResult]:
    """Compare project metrics against declared baselines."""
    results = []
    if not baselines:
        return results

    if "test_count" in baselines:
        expected = int(baselines["test_count"])
        actual = _get_test_count(root)
        if actual is None:
            results.append(AssertionResult(
                category="baselines",
                name="test_count",
                status="fail",
                message="Could not collect test count",
            ))
        elif actual >= expected:
            results.append(AssertionResult(
                category="baselines",
                name="test_count",
                status="ok",
                message=f"{actual} tests (baseline: {expected})",
            ))
        else:
            results.append(AssertionResult(
                category="baselines",
                name="test_count",
                status="fail",
                message=f"{actual} tests — below baseline of {expected} (delta: -{expected - actual})",
            ))

    if baselines.get("zero_regressions"):
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--timeout=60", "-q", "--tb=no"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                results.append(AssertionResult(
                    category="baselines",
                    name="zero_regressions",
                    status="ok",
                    message="All tests passing",
                ))
            else:
                # Extract failure count from output
                fail_match = re.search(r"(\d+)\s+failed", result.stdout)
                count = fail_match.group(1) if fail_match else "?"
                results.append(AssertionResult(
                    category="baselines",
                    name="zero_regressions",
                    status="fail",
                    message=f"{count} test(s) failing — zero regressions policy violated",
                ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results.append(AssertionResult(
                category="baselines",
                name="zero_regressions",
                status="fail",
                message="Could not run test suite",
            ))

    return results


# ── Orchestrator ────────────────────────────────────────────────


def run_assertions(root: Path, assertions_config: dict) -> list[AssertionResult]:
    """Run all assertion checks from config."""
    results = []
    results.extend(check_values(root, assertions_config.get("values", {})))
    results.extend(check_rules(root, assertions_config.get("rules", {})))
    results.extend(check_baselines(root, assertions_config.get("baselines", {})))
    return results


# ── Reporting ───────────────────────────────────────────────────

_CAT_ICONS = {
    "values": "📌",
    "rules": "📏",
    "baselines": "📊",
}


def format_assertions_report(results: list[AssertionResult]) -> str:
    """Format assertion results as a colored terminal report."""
    lines = [
        f"{BLUE}╔══════════════════════════════════════════════╗{NC}",
        f"{BLUE}║     📋 VIBESRAILS ASSERTIONS CHECK           ║{NC}",
        f"{BLUE}╚══════════════════════════════════════════════╝{NC}",
        "",
    ]

    # Group by category
    by_cat: dict[str, list[AssertionResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    for cat in ("values", "rules", "baselines"):
        cat_results = by_cat.get(cat, [])
        if not cat_results:
            continue
        icon = _CAT_ICONS.get(cat, "")
        lines.append(f"{BLUE}{icon} {cat.upper()}{NC}")
        for r in cat_results:
            status_icon = f"{GREEN}✅" if r.status == "ok" else f"{RED}❌"
            lines.append(f"  {status_icon} {r.name}: {r.message}{NC}")
            for detail in r.details[:5]:
                lines.append(f"     {detail}")
        lines.append("")

    failures = sum(1 for r in results if r.status == "fail")
    passes = sum(1 for r in results if r.status == "ok")
    lines.append("──────────────────────────────────────────────")
    if failures:
        lines.append(f"{RED}Result: {failures} assertion(s) failed, {passes} passed{NC}")
    else:
        lines.append(f"{GREEN}Result: All {passes} assertion(s) passed{NC}")

    return "\n".join(lines)


def assertions_exit_code(results: list[AssertionResult]) -> int:
    """Exit code: 0=all pass, 1=failures."""
    return 1 if any(r.status == "fail" for r in results) else 0
