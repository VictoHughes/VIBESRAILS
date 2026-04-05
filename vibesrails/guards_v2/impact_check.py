"""Impact Check Guard — AST call graph index to find callers of a function."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "impact-check"

_SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    ".eggs",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "tests",
}


@dataclass
class CallerRef:
    """A reference to a call site for a named function."""

    file: str
    line: int
    caller_name: str


@dataclass
class CallIndex:
    """Index mapping called function names to their call sites."""

    callers: dict[str, list[CallerRef]] = field(default_factory=dict)

    def get_callers(self, name: str) -> list[CallerRef]:
        """Return all call sites for *name*, or empty list if none."""
        return self.callers.get(name, [])


def _iter_py_files(root: Path, limit: int = 300):
    """Yield .py files under *root*, skipping excluded directories."""
    count = 0
    for path in sorted(root.rglob("*.py")):
        if count >= limit:
            break
        # Skip any path whose parts contain a skip dir or test file patterns
        parts = path.parts
        skip = False
        for part in parts:
            if part in _SKIP_DIRS:
                skip = True
                break
            # Skip test files by naming convention (but only for the filename)
        if skip:
            continue
        # Skip individual *_test.py files
        if path.name.endswith("_test.py"):
            continue
        # Skip test_* files
        if path.name.startswith("test_"):
            continue
        yield path
        count += 1


class _CallVisitor(ast.NodeVisitor):
    """Walk an AST and record all function call sites."""

    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
        self._current_func: str = "<module>"
        # List of (called_name, line, caller_func)
        self.calls: list[tuple[str, int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = prev

    def visit_Call(self, node: ast.Call) -> None:
        name: str | None = None

        if isinstance(node.func, ast.Name):
            # Direct call: helper()
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Attribute call: obj.method() — record just the method name
            name = node.func.attr

        if name is not None:
            self.calls.append((name, node.lineno, self._current_func))

        self.generic_visit(node)


def build_call_index(root: Path) -> CallIndex:
    """Parse all source files under *root* and build a call index.

    Only source files (excluding tests and virtualenvs) are indexed.
    Returns a :class:`CallIndex` mapping each called function name to
    the list of :class:`CallerRef` objects that call it.
    """
    index = CallIndex()

    for py_file in _iter_py_files(root):
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        visitor = _CallVisitor(str(py_file))
        visitor.visit(tree)

        for called_name, lineno, caller_func in visitor.calls:
            if called_name not in index.callers:
                index.callers[called_name] = []
            index.callers[called_name].append(
                CallerRef(
                    file=str(py_file),
                    line=lineno,
                    caller_name=caller_func,
                )
            )

    return index


class ImpactCheckGuard:
    """Guards that use the call index to assess the impact of changes."""

    def check_removed(
        self,
        removed_names: list[str],
        index: CallIndex,
    ) -> list[V2GuardIssue]:
        """Emit a block-severity issue for each removed function that still has callers."""
        issues: list[V2GuardIssue] = []
        for name in removed_names:
            refs = index.get_callers(name)
            if not refs:
                continue
            # Report one issue per call site so the developer sees every location
            for ref in refs:
                issues.append(
                    V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="block",
                        message=(
                            f"Removed function '{name}' is still called by "
                            f"'{ref.caller_name}'"
                        ),
                        file=ref.file,
                        line=ref.line,
                    )
                )
        return issues

    def check_modified(
        self,
        modified_names: list[str],
        index: CallIndex,
    ) -> list[V2GuardIssue]:
        """Emit a warn-severity issue for each modified function that has callers."""
        issues: list[V2GuardIssue] = []
        for name in modified_names:
            refs = index.get_callers(name)
            if not refs:
                continue
            for ref in refs:
                issues.append(
                    V2GuardIssue(
                        guard=GUARD_NAME,
                        severity="warn",
                        message=(
                            f"Modified function '{name}' is called by "
                            f"'{ref.caller_name}' — verify compatibility"
                        ),
                        file=ref.file,
                        line=ref.line,
                    )
                )
        return issues
