"""AI Bypass Detection — AST-based detection of architecture circumvention."""

import ast
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD = "ArchitectureDriftGuard"


def _all_layer_dirs() -> set[str]:
    """All directory names that map to a layer."""
    from .architecture_drift import _all_layer_dirs as _impl
    return _impl()


def detect_reexport_modules(
    guard: object, project_root: Path,
) -> list[V2GuardIssue]:
    """Detect modules that only re-export symbols."""
    issues: list[V2GuardIssue] = []
    for py_file in guard._iter_py_files(project_root):  # type: ignore[attr-defined]
        tree = guard._parse_file(py_file)  # type: ignore[attr-defined]
        if tree is None:
            continue
        stmts = tree.body
        if len(stmts) < 1:
            continue
        imports = 0
        has_all = False
        for node in stmts:
            if isinstance(
                node, (ast.Import, ast.ImportFrom)
            ):
                imports += 1
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "__all__"
                    ):
                        has_all = True
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Constant):
                    continue  # docstring
        total = len([
            s for s in stmts
            if not (
                isinstance(s, ast.Expr)
                and isinstance(s.value, ast.Constant)
            )
        ])
        if total >= 2 and imports > 0:
            ratio = imports / total
            if ratio >= 0.8 and has_all:
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
            methods = [
                n for n in node.body
                if isinstance(n, (ast.FunctionDef,
                                  ast.AsyncFunctionDef))
                and n.name != "__init__"
            ]
            if len(methods) < 2:
                continue
            delegating = 0
            for method in methods:
                if _is_delegating(method):
                    delegating += 1
            if delegating == len(methods):
                issues.append(V2GuardIssue(
                    guard=GUARD,
                    severity="warn",
                    message=(
                        f"Wrapper class '{node.name}' "
                        "delegates all methods"
                    ),
                    file=str(py_file),
                    line=node.lineno,
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
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom):
                    mod = child.module or ""
                    top = mod.split(".")[0]
                    if top in layer_dirs:
                        issues.append(V2GuardIssue(
                            guard=GUARD,
                            severity="warn",
                            message=(
                                "Function-level import "
                                f"of '{mod}'"
                            ),
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
            if not isinstance(node, ast.If):
                continue
            test = node.test
            is_tc = False
            if (
                isinstance(test, ast.Name)
                and test.id == "TYPE_CHECKING"
            ):
                is_tc = True
            elif (
                isinstance(test, ast.Attribute)
                and test.attr == "TYPE_CHECKING"
            ):
                is_tc = True
            if not is_tc:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.ImportFrom):
                    mod = child.module or ""
                    top = mod.split(".")[0]
                    if top in layer_dirs:
                        issues.append(V2GuardIssue(
                            guard=GUARD,
                            severity="warn",
                            message=(
                                "TYPE_CHECKING import "
                                f"of '{mod}'"
                            ),
                            file=str(py_file),
                            line=child.lineno,
                        ))
    return issues
