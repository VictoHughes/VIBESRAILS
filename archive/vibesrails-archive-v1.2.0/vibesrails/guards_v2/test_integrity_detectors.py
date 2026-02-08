"""Test Integrity Detectors — Individual detector methods."""

import ast
import logging
from pathlib import Path

from .dependency_audit import V2GuardIssue

logger = logging.getLogger(__name__)

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


_MOCK_NAMES = {"MagicMock", "Mock", "monkeypatch", "mock", "mocker"}
_MOCK_ATTRS = {"patch", "MagicMock", "Mock"}
_MOCK_CALL_NAMES = {"patch", "MagicMock", "Mock"}


def _is_mock_call(node: ast.Call) -> bool:
    """Check if a Call node is a mock construct."""
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr == "patch":
        return True
    return isinstance(f, ast.Name) and f.id in _MOCK_CALL_NAMES


def _node_is_mock(node: ast.AST) -> bool:
    """Check if a single AST node references a mock construct."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return any("patch" in ast.dump(dec).lower() for dec in node.decorator_list)
    if isinstance(node, ast.Name):
        return node.id in _MOCK_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr in _MOCK_ATTRS
    return isinstance(node, ast.Call) and _is_mock_call(node)


def _func_uses_mock(func: ast.AST) -> bool:
    """Check if a function body references mocking constructs."""
    return any(_node_is_mock(node) for node in ast.walk(func))


def _is_assertion_node(node: ast.AST) -> bool:
    """Check if a single node represents an assertion."""
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Attribute) and node.attr == "raises":
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr.startswith("assert")
    return False


def _has_assertion(func: ast.AST) -> bool:
    """Check if a function contains any assertion."""
    return any(_is_assertion_node(node) for node in ast.walk(func))


def _is_trivial_constant(test: ast.AST) -> bool:
    """Check if test is `assert True`."""
    return isinstance(test, ast.Constant) and test.value is True


def _is_trivial_compare(test: ast.AST) -> bool:
    """Check if test is `assert X == X` with same constants."""
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]
    return (
        isinstance(left, ast.Constant)
        and isinstance(right, ast.Constant)
        and left.value == right.value
    )


def _is_trivial_isinstance(test: ast.AST) -> bool:
    """Check if test is `assert isinstance(x, object)`."""
    if not isinstance(test, ast.Call):
        return False
    if not (isinstance(test.func, ast.Name) and test.func.id == "isinstance"):
        return False
    if len(test.args) != 2:
        return False
    return isinstance(test.args[1], ast.Name) and test.args[1].id == "object"


def _is_trivial_assert(node: ast.Assert) -> bool:
    """Check if an assert is trivial (always passes)."""
    test = node.test
    return _is_trivial_constant(test) or _is_trivial_compare(test) or _is_trivial_isinstance(test)


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


def _extract_compare_constants(compare: ast.Compare) -> set[object]:
    """Extract constant values from a Compare node."""
    values: set[object] = set()
    for comp in compare.comparators:
        if isinstance(comp, ast.Constant):
            values.add(comp.value)
    if isinstance(compare.left, ast.Constant):
        values.add(compare.left.value)
    return values


def _extract_assert_expected(func: ast.AST) -> set[object]:
    """Extract constant values from assert comparisons."""
    values: set[object] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            values.update(_extract_compare_constants(node.test))
    return values


def _infer_source_package(test_filepath: Path) -> str | None:
    name = test_filepath.stem
    return name[5:] if name.startswith("test_") else None


def _import_mentions_package(node: ast.AST, package_name: str) -> bool:
    """Check if an import node mentions the given package."""
    if isinstance(node, ast.Import):
        return any(package_name in alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        if node.module and package_name in node.module:
            return True
        return any(alias.name == package_name for alias in node.names)
    return False


def _file_imports_package(
    tree: ast.Module, package_name: str | None,
) -> bool:
    """Check if the file imports from a real source package."""
    if package_name is None:
        return True
    return any(
        _import_mentions_package(node, package_name)
        for node in ast.walk(tree)
    )


def count_mocks(tree: ast.Module) -> tuple[int, int]:
    """Return (mock_count, total_test_count)."""
    funcs = _get_test_functions(tree)
    total = len(funcs)
    mock_count = sum(1 for f in funcs if _func_uses_mock(f))
    return mock_count, total


def _is_patch_call(node: ast.Call) -> bool:
    """Check if a Call node is a patch() call."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "patch":
        return True
    return isinstance(func, ast.Name) and func.id == "patch"


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
        if not isinstance(node, ast.Call) or not _is_patch_call(node):
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if not (isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)):
            continue
        target = first_arg.value
        if module_name in target.split("."):
            issues.append(V2GuardIssue(
                guard=GUARD_NAME, severity="block",
                message=f"Test mocks the code it's supposed to test — this test proves nothing (patches {target})",
                file=fname, line=node.lineno,
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
