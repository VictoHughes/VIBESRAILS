"""Performance Guard — Detects common performance anti-patterns via AST + regex."""

import ast
import re
from pathlib import Path

from .dependency_audit import V2GuardIssue

# Patterns for DB calls that indicate potential N+1
_DB_CALL_PATTERNS = (
    "cursor.execute",
    "session.query",
    "objects.filter",
    "objects.get",
    "objects.all",
    "objects.exclude",
)

_SELECT_STAR_RE = re.compile(r"SELECT\s+\*", re.IGNORECASE)
_SQL_SELECT_RE = re.compile(
    r"SELECT\s+.+?\s+FROM\s+", re.IGNORECASE | re.DOTALL
)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_OFFSET_RE = re.compile(r"\bOFFSET\b", re.IGNORECASE)

_RE_FUNCS = {"re.search", "re.match", "re.findall", "re.sub"}

_IGNORE_MARKER = "# vibesrails: ignore"


class PerformanceGuard:
    """Detects performance anti-patterns in Python source files."""

    GUARD_NAME = "performance"

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Scan all .py files under *project_root* for performance issues."""
        issues: list[V2GuardIssue] = []
        for py_file in sorted(project_root.rglob("*.py")):
            # Skip hidden dirs, venv, etc.
            parts = py_file.relative_to(project_root).parts
            if any(p.startswith(".") or p in ("venv", "node_modules")
                   for p in parts):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            issues.extend(self.scan_file(py_file, content))
        return issues

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for performance anti-patterns."""
        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        # Regex-based checks (work even if AST parse fails)
        issues.extend(self._check_select_star(fname, content))
        issues.extend(self._check_no_limit(fname, content))
        issues.extend(
            self._check_time_sleep(fname, filepath, content)
        )
        issues.extend(self._check_read_no_limit(fname, content))

        # AST-based checks
        try:
            tree = ast.parse(content, filename=fname)
        except SyntaxError:
            return issues

        issues.extend(self._check_nplus1(fname, tree))
        issues.extend(self._check_regex_in_loop(fname, tree))
        issues.extend(self._check_string_concat_in_loop(fname, tree))
        issues.extend(self._check_len_listcomp(fname, tree))
        issues.extend(self._check_global_mutation(fname, tree, content))

        return issues

    def _check_select_star(self, fname: str, content: str) -> list[V2GuardIssue]:
        issues: list[V2GuardIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            if _IGNORE_MARKER in line:
                continue
            if _SELECT_STAR_RE.search(line):
                issues.append(V2GuardIssue(
                    guard=self.GUARD_NAME, severity="warn",
                    message="SELECT * found — specify columns explicitly",  # vibesrails: ignore — pattern definition
                    file=fname, line=i,
                ))
        return issues

    def _check_no_limit(self, fname: str, content: str) -> list[V2GuardIssue]:
        issues: list[V2GuardIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            if _SQL_SELECT_RE.search(line):
                if not _LIMIT_RE.search(line) and not _OFFSET_RE.search(line):
                    # Don't double-flag SELECT * lines  # vibesrails: ignore — pattern definition
                    if _SELECT_STAR_RE.search(line):
                        continue
                    issues.append(V2GuardIssue(
                        guard=self.GUARD_NAME,
                        severity="info",
                        message=(
                            "SQL query without LIMIT — "
                            "consider adding LIMIT to avoid large result sets"
                        ),
                        file=fname,
                        line=i,
                    ))
        return issues

    def _check_time_sleep(self, fname: str, filepath: Path, content: str) -> list[V2GuardIssue]:
        # Skip test files
        if filepath.name.startswith("test_") or "/tests/" in fname:
            return []
        issues: list[V2GuardIssue] = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if _IGNORE_MARKER in line:
                continue
            if "time.sleep(" in stripped and not stripped.startswith("#"):  # vibesrails: ignore — pattern definition
                issues.append(V2GuardIssue(
                    guard=self.GUARD_NAME,
                    severity="warn",
                    message=(
                        "time.sleep() in application code — "  # vibesrails: ignore — pattern definition
                        "consider async or event-based approach"
                    ),
                    file=fname,
                    line=i,
                ))
        return issues

    def _check_read_no_limit(self, fname: str, content: str) -> list[V2GuardIssue]:
        issues: list[V2GuardIssue] = []
        pat = re.compile(r"\.read\(\s*\)")
        for i, line in enumerate(content.splitlines(), 1):
            if pat.search(line):
                issues.append(V2GuardIssue(
                    guard=self.GUARD_NAME,
                    severity="info",
                    message=(
                        ".read() without size limit — "
                        "pass a max byte count to avoid memory issues"
                    ),
                    file=fname,
                    line=i,
                ))
        return issues

    def _check_nplus1(self, fname: str, tree: ast.Module) -> list[V2GuardIssue]:
        """Detect DB calls inside for loops (N+1 pattern)."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    src = _call_name(child)
                    if src and any(p in src for p in _DB_CALL_PATTERNS):
                        issues.append(V2GuardIssue(
                            guard=self.GUARD_NAME,
                            severity="warn",
                            message=(
                                f"Potential N+1 query: {src} "
                                f"inside for loop"
                            ),
                            file=fname,
                            line=child.lineno,
                        ))
        return issues

    def _check_regex_in_loop(self, fname: str, tree: ast.Module) -> list[V2GuardIssue]:
        """Detect re.search/match/findall inside loops."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    src = _call_name(child)
                    if src and src in _RE_FUNCS:
                        issues.append(V2GuardIssue(
                            guard=self.GUARD_NAME,
                            severity="info",
                            message=(
                                f"{src} inside loop — "
                                f"precompile with re.compile()"
                            ),
                            file=fname,
                            line=child.lineno,
                        ))
        return issues

    def _check_string_concat_in_loop(self, fname: str, tree: ast.Module) -> list[V2GuardIssue]:
        """Detect += on string variables inside loops."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.AugAssign)
                    and isinstance(child.op, ast.Add)
                    and isinstance(child.target, ast.Name)
                ):
                    issues.append(V2GuardIssue(
                        guard=self.GUARD_NAME,
                        severity="info",
                        message=(
                            f"String concatenation with += in loop "
                            f"(variable '{child.target.id}') — "
                            f"consider list + join"
                        ),
                        file=fname,
                        line=child.lineno,
                    ))
        return issues

    def _check_len_listcomp(self, fname: str, tree: ast.Module) -> list[V2GuardIssue]:
        """Detect len([x for x in ...]) — use sum(1 for ...) instead."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "len"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.ListComp)
            ):
                issues.append(V2GuardIssue(
                    guard=self.GUARD_NAME,
                    severity="info",
                    message=(
                        "len([x for x in ...]) — "
                        "use sum(1 for x in ...) to avoid "
                        "allocating a list"
                    ),
                    file=fname,
                    line=node.lineno,
                ))
        return issues

    def _check_global_mutation(self, fname: str, tree: ast.Module, content: str = "") -> list[V2GuardIssue]:
        """Detect assignment to module-level variable inside a function."""
        lines = content.splitlines() if content else []
        issues: list[V2GuardIssue] = []
        # Collect module-level names
        module_names: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_names.add(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    module_names.add(node.target.id)

        # Check functions for `global x` then assignment
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Check if the global statement line has an ignore marker
            has_ignore = False
            for child in ast.walk(node):
                if isinstance(child, ast.Global) and lines:
                    line_idx = child.lineno - 1
                    if 0 <= line_idx < len(lines) and _IGNORE_MARKER in lines[line_idx]:
                        has_ignore = True
            if has_ignore:
                continue
            declared_global: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Global):
                    declared_global.update(child.names)
            for name in declared_global:
                if name in module_names:
                    issues.append(V2GuardIssue(
                        guard=self.GUARD_NAME,
                        severity="warn",
                        message=(
                            f"Global state mutation: '{name}' "
                            f"modified inside function "
                            f"'{node.name}'"
                        ),
                        file=fname,
                        line=node.lineno,
                    ))
        return issues


def _call_name(node: ast.Call) -> str | None:
    """Extract dotted call name like 'cursor.execute' from a Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = [func.attr]
        obj = func.value
        while isinstance(obj, ast.Attribute):
            parts.append(obj.attr)
            obj = obj.value
        if isinstance(obj, ast.Name):
            parts.append(obj.id)
        return ".".join(reversed(parts))
    return None
