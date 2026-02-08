"""Test Integrity Guard — Detects cheating tests that over-mock."""

import ast
import logging
from pathlib import Path

from . import test_integrity_detectors as det
from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "test-integrity"


class TestIntegrityGuard:
    """Detects tests that cheat by over-mocking."""

    def scan_file(
        self, filepath: Path, content: str,
    ) -> list[V2GuardIssue]:
        """Scan a single test file for integrity issues."""
        if not filepath.name.startswith("test_"):
            return []
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        fname = str(filepath)
        issues: list[V2GuardIssue] = []

        mock_count, total = det.count_mocks(tree)
        if total > 0:
            ratio = mock_count / total
            if ratio > 0.8:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        "Tests mock too much — mocks hide real bugs"
                        f" ({mock_count}/{total} = {ratio:.0%})"
                    ),
                    file=fname,
                ))
            elif ratio > 0.6:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "Tests mock too much — mocks hide real bugs"
                        f" ({mock_count}/{total} = {ratio:.0%})"
                    ),
                    file=fname,
                ))

        issues.extend(det.detect_sut_mocking(tree, filepath))
        issues.extend(det.detect_assert_free(tree, fname))
        issues.extend(det.detect_trivial_assertions(tree, fname))
        issues.extend(det.detect_mock_echo(tree, fname))
        issues.extend(det.detect_missing_imports(tree, filepath))

        return issues

    def scan(
        self, project_root: Path,
    ) -> list[V2GuardIssue]:
        """Scan tests/ directory for test integrity issues."""
        issues: list[V2GuardIssue] = []
        test_dir = project_root / "tests"
        if not test_dir.is_dir():
            return issues

        mock_ratios: list[float] = []

        for py_file in sorted(test_dir.rglob("test_*.py")):
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            issues.extend(self.scan_file(py_file, content))

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            mc, total = det.count_mocks(tree)
            if total > 0:
                mock_ratios.append(mc / total)

        if mock_ratios and all(r > 0.5 for r in mock_ratios):
            has_integration = any(
                r < 0.2 for r in mock_ratios
            )
            if not has_integration:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "No integration tests found"
                        " — add tests that run real code"
                    ),
                    file=str(test_dir),
                ))

        return issues
