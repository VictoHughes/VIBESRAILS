"""Docstring Guard — Detects missing, empty, or outdated docstrings."""

import ast
import logging
import re
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD_NAME = "docstring"


class DocstringGuard:
    """Detects docstring issues using AST analysis."""

    def scan_file(
        self, filepath: Path, content: str
    ) -> list[V2GuardIssue]:
        """Scan a single file for docstring issues."""
        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError:
            return []

        issues: list[V2GuardIssue] = []
        fname = str(filepath)

        issues.extend(self._check_module_docstring(tree, fname))
        issues.extend(self._check_classes(tree, fname))
        issues.extend(self._check_functions(tree, fname))

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
        return issues

    # ----------------------------------------------------------
    # Internal checks
    # ----------------------------------------------------------

    def _check_module_docstring(
        self, tree: ast.Module, fname: str
    ) -> list[V2GuardIssue]:
        """Check for missing or empty module-level docstring."""
        doc = ast.get_docstring(tree)
        if doc is None:
            return [V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message="Module missing docstring",
                file=fname,
                line=1,
            )]
        if _is_empty_docstring(doc):
            return [V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message="Module has empty docstring",
                file=fname,
                line=1,
            )]
        return []

    def _check_classes(
        self, tree: ast.Module, fname: str
    ) -> list[V2GuardIssue]:
        """Check public classes for missing/empty docstrings."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name.startswith("_"):
                continue
            doc = ast.get_docstring(node)
            if doc is None:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"Public class '{node.name}' missing"
                            " docstring",
                    file=fname,
                    line=node.lineno,
                ))
            elif _is_empty_docstring(doc):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"Public class '{node.name}' has"
                            " empty docstring",
                    file=fname,
                    line=node.lineno,
                ))
        return issues

    def _check_functions(
        self, tree: ast.Module, fname: str
    ) -> list[V2GuardIssue]:
        """Check public functions/methods for docstring issues."""
        issues: list[V2GuardIssue] = []
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                continue
            if node.name.startswith("_"):
                continue

            doc = ast.get_docstring(node)
            if doc is None:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"Public function '{node.name}'"
                            " missing docstring",
                    file=fname,
                    line=node.lineno,
                ))
                continue

            if _is_empty_docstring(doc):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=f"Public function '{node.name}'"
                            " has empty docstring",
                    file=fname,
                    line=node.lineno,
                ))
                continue

            issues.extend(
                self._check_outdated_params(node, doc, fname)
            )

        return issues

    def _check_outdated_params(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        doc: str,
        fname: str,
    ) -> list[V2GuardIssue]:
        """Detect param names in docstring not in signature."""
        sig_params = _get_signature_params(node)
        doc_params = _extract_doc_params(doc)
        stale = doc_params - sig_params
        if not stale:
            return []
        names = ", ".join(sorted(stale))
        return [V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message=f"Function '{node.name}' docstring mentions"
                    f" params not in signature: {names}",
            file=fname,
            line=node.lineno,
        )]


# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------

def _is_empty_docstring(doc: str) -> bool:
    """Return True if a docstring is effectively empty."""
    return doc.strip() == ""


def _get_signature_params(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    """Extract parameter names from a function AST node."""
    params: set[str] = set()
    args = node.args
    for arg in (
        args.args + args.posonlyargs + args.kwonlyargs
    ):
        if arg.arg != "self" and arg.arg != "cls":
            params.add(arg.arg)
    if args.vararg:
        params.add(args.vararg.arg)
    if args.kwarg:
        params.add(args.kwarg.arg)
    return params


_PARAM_PATTERN = re.compile(
    r"""
    (?:                     # match these docstring styles:
      :param\s+(\w+)        # Sphinx  — :param name:
    | @param\s+(\w+)        # Javadoc — @param name
    | (\w+)\s*[\(:]         # Google/Numpy — name: or name (type):
    )
    """,
    re.VERBOSE,
)


_PARAM_PATTERNS = [
    re.compile(r":param\s+(\w+)"),
    re.compile(r"@param\s+(\w+)"),
    re.compile(r"(\w+)\s*\(.*?\)\s*:"),
    re.compile(r"(\w+)\s*:"),
]


def _extract_doc_params(doc: str) -> set[str]:
    """Extract parameter names referenced in a docstring."""
    params: set[str] = set()
    for line in doc.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in _PARAM_PATTERNS:
            m = pattern.match(stripped)
            if m:
                word = m.group(1)
                if word not in _NON_PARAM_WORDS:
                    params.add(word)
                break
    return params


_NON_PARAM_WORDS = frozenset({
    "Args", "Arguments", "Parameters", "Returns", "Return",
    "Raises", "Yields", "Yield", "Note", "Notes",
    "Example", "Examples", "See", "References", "Todo",
    "Attributes", "Warning", "Warnings", "Deprecated",
    "Type", "Types",
})


_EXCLUDED_DIRS = frozenset({
    "venv", ".venv", "node_modules", "site-packages",
    "__pycache__", "tests", "test",
})


def _is_excluded(path: Path) -> bool:
    """Skip test files, __init__.py, venvs, hidden dirs."""
    if path.name == "__init__.py":
        return True
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True
    return any(
        part.startswith(".") or part in _EXCLUDED_DIRS
        for part in path.parts
    )
