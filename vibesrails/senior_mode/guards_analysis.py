"""Senior Mode Guards - Analysis guards (hallucination, lazy code, bypass)."""
import ast
import importlib.util
import logging
import re

from vibesrails.senior_mode.guards import GuardIssue

logger = logging.getLogger(__name__)


class HallucinationGuard:
    """Detects imports that might be AI hallucinations."""

    STDLIB = {
        "os", "sys", "re", "json", "datetime", "pathlib", "typing", "collections",
        "itertools", "functools", "dataclasses", "ast", "hashlib", "logging",
        "unittest", "pytest", "time", "random", "math", "copy", "io", "shutil",
        "subprocess", "argparse", "importlib", "abc", "contextlib", "enum",
    }

    def _check_import_node(self, node: ast.Import, filepath: str) -> list[GuardIssue]:
        """Check an Import node for hallucinated modules."""
        issues = []
        for alias in node.names:
            module = alias.name.split(".")[0]
            if not self._module_exists(module):
                issues.append(GuardIssue(
                    guard="HallucinationGuard", severity="block",
                    message=f"Module '{alias.name}' not found - possible hallucination?",
                    file=filepath, line=node.lineno,
                ))
        return issues

    def _check_import_from_node(self, node: ast.ImportFrom, filepath: str) -> list[GuardIssue]:
        """Check an ImportFrom node for hallucinated modules."""
        if node.level > 0 or not node.module:
            return []
        module = node.module.split(".")[0]
        if self._module_exists(module):
            return []
        return [GuardIssue(
            guard="HallucinationGuard", severity="block",
            message=f"Module '{node.module}' not found - possible hallucination?",
            file=filepath, line=node.lineno,
        )]

    def check(self, code: str, filepath: str) -> list[GuardIssue]:
        """Check for potentially hallucinated imports."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        issues = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                issues.extend(self._check_import_node(node, filepath))
            elif isinstance(node, ast.ImportFrom):
                issues.extend(self._check_import_from_node(node, filepath))
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

    @staticmethod
    def _check_empty_functions(code: str, filepath: str) -> list[GuardIssue]:
        """Check for empty functions (only pass or docstring+pass)."""
        issues = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return issues
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = node.body
            is_empty = (len(body) == 1 and isinstance(body[0], ast.Pass))
            is_docstring_pass = (
                len(body) == 2
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[1], ast.Pass)
            )
            if is_empty:
                issues.append(GuardIssue(
                    guard="LazyCodeGuard", severity="warn",
                    message=f"Empty function '{node.name}' - implement or remove",
                    file=filepath, line=node.lineno
                ))
            elif is_docstring_pass:
                issues.append(GuardIssue(
                    guard="LazyCodeGuard", severity="warn",
                    message=f"Function '{node.name}' has only docstring+pass - implement it",
                    file=filepath, line=node.lineno
                ))
        return issues

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

        issues.extend(self._check_empty_functions(code, filepath))
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
        # Git bypasses in code — patterns split to avoid self-detection
        ("--no" + "-verify", "git --no" + "-verify in code - don't encourage skipping hooks"),
        ("git " + r"commit.*-n\b", "git " + "commit -n (no-verify) - don't skip hooks"),
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
