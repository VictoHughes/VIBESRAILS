"""Dead Code Guard — Detects unused imports, variables, and unreachable code."""

import ast
import logging
import subprocess
import sys
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "dead-code"

# Statements after which code is unreachable
_TERMINAL_STMTS = (ast.Return, ast.Raise, ast.Break, ast.Continue)


class DeadCodeGuard:
    """Detects dead code using AST analysis and optional vulture."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for dead code issues."""
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        issues.extend(self._unused_imports(tree, content, fname))
        issues.extend(self._unreachable_code(tree, fname))
        issues.extend(self._unused_variables(tree, content, fname))
        issues.extend(self._empty_functions(tree, fname))

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

        issues.extend(self._run_vulture(project_root))
        return issues

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_imports(tree: ast.Module) -> list[tuple[str, int]]:
        """Collect all imported names with their line numbers."""
        imported: list[tuple[str, int]] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append((alias.asname or alias.name.split(".")[0], node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported.append((alias.asname or alias.name, node.lineno))
        return imported

    @staticmethod
    def _collect_used_names(tree: ast.Module) -> set[str]:
        """Collect all Name references in the AST."""
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

    def _unused_imports(
        self,
        tree: ast.Module,
        content: str,
        filepath: str,
    ) -> list[V2GuardIssue]:
        """Find imports whose names are never referenced."""
        imported = self._collect_imports(tree)
        used_names = self._collect_used_names(tree)

        return [
            V2GuardIssue(
                guard=GUARD_NAME, severity="info",
                message=f"Unused import: '{name}'",
                file=filepath, line=lineno,
            )
            for name, lineno in imported
            if name not in used_names
        ]

    def _unreachable_code(
        self,
        tree: ast.Module,
        filepath: str,
    ) -> list[V2GuardIssue]:
        """Detect statements that follow return/raise/break/continue."""
        issues: list[V2GuardIssue] = []
        self._walk_bodies(tree, filepath, issues)
        return issues

    def _walk_bodies(
        self,
        node: ast.AST,
        filepath: str,
        issues: list[V2GuardIssue],
    ) -> None:
        """Recurse into all statement-bearing nodes."""
        for field_name in ("body", "orelse", "finalbody", "handlers"):
            body = getattr(node, field_name, None)
            if not isinstance(body, list):
                continue
            self._check_body(body, filepath, issues)
            for child in body:
                self._walk_bodies(child, filepath, issues)

    def _check_body(
        self,
        body: list[ast.stmt],
        filepath: str,
        issues: list[V2GuardIssue],
    ) -> None:
        """Flag statements that appear after a terminal statement."""
        for i, stmt in enumerate(body):
            if isinstance(stmt, _TERMINAL_STMTS) and i < len(body) - 1:
                nxt = body[i + 1]
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message="Unreachable code after "
                            f"{type(stmt).__name__.lower()}",
                    file=filepath,
                    line=nxt.lineno,
                ))
                break  # only report once per body

    @staticmethod
    def _find_unused_in_func(func_node: ast.AST) -> list[tuple[str, int]]:
        """Find unused variables in a single function. Returns (name, lineno) pairs."""
        assigned: dict[str, int] = {}
        read: set[str] = set()
        for node in ast.walk(func_node):
            if not isinstance(node, ast.Name):
                continue
            if isinstance(node.ctx, ast.Store) and node.id not in assigned:
                assigned[node.id] = node.lineno
            elif isinstance(node.ctx, (ast.Load, ast.Del)):
                read.add(node.id)
        return [
            (name, lineno) for name, lineno in assigned.items()
            if not name.startswith("_") and name not in read
        ]

    def _unused_variables(
        self,
        tree: ast.Module,
        content: str,
        filepath: str,
    ) -> list[V2GuardIssue]:
        """Find variables assigned but never read (skip _ prefix)."""
        issues: list[V2GuardIssue] = []
        for func_node in ast.walk(tree):
            if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for name, lineno in self._find_unused_in_func(func_node):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME, severity="info",
                    message=f"Unused variable: '{name}'",
                    file=filepath, line=lineno,
                ))
        return issues

    def _empty_functions(
        self,
        tree: ast.Module,
        filepath: str,
    ) -> list[V2GuardIssue]:
        """Detect functions whose body is only `pass` or `...`."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if self._is_empty_body(node.body):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="info",
                    message=f"Empty function: '{node.name}'",
                    file=filepath,
                    line=node.lineno,
                ))
        return issues

    @staticmethod
    def _is_empty_body(body: list[ast.stmt]) -> bool:
        """Return True if body is only pass / Ellipsis (no docstring)."""
        if not body:
            return True
        # Filter out docstrings
        stmts = body
        if (
            isinstance(stmts[0], ast.Expr)
            and isinstance(stmts[0].value, (ast.Constant,))
            and isinstance(stmts[0].value.value, str)
        ):
            # Has a docstring — not considered empty
            return False
        for stmt in stmts:
            if isinstance(stmt, ast.Pass):
                continue
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is ...
            ):
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # Vulture integration
    # ------------------------------------------------------------------

    def _run_vulture(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run vulture if installed; parse its output."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "vulture", str(project_root)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        if result.returncode not in (0, 1):
            return []

        issues: list[V2GuardIssue] = []
        for line in result.stdout.splitlines():
            parts = line.split(":", maxsplit=2)
            if len(parts) < 3:
                continue
            fpath = parts[0]
            try:
                lineno = int(parts[1])
            except ValueError:
                continue
            msg = parts[2].strip()
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="info",
                message=f"vulture: {msg}",
                file=fpath,
                line=lineno,
            ))
        return issues


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _is_excluded(path: Path) -> bool:
    """Skip virtual-envs, hidden dirs, and __pycache__."""
    parts = path.parts
    for part in parts:
        if part.startswith(".") or part == "__pycache__":
            return True
        if part in ("venv", ".venv", "node_modules", "site-packages"):
            return True
    return False
