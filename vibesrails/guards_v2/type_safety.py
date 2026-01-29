"""Type Safety Guard — Detects missing type annotations and unsafe typing."""

import ast
import re
import subprocess
import sys
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD_NAME = "type-safety"

# Params to skip when checking annotations
_SKIP_PARAMS = {"self", "cls"}

# Pattern for bare `# type: ignore` without explanation
_BARE_TYPE_IGNORE = re.compile(
    r"#\s*type:\s*ignore\s*$", re.MULTILINE
)


class TypeSafetyGuard:
    """Detects missing type annotations and unsafe typing patterns."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for type safety issues."""
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        issues.extend(self._missing_return_types(tree, fname))
        issues.extend(self._missing_param_types(tree, fname))
        issues.extend(self._explicit_any(tree, fname))
        issues.extend(
            self._bare_type_ignore(content, fname)
        )

        return issues

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan all Python files under *project_root*."""
        issues: list[V2GuardIssue] = []
        for py_file in sorted(project_root.rglob("*.py")):
            if _is_excluded(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            issues.extend(self.scan_file(py_file, content))

        issues.extend(self._run_mypy(project_root))
        return issues

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------

    def _missing_return_types(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Public functions without return type annotation."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            if node.name.startswith("_"):
                continue
            if node.returns is None:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        f"Public function '{node.name}' "
                        f"has no return type annotation"
                    ),
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _missing_param_types(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Public function params without type annotations."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            if node.name.startswith("_"):
                continue
            for arg in node.args.args:
                if arg.arg in _SKIP_PARAMS:
                    continue
                if arg.annotation is None:
                    issues.append(V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="warn",
                        message=(
                            f"Parameter '{arg.arg}' in "
                            f"'{node.name}' has no type"
                        ),
                        file=filepath,
                        line=node.lineno,
                    ))
        return issues

    def _explicit_any(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Warn on explicit use of Any type."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "Any":
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="info",
                    message="Explicit 'Any' usage detected",
                    file=filepath,
                    line=node.lineno,
                ))
            elif (
                isinstance(node, ast.Attribute)
                and node.attr == "Any"
                and isinstance(node.value, ast.Name)
                and node.value.id == "typing"
            ):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="info",
                    message="Explicit 'Any' usage detected",
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _bare_type_ignore(
        self, content: str, filepath: str
    ) -> list[V2GuardIssue]:
        """Find bare `# type: ignore` without explanation."""
        issues: list[V2GuardIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.rstrip()
            if not re.search(
                r"#\s*type:\s*ignore", stripped
            ):
                continue
            # Has bracket explanation like [attr-defined]?
            if re.search(
                r"#\s*type:\s*ignore\[", stripped
            ):
                continue
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    "Bare '# type: ignore' without "
                    "error code"
                ),
                file=filepath,
                line=i,
            ))
        return issues

    # ------------------------------------------------------------------
    # Optional mypy integration
    # ------------------------------------------------------------------

    def _run_mypy(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run mypy if available and parse results."""
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "mypy",
                    "--no-error-summary",
                    "--no-color",
                    str(project_root),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        if result.returncode == 0:
            return []

        issues: list[V2GuardIssue] = []
        for line in result.stdout.splitlines():
            match = re.match(
                r"(.+):(\d+):\s*error:\s*(.+)", line
            )
            if match:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"mypy: {match.group(3)}",
                    file=match.group(1),
                    line=int(match.group(2)),
                ))
        return issues


def _is_excluded(path: Path) -> bool:
    """Skip venvs, hidden dirs, test files, __init__."""
    if path.name == "__init__.py":
        return True
    if path.name.startswith("test_"):
        return True
    parts = path.parts
    for part in parts:
        if part.startswith(".") or part == "__pycache__":
            return True
        if part in (
            "venv", ".venv", "node_modules",
            "site-packages", "tests",
        ):
            return True
    return False
