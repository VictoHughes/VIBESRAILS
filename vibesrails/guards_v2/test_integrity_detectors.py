"""Test Integrity Detectors — Individual detector methods."""

import ast
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD_NAME = "test-integrity"


def _is_test_func(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")


def _get_test_functions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Extract all test functions from a module."""
    funcs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if _is_test_func(node):
            funcs.append(node)  # type: ignore[arg-type]
    return funcs


def _func_uses_mock(func: ast.AST) -> bool:
    """Check if a function body references mocking constructs."""
    for node in ast.walk(func):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                src = ast.dump(dec)
                if "patch" in src.lower():
                    return True
        if isinstance(node, ast.Name):
            if node.id in (
                "MagicMock", "Mock", "monkeypatch",
                "mock", "mocker",
            ):
                return True
        if isinstance(node, ast.Attribute):
            if node.attr in ("patch", "MagicMock", "Mock"):
                return True
        if isinstance(node, ast.Call):
            func_node = node.func
            if isinstance(func_node, ast.Attribute):
                if func_node.attr == "patch":
                    return True
            if isinstance(func_node, ast.Name):
                if func_node.id in ("patch", "MagicMock", "Mock"):
                    return True
    return False


def _has_assertion(func: ast.AST) -> bool:
    """Check if a function contains any assertion."""
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Attribute):
            if node.attr == "raises":
                return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
                if name.startswith("assert"):
                    return True
    return False


def _is_trivial_assert(node: ast.Assert) -> bool:
    """Check if an assert is trivial (always passes)."""
    test = node.test
    if isinstance(test, ast.Constant):
        if test.value is True:
            return True
    if isinstance(test, ast.Compare):
        if (
            len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
        ):
            left = test.left
            right = test.comparators[0]
            if (
                isinstance(left, ast.Constant)
                and isinstance(right, ast.Constant)
                and left.value == right.value
            ):
                return True
    if isinstance(test, ast.Call):
        if (
            isinstance(test.func, ast.Name)
            and test.func.id == "isinstance"
            and len(test.args) == 2
        ):
            type_arg = test.args[1]
            if (
                isinstance(type_arg, ast.Name)
                and type_arg.id == "object"
            ):
                return True
    return False


def _extract_mock_return_values(func: ast.AST) -> set[object]:
    """Extract constant values assigned to mock return_value."""
    values: set[object] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "return_value"
                    and isinstance(node.value, ast.Constant)
                ):
                    values.add(node.value.value)
    return values


def _extract_assert_expected(func: ast.AST) -> set[object]:
    """Extract constant values from assert comparisons."""
    values: set[object] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            test = node.test
            if isinstance(test, ast.Compare):
                for comp in test.comparators:
                    if isinstance(comp, ast.Constant):
                        values.add(comp.value)
                if isinstance(test.left, ast.Constant):
                    values.add(test.left.value)
    return values


def _infer_source_package(test_filepath: Path) -> str | None:
    name = test_filepath.stem
    return name[5:] if name.startswith("test_") else None


def _file_imports_package(
    tree: ast.Module, package_name: str | None,
) -> bool:
    """Check if the file imports from a real source package."""
    if package_name is None:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if package_name in alias.name:
                    return True
        if isinstance(node, ast.ImportFrom):
            if node.module and package_name in node.module:
                return True
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == package_name:
                        return True
    return False


def count_mocks(tree: ast.Module) -> tuple[int, int]:
    """Return (mock_count, total_test_count)."""
    funcs = _get_test_functions(tree)
    total = len(funcs)
    mock_count = sum(1 for f in funcs if _func_uses_mock(f))
    return mock_count, total


def detect_sut_mocking(
    tree: ast.Module, test_filepath: Path,
) -> list[V2GuardIssue]:
    """Detect when tests mock the module they test."""
    module_name = _infer_source_package(test_filepath)
    if module_name is None:
        return []
    issues: list[V2GuardIssue] = []
    fname = str(test_filepath)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_patch = False
        if isinstance(func, ast.Attribute):
            if func.attr == "patch":
                is_patch = True
        if isinstance(func, ast.Name):
            if func.id == "patch":
                is_patch = True
        if not is_patch or not node.args:
            continue
        first_arg = node.args[0]
        if (
            isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
        ):
            target = first_arg.value
            parts = target.split(".")
            if module_name in parts:
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="block",
                    message=(
                        "Test mocks the code it's supposed"
                        " to test — this test proves"
                        f" nothing (patches {target})"
                    ),
                    file=fname,
                    line=node.lineno,
                ))
    return issues


def detect_assert_free(
    tree: ast.Module, filepath: str,
) -> list[V2GuardIssue]:
    """Detect test functions without assertions."""
    issues: list[V2GuardIssue] = []
    for func in _get_test_functions(tree):
        if not _has_assertion(func):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="block",
                message=(
                    "Test has no assertions — it can"
                    f" never fail ({func.name})"
                ),
                file=filepath,
                line=func.lineno,
            ))
    return issues


def detect_trivial_assertions(
    tree: ast.Module, filepath: str,
) -> list[V2GuardIssue]:
    """Detect trivial assertions that always pass."""
    issues: list[V2GuardIssue] = []
    for func in _get_test_functions(tree):
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Assert)
                and _is_trivial_assert(node)
            ):
                issues.append(V2GuardIssue(
                    guard=GUARD_NAME,
                    severity="warn",
                    message=(
                        "Trivial assertion — test doesn't"
                        " verify behavior"
                        f" ({func.name})"
                    ),
                    file=filepath,
                    line=node.lineno,
                ))
    return issues


def detect_mock_echo(
    tree: ast.Module, filepath: str,
) -> list[V2GuardIssue]:
    """Detect mock return_value == asserted value."""
    issues: list[V2GuardIssue] = []
    for func in _get_test_functions(tree):
        rv = _extract_mock_return_values(func)
        ev = _extract_assert_expected(func)
        overlap = rv & ev
        overlap.discard(None)
        if overlap:
            sample = next(iter(overlap))
            issues.append(V2GuardIssue(
                guard=GUARD_NAME,
                severity="warn",
                message=(
                    "Test just checks that mock returns"
                    " what you told it to return"
                    f" ({func.name}, value={sample!r})"
                ),
                file=filepath,
                line=func.lineno,
            ))
    return issues


def detect_missing_imports(
    tree: ast.Module, filepath: Path,
) -> list[V2GuardIssue]:
    """Detect test files that don't import source code."""
    module_name = _infer_source_package(filepath)
    if not _file_imports_package(tree, module_name):
        return [V2GuardIssue(
            guard=GUARD_NAME,
            severity="warn",
            message=(
                "Test file doesn't import the code"
                " it should test"
            ),
            file=str(filepath),
        )]
    return []
