"""Senior Mode Guards - Concrete checks for vibe coding issues."""
import ast
import importlib.util
import re
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
                # Skip relative imports (from . or from .. etc.)
                if node.level > 0:
                    continue
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
        code_added = len([line for line in code_diff.splitlines() if line.startswith("+") and not line.startswith("+++")])
        test_added = len([line for line in test_diff.splitlines() if line.startswith("+") and not line.startswith("+++")])

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


class LazyCodeGuard:
    """Detects lazy coding patterns - placeholders, shortcuts, incomplete code."""

    PATTERNS = [
        # Placeholder patterns
        (r"^\s*pass\s*$", "pass without comment - implement or explain why empty"),
        (r"^\s*\.\.\.\s*$", "Ellipsis placeholder - implement the actual code"),
        (r"raise NotImplementedError\s*\(\s*\)", "NotImplementedError without message - explain what's missing"),
        (r"raise NotImplementedError\s*$", "NotImplementedError without message - explain what's missing"),
        # Lazy TODO patterns
        (r"#\s*TODO\s*$", "TODO without description - be specific about what needs doing"),
        (r"#\s*FIXME\s*$", "FIXME without description - explain what's broken"),
        (r"#\s*XXX\s*$", "XXX marker without explanation"),
        (r"#\s*HACK\s*$", "HACK without justification - document why this is necessary"),
        # Lazy return patterns
        (r"return None\s*#", "Explicit return None - is this intentional or lazy?"),
    ]

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for lazy code patterns."""
        issues = []
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            for pattern, message in self.PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(GuardIssue(
                        guard="LazyCodeGuard",
                        severity="warn",
                        message=f"Lazy pattern: {message}",
                        file=filepath,
                        line=i
                    ))

        # Check for empty functions (more than just pass)
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = node.body
                    # Function with only pass or docstring+pass
                    if len(body) == 1 and isinstance(body[0], ast.Pass):
                        issues.append(GuardIssue(
                            guard="LazyCodeGuard",
                            severity="warn",
                            message=f"Empty function '{node.name}' - implement or remove",
                            file=filepath,
                            line=node.lineno
                        ))
                    elif len(body) == 2:
                        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                            if isinstance(body[1], ast.Pass):
                                issues.append(GuardIssue(
                                    guard="LazyCodeGuard",
                                    severity="warn",
                                    message=f"Function '{node.name}' has only docstring+pass - implement it",
                                    file=filepath,
                                    line=node.lineno
                                ))
        except SyntaxError:
            pass

        return issues


class BypassGuard:
    """Detects code that bypasses safety checks without justification."""

    PATTERNS = [
        # Type checking bypasses
        (r"#\s*type:\s*ignore\s*$", "type: ignore without code - specify what you're ignoring [error-code]"),
        (r"#\s*type:\s*ignore\s*\[", None),  # OK if has code
        # Linter bypasses
        (r"#\s*noqa\s*$", "noqa without code - specify which rule: # noqa: E501"),
        (r"#\s*noqa:\s*[A-Z]", None),  # OK if has code
        # Security bypasses
        (r"#\s*nosec\s*$", "nosec without justification - explain why this is safe"),
        (r"#\s*nosemgrep\s*$", "nosemgrep without rule - specify which rule"),
        # Coverage bypasses
        (r"#\s*pragma:\s*no\s*cover\s*$", "pragma: no cover - justify why this isn't tested"),
        # Git bypasses in code
        (r"--no-verify", "git --no-verify in code - don't encourage skipping hooks"),
        (r"git commit.*-n\b", "git commit -n (no-verify) - don't skip hooks"),
    ]

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for unjustified bypass comments."""
        issues = []
        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            for pattern, message in self.PATTERNS:
                if message is None:  # OK pattern
                    continue
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if there's justification after
                    if not re.search(pattern + r".*\w{10,}", line):  # No long explanation after
                        issues.append(GuardIssue(
                            guard="BypassGuard",
                            severity="warn",
                            message=f"Unjustified bypass: {message}",
                            file=filepath,
                            line=i
                        ))

        return issues


class ResilienceGuard:
    """Detects code lacking resilience patterns."""

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for missing resilience patterns."""
        issues = []
        lines = code.splitlines()

        # Check for network calls without timeout
        network_patterns = [
            (r"requests\.(get|post|put|delete|patch)\s*\([^)]*\)", "timeout"),
            (r"urllib\.request\.urlopen\s*\([^)]*\)", "timeout"),
            (r"httpx\.(get|post|put|delete|patch)\s*\([^)]*\)", "timeout"),
            (r"aiohttp\.ClientSession\(\s*\)", "timeout"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, missing in network_patterns:
                if re.search(pattern, line) and missing not in line.lower():
                    issues.append(GuardIssue(
                        guard="ResilienceGuard",
                        severity="warn",
                        message=f"Network call without {missing} - add timeout to prevent hanging",
                        file=filepath,
                        line=i
                    ))

        # Check for database calls without error handling context
        if "execute(" in code or "cursor." in code:
            if "try:" not in code or "except" not in code:
                # Find the line with execute
                for i, line in enumerate(lines, 1):
                    if "execute(" in line or "cursor." in line:
                        issues.append(GuardIssue(
                            guard="ResilienceGuard",
                            severity="warn",
                            message="Database operation without try/except - handle connection errors",
                            file=filepath,
                            line=i
                        ))
                        break

        # Check for file operations without context manager
        file_patterns = [
            (r"open\s*\([^)]+\)\s*$", "File open without context manager - use 'with open(...)'"),
            (r"\.read\(\)\s*$", None),  # OK
        ]

        for i, line in enumerate(lines, 1):
            # Skip if line has 'with'
            if "with " in line:
                continue
            for pattern, message in file_patterns:
                if message and re.search(pattern, line):
                    # Check if previous line has 'with'
                    if i > 1 and "with " not in lines[i-2]:
                        issues.append(GuardIssue(
                            guard="ResilienceGuard",
                            severity="warn",
                            message=message,
                            file=filepath,
                            line=i
                        ))

        return issues


class SeniorGuards:
    """Run all Senior Mode guards."""

    def __init__(self):
        self.diff_guard = DiffSizeGuard()
        self.error_guard = ErrorHandlingGuard()
        self.hallucination_guard = HallucinationGuard()
        self.dependency_guard = DependencyGuard()
        self.test_guard = TestCoverageGuard()
        self.lazy_guard = LazyCodeGuard()
        self.bypass_guard = BypassGuard()
        self.resilience_guard = ResilienceGuard()

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
                issues.extend(self.lazy_guard.check(content, filepath))
                issues.extend(self.bypass_guard.check(content, filepath))
                issues.extend(self.resilience_guard.check(content, filepath))

        return issues
