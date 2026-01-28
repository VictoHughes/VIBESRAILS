"""Senior Mode Guards - Concrete checks for vibe coding issues."""
import ast
import re
import importlib.util
from dataclasses import dataclass
from typing import Literal


@dataclass
class GuardIssue:
    """An issue detected by a guard."""
    guard: str
    severity: Literal["warn", "block"]
    message: str
    file: str | None = None
    line: int | None = None


class DiffSizeGuard:
    """Warns when too much code is added in one commit."""

    def __init__(self, max_lines: int = 200, warn_at: int = 100):
        self.max_lines = max_lines
        self.warn_at = warn_at

    def check(self, diff: str) -> list[GuardIssue]:
        """Check diff size."""
        added_lines = len([line for line in diff.splitlines() if line.startswith("+")])

        if added_lines > self.max_lines:
            return [GuardIssue(
                guard="DiffSizeGuard",
                severity="block",
                message=f"{added_lines} lines added (max: {self.max_lines}). "
                        "Large changes need careful review. Split into smaller commits?"
            )]
        elif added_lines > self.warn_at:
            return [GuardIssue(
                guard="DiffSizeGuard",
                severity="warn",
                message=f"{added_lines} lines added. Consider reviewing carefully."
            )]
        return []


class ErrorHandlingGuard:
    """Detects poor error handling patterns."""

    PATTERNS = [
        (r"except:\s*$", "Bare except clause - catches all exceptions including KeyboardInterrupt"),
        (r"except:\s*pass", "except: pass - silently swallows errors"),
        (r"except Exception:\s*pass", "except Exception: pass - silently swallows errors"),
    ]

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for error handling issues."""
        issues = []
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            for pattern, message in self.PATTERNS:
                if re.search(pattern, line):
                    issues.append(GuardIssue(
                        guard="ErrorHandlingGuard",
                        severity="warn",
                        message=message,
                        file=filepath,
                        line=i
                    ))
        return issues


class HallucinationGuard:
    """Detects imports that might be AI hallucinations."""

    STDLIB = {
        "os", "sys", "re", "json", "datetime", "pathlib", "typing", "collections",
        "itertools", "functools", "dataclasses", "ast", "hashlib", "logging",
        "unittest", "pytest", "time", "random", "math", "copy", "io", "shutil",
        "subprocess", "argparse", "importlib", "abc", "contextlib", "enum",
    }

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for potentially hallucinated imports."""
        issues = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if not self._module_exists(module):
                        issues.append(GuardIssue(
                            guard="HallucinationGuard",
                            severity="block",
                            message=f"Module '{alias.name}' not found - possible hallucination?",
                            file=filepath,
                            line=node.lineno
                        ))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if not self._module_exists(module):
                        issues.append(GuardIssue(
                            guard="HallucinationGuard",
                            severity="block",
                            message=f"Module '{node.module}' not found - possible hallucination?",
                            file=filepath,
                            line=node.lineno
                        ))

        return issues

    def _module_exists(self, module: str) -> bool:
        """Check if a module exists."""
        if module in self.STDLIB:
            return True
        try:
            spec = importlib.util.find_spec(module)
            return spec is not None
        except (ModuleNotFoundError, ValueError):
            return False


class DependencyGuard:
    """Detects new dependencies being added."""

    def check(self, old_requirements: str, new_requirements: str) -> list[GuardIssue]:
        """Check for new dependencies."""
        old_deps = self._parse_requirements(old_requirements)
        new_deps = self._parse_requirements(new_requirements)

        added = new_deps - old_deps
        issues = []

        for dep in added:
            issues.append(GuardIssue(
                guard="DependencyGuard",
                severity="warn",
                message=f"New dependency: {dep} - Is this necessary? Check size/vulnerabilities."
            ))

        return issues

    def _parse_requirements(self, content: str) -> set[str]:
        """Parse package names from requirements."""
        deps = set()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                if match:
                    deps.add(match.group(1).lower())
        return deps


class TestCoverageGuard:
    """Warns when code is added without corresponding tests."""

    def __init__(self, min_ratio: float = 0.3):
        self.min_ratio = min_ratio

    def check(self, code_diff: str, test_diff: str) -> list[GuardIssue]:
        """Check test coverage for new code."""
        code_added = len([l for l in code_diff.splitlines() if l.startswith("+") and not l.startswith("+++")])
        test_added = len([l for l in test_diff.splitlines() if l.startswith("+") and not l.startswith("+++")])

        if code_added > 20 and test_added == 0:
            return [GuardIssue(
                guard="TestCoverageGuard",
                severity="warn",
                message=f"{code_added} lines of code added with no tests. "
                        "AI generates code, YOU should test it."
            )]
        elif code_added > 50 and test_added < code_added * self.min_ratio:
            ratio = test_added / code_added if code_added > 0 else 0
            return [GuardIssue(
                guard="TestCoverageGuard",
                severity="warn",
                message=f"Test ratio {ratio:.0%} below minimum {self.min_ratio:.0%}. "
                        f"Add more tests for {code_added} lines of new code."
            )]

        return []


class SeniorGuards:
    """Run all Senior Mode guards."""

    def __init__(self):
        self.diff_guard = DiffSizeGuard()
        self.error_guard = ErrorHandlingGuard()
        self.hallucination_guard = HallucinationGuard()
        self.dependency_guard = DependencyGuard()
        self.test_guard = TestCoverageGuard()

    def check_all(
        self,
        code_diff: str,
        test_diff: str = "",
        files: list[tuple[str, str]] | None = None,
        old_requirements: str = "",
        new_requirements: str = "",
    ) -> list[GuardIssue]:
        """Run all guards and collect issues."""
        issues = []

        issues.extend(self.diff_guard.check(code_diff))
        issues.extend(self.test_guard.check(code_diff, test_diff))

        if old_requirements or new_requirements:
            issues.extend(self.dependency_guard.check(old_requirements, new_requirements))

        if files:
            for filepath, content in files:
                issues.extend(self.error_guard.check(content, filepath))
                issues.extend(self.hallucination_guard.check(content, filepath))

        return issues
