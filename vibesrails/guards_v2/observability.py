"""Observability Guard — Detects poor logging practices."""

import ast
import logging
import re
from fnmatch import fnmatch
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "observability"

# Files to skip (CLI, test, entry-point files)
_SKIP_PATTERNS = [
    "**/cli.py",
    "**/cli_*.py",
    "**/__main__.py",
    "**/test_*",
    "**/conftest.py",
]

# Regex for print statements that look like logging
_PRINT_LOG_RE = re.compile(
    r"""\bprint\s*\(\s*(?:f?["'](?:DEBUG|ERROR|WARN|INFO):)""",
    re.IGNORECASE,
)


class ObservabilityGuard:
    """Detects poor observability practices in Python code."""

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for observability issues."""
        if _should_skip(filepath):
            return []
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        issues.extend(self._bare_prints(tree, fname))
        issues.extend(self._traceback_print_exc(tree, fname))
        issues.extend(self._silent_except(tree, fname))
        issues.extend(self._logging_without_level(tree, fname))
        issues.extend(
            self._print_looks_like_logging(content, fname)
        )
        return issues

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan all Python files under *project_root*."""
        issues: list[V2GuardIssue] = []
        for py_file in sorted(project_root.rglob("*.py")):
            if _is_excluded(py_file) or _should_skip(py_file):
                continue
            try:
                text = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            issues.extend(self.scan_file(py_file, text))
        return issues

    # ----------------------------------------------------------
    # Detectors
    # ----------------------------------------------------------

    def _bare_prints(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Detect print() calls (debug leftovers)."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            if _is_print_call(call):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message="print() found — use logger instead",
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _traceback_print_exc(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Detect traceback.print_exc() usage."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            if _is_traceback_print_exc(call):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "traceback.print_exc() — "
                        "use logger.exception() instead"
                    ),
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _silent_except(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Detect except blocks with no logging at all."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not _body_has_logging(node.body):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "except block without logging "
                        "— silent error swallowing"
                    ),
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _logging_without_level(
        self, tree: ast.Module, filepath: str
    ) -> list[V2GuardIssue]:
        """Detect logging.log() without level or bare logger()."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr):
                continue
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            if _is_logging_log_no_level(call):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "logging.log() without explicit level"
                    ),
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    def _print_looks_like_logging(
        self, content: str, filepath: str
    ) -> list[V2GuardIssue]:
        """Detect print('DEBUG:...') or print('Error:...')."""
        issues: list[V2GuardIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            if _PRINT_LOG_RE.search(line):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "print() used as logging — "
                        "use a proper logger"
                    ),
                    file=filepath,
                    line=i,
                ))
        return issues


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

_LOG_METHODS = frozenset({
    "debug", "info", "warning", "error", "critical",
    "exception", "log", "warn",
})


def _is_print_call(call: ast.Call) -> bool:
    """True if call is print(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "print":
        return True
    return False


def _is_traceback_print_exc(call: ast.Call) -> bool:
    """True if call is traceback.print_exc()."""
    func = call.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "print_exc"
        and isinstance(func.value, ast.Name)
        and func.value.id == "traceback"
    ):
        return True
    return False


def _is_logging_log_no_level(call: ast.Call) -> bool:
    """True if call is logging.log() with no level argument."""
    func = call.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "log":
        return False
    obj = func.value
    if isinstance(obj, ast.Name) and obj.id == "logging":
        # logging.log() needs at least 2 args (level, msg)
        if len(call.args) < 2:
            return True
    return False


def _is_logging_node(node: ast.AST) -> bool:
    """Check if a node represents logging, printing, raise, or return."""
    if isinstance(node, (ast.Raise, ast.Return)):
        return True
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    if isinstance(func, ast.Attribute) and func.attr in _LOG_METHODS:
        return True
    return isinstance(func, ast.Name) and func.id == "print"


def _body_has_logging(body: list[ast.stmt]) -> bool:
    """Check if a list of statements contains any logging."""
    return any(
        _is_logging_node(node)
        for node in ast.walk(ast.Module(body=body, type_ignores=[]))
    )


def _should_skip(filepath: Path) -> bool:
    """Check if file matches skip patterns."""
    name = filepath.name
    s = str(filepath)
    for pat in _SKIP_PATTERNS:
        if fnmatch(s, pat) or fnmatch(name, pat.split("/")[-1]):
            return True
    return False


def _is_excluded(path: Path) -> bool:
    """Skip virtual-envs, hidden dirs, and __pycache__."""
    for part in path.parts:
        if part.startswith(".") or part == "__pycache__":
            return True
        if part in ("venv", ".venv", "node_modules", "site-packages"):
            return True
    return False
