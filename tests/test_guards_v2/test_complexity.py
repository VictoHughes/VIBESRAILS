"""Tests for ComplexityGuard — real files, real AST parsing, no mocks."""

import textwrap
from pathlib import Path

import pytest

from vibesrails.guards_v2.complexity import (
    ComplexityGuard,
)


@pytest.fixture
def guard():
    return ComplexityGuard()


def _write(tmp_path: Path, code: str, name: str = "mod.py") -> Path:
    f = tmp_path / name
    f.write_text(textwrap.dedent(code))
    return f


# ── Cyclomatic complexity (real AST) ─────────────────────────────


def test_cyclomatic_simple(guard):
    code = "def f(): pass"
    issues = guard.scan_file(Path("t.py"), code)
    assert not any("cyclomatic" in i.message for i in issues)


def test_cyclomatic_high_triggers_warn(guard, tmp_path):
    """A function with many if/elif branches exceeds CYCLOMATIC_WARN."""
    branches = "\n".join(
        f"    elif x == {i}:\n        pass" for i in range(1, 14)
    )
    code = f"def big(x):\n    if x == 0:\n        pass\n{branches}\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("cyclomatic" in i.message for i in issues)


# ── Cognitive complexity (real AST) ──────────────────────────────


def test_cognitive_simple_no_issue(guard):
    code = "def f(x):\n    if x:\n        pass\n"
    issues = guard.scan_file(Path("t.py"), code)
    assert not any("cognitive" in i.message for i in issues)


def test_cognitive_deep_nesting_triggers(guard, tmp_path):
    """Deeply nested code should trigger cognitive complexity warning."""
    code = """\
def deep(a, b, c, d, e):
    if a:
        for x in b:
            if c:
                while d:
                    if e:
                        for y in range(10):
                            if y > 5:
                                pass  # intentional nesting for complexity test
"""
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("cognitive" in i.message for i in issues)


# ── Nesting depth (real files) ───────────────────────────────────


def test_nesting_flat_no_issue(guard, tmp_path):
    _write(tmp_path, "def f():\n    x = 1\n    return x\n")
    issues = guard.scan(tmp_path)
    assert not any("nesting" in i.message.lower() for i in issues)


def test_nesting_6_levels_triggers(guard, tmp_path):
    code = """\
def deeply_nested(a):
    if a:
        for x in range(10):
            while True:
                try:
                    if x > 5:
                        with open("f") as fh:
                            pass  # deep nesting fixture
                except Exception:
                    pass  # deep nesting fixture
"""
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("nesting" in i.message.lower() for i in issues)


# ── Parameter count (real AST) ───────────────────────────────────


def test_few_params_no_issue(guard, tmp_path):
    _write(tmp_path, "def f(a, b, c): pass\n")
    issues = guard.scan(tmp_path)
    assert not any("params" in i.message for i in issues)


def test_many_params_warn(guard, tmp_path):
    params = ", ".join(f"p{i}" for i in range(7))
    _write(tmp_path, f"def f({params}): pass\n")
    issues = guard.scan(tmp_path)
    assert any("params" in i.message and i.severity == "warn" for i in issues)


def test_too_many_params_block(guard, tmp_path):
    params = ", ".join(f"p{i}" for i in range(10))
    _write(tmp_path, f"def f({params}): pass\n")
    issues = guard.scan(tmp_path)
    assert any("params" in i.message and i.severity == "block" for i in issues)


def test_self_excluded_from_count(guard):
    code = "def f(self, a, b): pass\n"
    issues = guard.scan_file(Path("t.py"), code)
    assert not any("params" in i.message for i in issues)


def test_cls_excluded_from_count(guard):
    code = "def f(cls, a, b): pass\n"
    issues = guard.scan_file(Path("t.py"), code)
    assert not any("params" in i.message for i in issues)


# ── Function length (real files) ─────────────────────────────────


def test_short_function_no_issue(guard, tmp_path):
    _write(tmp_path, "def f():\n    return 1\n")
    issues = guard.scan(tmp_path)
    assert not any("lines" in i.message for i in issues)


def test_long_function_triggers_warn(guard, tmp_path):
    body = "\n".join(f"    x{i} = {i}" for i in range(60))
    code = f"def long_func():\n{body}\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("lines" in i.message for i in issues)


# ── Return count (real files) ────────────────────────────────────


def test_few_returns_no_issue(guard, tmp_path):
    code = "def f(x):\n    if x > 0:\n        return 1\n    return 0\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert not any("returns" in i.message for i in issues)


def test_many_returns_triggers_warn(guard, tmp_path):
    branches = "\n".join(
        f"    if x == {i}:\n        return {i}" for i in range(7)
    )
    code = f"def many_returns(x):\n{branches}\n    return -1\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("returns" in i.message for i in issues)


# ── Clean function passes (real file) ────────────────────────────


def test_clean_function_no_issues(guard, tmp_path):
    code = "def greet(name):\n    return f'Hello {name}'\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert issues == []


# ── scan_file with syntax error ──────────────────────────────────


def test_syntax_error_returns_empty(guard):
    issues = guard.scan_file(Path("bad.py"), "def (broken")
    assert issues == []


# ── scan directory integration ───────────────────────────────────


def test_scan_directory_multiple_files(guard, tmp_path):
    _write(tmp_path, "def ok(): return 1\n", name="good.py")
    params = ", ".join(f"p{i}" for i in range(10))
    _write(tmp_path, f"def bad({params}): pass\n", name="bad.py")
    issues = guard.scan(tmp_path)
    assert any("params" in i.message for i in issues)
    bad_files = [i.file for i in issues if "params" in i.message]
    assert any("bad.py" in f for f in bad_files)
