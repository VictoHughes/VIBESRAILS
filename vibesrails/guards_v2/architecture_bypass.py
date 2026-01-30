"""AI Bypass Detection — AST-based detection of architecture circumvention."""

import ast
import logging
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

GUARD = "ArchitectureDriftGuard"


def _all_layer_dirs() -> set[str]:
    """All directory names that map to a layer."""
    from .architecture_drift import _all_layer_dirs as _impl
    return _impl()


def _has_all_assignment(stmts: list[ast.stmt]) -> bool:
    """Check if any statement assigns to __all__."""
    for node in stmts:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                return True
    return False


def _check_reexport_file(tree: ast.Module) -> tuple[bool, int, int]:
    """Check if a module is a re-export module. Returns (is_reexport, imports, total)."""
    stmts = tree.body
    if not stmts:
        return False, 0, 0
    imports = sum(1 for n in stmts if isinstance(n, (ast.Import, ast.ImportFrom)))
    total = len([
        s for s in stmts
        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
    ])
    is_reexport = total >= 2 and imports > 0 and (imports / total) >= 0.8 and _has_all_assignment(stmts)
    return is_reexport, imports, total


def detect_reexport_modules(
    guard: object, project_root: Path,
) -> list[V2GuardIssue]:
    """Detect modules that only re-export symbols."""
    issues: list[V2GuardIssue] = []
    for py_file in guard._iter_py_files(project_root):  # type: ignore[attr-defined]
        tree = guard._parse_file(py_file)  # type: ignore[attr-defined]
        if tree is None:
            continue
        is_reexport, imports, total = _check_reexport_file(tree)
        if is_reexport:
            issues.append(V2GuardIssue(
                guard=GUARD,
                severity="warn",
                message=(
                    "Re-export module detected: "
                    f"{imports}/{total} statements "
                    "are imports with __all__"
                ),
                file=str(py_file),
            ))
    return issues


def _check_wrapper_class(node: ast.ClassDef) -> bool:
    """Check if a class delegates all its methods."""
    methods = [
        n for n in node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name != "__init__"
    ]
    if len(methods) < 2:
        return False
    return all(_is_delegating(m) for m in methods)


def detect_wrapper_classes(
    guard: object, project_root: Path,
) -> list[V2GuardIssue]:
    """Detect classes that delegate all methods."""
    issues: list[V2GuardIssue] = []
    for py_file in guard._iter_py_files(project_root):  # type: ignore[attr-defined]
        tree = guard._parse_file(py_file)  # type: ignore[attr-defined]
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if _check_wrapper_class(node):
                issues.append(V2GuardIssue(
                    guard=GUARD, severity="warn",
                    message=f"Wrapper class '{node.name}' delegates all methods",
                    file=str(py_file), line=node.lineno,
                ))
    return issues


def _is_delegating(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Check if a method just delegates to self._inner."""
    body = func.body
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Return) and stmt.value:
        return _is_inner_call(stmt.value)
    if isinstance(stmt, ast.Expr):
        return _is_inner_call(stmt.value)
    return False


def _is_inner_call(node: ast.expr) -> bool:
    """Check if expression is self._inner.method()."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    value = func.value
    if not isinstance(value, ast.Attribute):
        return False
    if not isinstance(value.value, ast.Name):
        return False
    return (
        value.value.id == "self"
        and value.attr.startswith("_")
    )


def _find_layer_imports_in_func(
    func_node: ast.AST, layer_dirs: set[str], py_file: Path,
) -> list[V2GuardIssue]:
    """Find layer imports inside a function node."""
    issues: list[V2GuardIssue] = []
    for child in ast.walk(func_node):
        if not isinstance(child, ast.ImportFrom):
            continue
        mod = child.module or ""
        top = mod.split(".")[0]
        if top in layer_dirs:
            issues.append(V2GuardIssue(
                guard=GUARD, severity="warn",
                message=f"Function-level import of '{mod}'",
                file=str(py_file), line=child.lineno,
            ))
    return issues


def detect_function_level_imports(
    guard: object, project_root: Path,
) -> list[V2GuardIssue]:
    """Detect imports inside functions."""
    issues: list[V2GuardIssue] = []
    layer_dirs = _all_layer_dirs()
    for py_file in guard._iter_py_files(project_root):  # type: ignore[attr-defined]
        tree = guard._parse_file(py_file)  # type: ignore[attr-defined]
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues.extend(_find_layer_imports_in_func(node, layer_dirs, py_file))
    return issues


def _is_type_checking_block(node: ast.If) -> bool:
    """Check if an If node is a TYPE_CHECKING guard."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def _collect_layer_imports(node: ast.AST, layer_dirs: set[str], py_file: Path) -> list[V2GuardIssue]:
    """Collect issues for layer imports inside a node."""
    issues: list[V2GuardIssue] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.ImportFrom):
            continue
        mod = child.module or ""
        top = mod.split(".")[0]
        if top in layer_dirs:
            issues.append(V2GuardIssue(
                guard=GUARD,
                severity="warn",
                message=f"TYPE_CHECKING import of '{mod}'",
                file=str(py_file),
                line=child.lineno,
            ))
    return issues


def detect_type_checking_bypass(
    guard: object, project_root: Path,
) -> list[V2GuardIssue]:
    """Detect imports in TYPE_CHECKING blocks."""
    issues: list[V2GuardIssue] = []
    layer_dirs = _all_layer_dirs()
    for py_file in guard._iter_py_files(project_root):  # type: ignore[attr-defined]
        tree = guard._parse_file(py_file)  # type: ignore[attr-defined]
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and _is_type_checking_block(node):
                issues.extend(_collect_layer_imports(node, layer_dirs, py_file))
    return issues
