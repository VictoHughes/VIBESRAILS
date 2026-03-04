"""Tests for architecture_bypass.py — pure AST helper functions."""

import ast

from vibesrails.guards_v2.architecture_bypass import (
    _check_reexport_file,
    _check_wrapper_class,
    _has_all_assignment,
    _is_delegating,
    _is_inner_call,
    _is_type_checking_block,
)


def _parse(code: str) -> ast.Module:
    return ast.parse(code)


# ── _has_all_assignment ──────────────────────────────────


def test_has_all_assignment_present():
    tree = _parse('__all__ = ["foo", "bar"]\n')
    assert _has_all_assignment(tree.body) is True


def test_has_all_assignment_absent():
    tree = _parse("x = 1\ny = 2\n")
    assert _has_all_assignment(tree.body) is False


def test_has_all_assignment_empty():
    assert _has_all_assignment([]) is False


# ── _check_reexport_file ─────────────────────────────────


def test_reexport_file_detected():
    # Need imports/total >= 0.8 and __all__ present
    # 4 imports + 1 __all__ = 5 stmts, 4/5 = 0.8
    code = (
        "from .foo import Foo\n"
        "from .bar import Bar\n"
        "from .baz import Baz\n"
        "from .qux import Qux\n"
        '__all__ = ["Foo", "Bar", "Baz", "Qux"]\n'
    )
    tree = _parse(code)
    is_reexport, imports, total = _check_reexport_file(tree)
    assert is_reexport is True
    assert imports == 4
    assert total == 5


def test_reexport_file_not_detected_no_all():
    code = "from .foo import Foo\nfrom .bar import Bar\n"
    tree = _parse(code)
    is_reexport, _, _ = _check_reexport_file(tree)
    assert is_reexport is False


def test_reexport_file_empty():
    tree = _parse("")
    is_reexport, imports, total = _check_reexport_file(tree)
    assert is_reexport is False
    assert imports == 0
    assert total == 0


def test_reexport_file_mostly_code():
    code = (
        "from .foo import Foo\n"
        "x = 1\ny = 2\nz = 3\n"
        '__all__ = ["Foo"]\n'
    )
    tree = _parse(code)
    is_reexport, _, _ = _check_reexport_file(tree)
    # 1 import out of 5 statements = 20% < 80% threshold
    assert is_reexport is False


# ── _check_wrapper_class ─────────────────────────────────


def test_wrapper_class_detected():
    code = (
        "class Wrapper:\n"
        "    def __init__(self): self._inner = None\n"
        "    def foo(self): return self._inner.foo()\n"
        "    def bar(self): return self._inner.bar()\n"
    )
    tree = _parse(code)
    cls_node = tree.body[0]
    assert _check_wrapper_class(cls_node) is True


def test_wrapper_class_not_detected_real_logic():
    code = (
        "class Service:\n"
        "    def __init__(self): pass\n"
        "    def foo(self): return 42\n"
        "    def bar(self): return 'hello'\n"
    )
    tree = _parse(code)
    cls_node = tree.body[0]
    assert _check_wrapper_class(cls_node) is False


def test_wrapper_class_too_few_methods():
    code = (
        "class Small:\n"
        "    def __init__(self): pass\n"
        "    def foo(self): return self._inner.foo()\n"
    )
    tree = _parse(code)
    cls_node = tree.body[0]
    # Only 1 non-init method, needs >= 2
    assert _check_wrapper_class(cls_node) is False


# ── _is_delegating ───────────────────────────────────────


def test_is_delegating_return_inner_call():
    code = "class C:\n    def foo(self): return self._inner.foo()\n"
    tree = _parse(code)
    method = tree.body[0].body[0]
    assert _is_delegating(method) is True


def test_is_delegating_expr_inner_call():
    code = "class C:\n    def foo(self): self._inner.foo()\n"
    tree = _parse(code)
    method = tree.body[0].body[0]
    assert _is_delegating(method) is True


def test_is_delegating_real_logic():
    code = "class C:\n    def foo(self): return 42\n"
    tree = _parse(code)
    method = tree.body[0].body[0]
    assert _is_delegating(method) is False


def test_is_delegating_multi_statement():
    code = "class C:\n    def foo(self):\n        x = 1\n        return x\n"
    tree = _parse(code)
    method = tree.body[0].body[0]
    assert _is_delegating(method) is False


# ── _is_inner_call ───────────────────────────────────────


def test_is_inner_call_valid():
    code = "self._inner.method()"
    tree = _parse(code)
    expr = tree.body[0].value
    assert _is_inner_call(expr) is True


def test_is_inner_call_not_self():
    code = "other._inner.method()"
    tree = _parse(code)
    expr = tree.body[0].value
    assert _is_inner_call(expr) is False


def test_is_inner_call_not_private():
    code = "self.public.method()"
    tree = _parse(code)
    expr = tree.body[0].value
    assert _is_inner_call(expr) is False


def test_is_inner_call_not_a_call():
    code = "self._inner.attr"
    tree = _parse(code)
    expr = tree.body[0].value
    assert _is_inner_call(expr) is False


# ── _is_type_checking_block ──────────────────────────────


def test_type_checking_block_name():
    code = "if TYPE_CHECKING:\n    import foo\n"
    tree = _parse(code)
    if_node = tree.body[0]
    assert _is_type_checking_block(if_node) is True


def test_type_checking_block_attribute():
    code = "if typing.TYPE_CHECKING:\n    import foo\n"
    tree = _parse(code)
    if_node = tree.body[0]
    assert _is_type_checking_block(if_node) is True


def test_type_checking_block_regular_if():
    code = "if True:\n    pass\n"
    tree = _parse(code)
    if_node = tree.body[0]
    assert _is_type_checking_block(if_node) is False
