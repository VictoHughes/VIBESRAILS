"""Tests for TypeSafetyGuard — real files, real AST parsing.

Only subprocess (mypy) is mocked as external.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from vibesrails.guards_v2.type_safety import TypeSafetyGuard, _is_excluded


@pytest.fixture
def guard():
    return TypeSafetyGuard()


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write a Python file and return its path."""
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


def _scan(guard, tmp_path):
    """Scan with mypy subprocess disabled (external tool not available)."""
    with patch("subprocess.run",
               side_effect=FileNotFoundError):
        return guard.scan(tmp_path)


def _msgs(issues):
    return [i.message for i in issues]


# ------------------------------------------------------------------
# Missing return types
# ------------------------------------------------------------------

class TestMissingReturnType:
    def test_no_return_type(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "def hello(x: int):\n    return x\n")
        issues = _scan(guard, tmp_path)
        assert any("return type" in m for m in _msgs(issues))

    def test_return_type_present_ok(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "def hello(x: int) -> int:\n    return x\n")
        issues = _scan(guard, tmp_path)
        ret = [m for m in _msgs(issues) if "return type" in m]
        assert ret == []

    def test_async_function_no_return_type(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "async def fetch(url: str):\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert any("return type" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Missing param types
# ------------------------------------------------------------------

class TestMissingParamType:
    def test_param_without_type(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "def greet(name) -> None:\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert any("'name'" in m for m in _msgs(issues))

    def test_self_cls_skipped(self, guard, tmp_path):
        code = (
            "class C:\n"
            "    def method(self, x: int) -> None:\n"
            "        pass\n"
            "    @classmethod\n"
            "    def create(cls, y: int) -> None:\n"
            "        pass\n"
        )
        _write(tmp_path, "mod.py", code)
        issues = _scan(guard, tmp_path)
        param_issues = [m for m in _msgs(issues) if "Parameter" in m]
        assert param_issues == []

    def test_async_param_without_type(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "async def fetch(url):\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert any("'url'" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Private functions skipped
# ------------------------------------------------------------------

class TestPrivateSkipped:
    def test_private_function_skipped(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "def _internal(x):\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert issues == []

    def test_dunder_method_skipped(self, guard, tmp_path):
        code = "class C:\n    def __init__(self, x):\n        self.x = x\n"
        _write(tmp_path, "mod.py", code)
        issues = _scan(guard, tmp_path)
        # __init__ starts with _ so should be skipped
        func_issues = [m for m in _msgs(issues) if "function" in m.lower()]
        assert func_issues == []


# ------------------------------------------------------------------
# Explicit Any usage
# ------------------------------------------------------------------

class TestExplicitAny:
    def test_any_name(self, guard, tmp_path):
        code = "from typing import Any\ndef f(x: Any) -> Any:\n    pass\n"
        _write(tmp_path, "mod.py", code)
        issues = _scan(guard, tmp_path)
        any_issues = [m for m in _msgs(issues) if "Any" in m]
        assert len(any_issues) >= 2

    def test_any_attribute(self, guard, tmp_path):
        code = "import typing\ndef f(x: typing.Any) -> typing.Any:\n    pass\n"
        _write(tmp_path, "mod.py", code)
        issues = _scan(guard, tmp_path)
        any_issues = [m for m in _msgs(issues) if "Any" in m]
        assert len(any_issues) >= 2


# ------------------------------------------------------------------
# Bare type: ignore
# ------------------------------------------------------------------

class TestBareTypeIgnore:
    def test_bare_type_ignore_detected(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "x = 1  # type: ignore\n")
        issues = _scan(guard, tmp_path)
        assert any("type: ignore" in m for m in _msgs(issues))

    def test_type_ignore_with_code_ok(self, guard, tmp_path):
        _write(tmp_path, "mod.py", "x = 1  # type: ignore[assignment]\n")
        issues = _scan(guard, tmp_path)
        ignore = [m for m in _msgs(issues) if "type: ignore" in m]
        assert ignore == []


# ------------------------------------------------------------------
# File exclusion
# ------------------------------------------------------------------

class TestExclusion:
    def test_init_excluded(self, guard, tmp_path):
        _write(tmp_path, "__init__.py", "def run(x):\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert issues == []

    def test_test_file_excluded(self, guard, tmp_path):
        _write(tmp_path, "test_foo.py", "def run(x):\n    pass\n")
        issues = _scan(guard, tmp_path)
        assert issues == []

    def test_is_excluded_helper(self):
        assert _is_excluded(Path("tests/test_foo.py"))
        assert _is_excluded(Path("src/__init__.py"))
        assert not _is_excluded(Path("src/main.py"))

    def test_scan_only_scans_real_code(self, guard, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        _write(src, "app.py", "def run(x):\n    pass\n")
        _write(src, "__init__.py", "")
        _write(src, "test_skip.py", "def test_it():\n    pass\n")
        with patch("subprocess.run",
                   side_effect=FileNotFoundError):
            issues = guard.scan(tmp_path)
        files = {i.file for i in issues}
        assert str(src / "app.py") in files
        assert str(src / "__init__.py") not in files
        assert str(src / "test_skip.py") not in files


# ------------------------------------------------------------------
# Syntax error handling
# ------------------------------------------------------------------

class TestSyntaxError:
    def test_syntax_error_returns_empty(self, guard, tmp_path):
        _write(tmp_path, "broken.py", "def (\n")
        issues = _scan(guard, tmp_path)
        assert issues == []


# ------------------------------------------------------------------
# Fully typed code should not trigger
# ------------------------------------------------------------------

class TestCleanCode:
    def test_fully_typed_no_issues(self, guard, tmp_path):
        code = (
            "def greet(name: str, age: int) -> str:\n"
            "    return f'Hello {name}, {age}'\n"
        )
        _write(tmp_path, "mod.py", code)
        issues = _scan(guard, tmp_path)
        assert issues == []
