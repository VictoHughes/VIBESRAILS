"""Tests for DocstringGuard — real files, real AST parsing, no mocking."""

from pathlib import Path

import pytest

from vibesrails.guards_v2.docstring import DocstringGuard


@pytest.fixture
def guard():
    return DocstringGuard()


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write a Python file and return its path."""
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


def _scan(guard, tmp_path):
    """Scan project root."""
    return guard.scan(tmp_path)


def _msgs(issues):
    return [i.message for i in issues]


# ------------------------------------------------------------------
# Module docstring
# ------------------------------------------------------------------

class TestModuleDocstring:
    def test_missing_module_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        issues = _scan(guard, tmp_path)
        assert any("Module missing docstring" in m for m in _msgs(issues))

    def test_present_module_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""A module."""\nx = 1\n')
        issues = _scan(guard, tmp_path)
        assert not any("Module" in m for m in _msgs(issues))

    def test_empty_module_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""  """\nx = 1\n')
        issues = _scan(guard, tmp_path)
        assert any("Module has empty docstring" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Class docstring
# ------------------------------------------------------------------

class TestClassDocstring:
    def test_missing_class_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\nclass Foo:\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert any("Public class 'Foo' missing" in m for m in _msgs(issues))

    def test_present_class_docstring(self, guard, tmp_path):
        code = '"""Mod."""\nclass Foo:\n    """A class."""\n    pass\n'
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert not any("class" in m.lower() for m in _msgs(issues))

    def test_private_class_skipped(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\nclass _Internal:\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert not any("class" in m.lower() for m in _msgs(issues))

    def test_empty_class_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\nclass Foo:\n    """"""\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert any("empty docstring" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Function docstring
# ------------------------------------------------------------------

class TestFunctionDocstring:
    def test_missing_function_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\ndef greet(name):\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert any("'greet' missing" in m for m in _msgs(issues))

    def test_present_function_docstring(self, guard, tmp_path):
        code = '"""Mod."""\ndef greet(name):\n    """Say hi."""\n    pass\n'
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert not any("greet" in m for m in _msgs(issues))

    def test_private_function_skipped(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\ndef _helper():\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert not any("function" in m.lower() for m in _msgs(issues))

    def test_empty_function_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\ndef greet():\n    """"""\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert any("empty docstring" in m for m in _msgs(issues))

    def test_async_function_missing_docstring(self, guard, tmp_path):
        _write(tmp_path, "app.py", '"""Mod."""\nasync def fetch(url):\n    pass\n')
        issues = _scan(guard, tmp_path)
        assert any("'fetch' missing" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# Outdated docstring params
# ------------------------------------------------------------------

class TestOutdatedDocstring:
    def test_outdated_param_sphinx(self, guard, tmp_path):
        code = (
            '"""Mod."""\n'
            'def greet(name):\n'
            '    """\n'
            '    :param name: The name.\n'
            '    :param age: The age.\n'
            '    """\n'
            '    pass\n'
        )
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert any("age" in m for m in _msgs(issues))

    def test_outdated_param_google(self, guard, tmp_path):
        code = (
            '"""Mod."""\n'
            'def greet(name):\n'
            '    """Hello.\n\n'
            '    Args:\n'
            '        name: The name.\n'
            '        age: Gone param.\n'
            '    """\n'
            '    pass\n'
        )
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert any("age" in m for m in _msgs(issues))

    def test_no_false_positive_matching_params(self, guard, tmp_path):
        code = (
            '"""Mod."""\n'
            'def greet(name, age):\n'
            '    """\n'
            '    :param name: The name.\n'
            '    :param age: The age.\n'
            '    """\n'
            '    pass\n'
        )
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert not any("not in signature" in m for m in _msgs(issues))


# ------------------------------------------------------------------
# File exclusion (scan level)
# ------------------------------------------------------------------

class TestScanExclusion:
    def test_init_skipped(self, guard, tmp_path):
        _write(tmp_path, "__init__.py", "x = 1\n")
        issues = _scan(guard, tmp_path)
        files = {i.file for i in issues}
        assert str(tmp_path / "__init__.py") not in files

    def test_test_file_skipped(self, guard, tmp_path):
        _write(tmp_path, "test_foo.py", "x = 1\n")
        issues = _scan(guard, tmp_path)
        files = {i.file for i in issues}
        assert str(tmp_path / "test_foo.py") not in files

    def test_normal_file_scanned(self, guard, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        issues = _scan(guard, tmp_path)
        files = {i.file for i in issues}
        assert str(tmp_path / "app.py") in files

    def test_mixed_files(self, guard, tmp_path):
        _write(tmp_path, "__init__.py", "x = 1\n")
        _write(tmp_path, "test_foo.py", "x = 1\n")
        _write(tmp_path, "app.py", "x = 1\n")
        issues = _scan(guard, tmp_path)
        files = {i.file for i in issues}
        assert str(tmp_path / "__init__.py") not in files
        assert str(tmp_path / "test_foo.py") not in files
        assert str(tmp_path / "app.py") in files


# ------------------------------------------------------------------
# Syntax error handling
# ------------------------------------------------------------------

class TestSyntaxError:
    def test_syntax_error_returns_empty(self, guard, tmp_path):
        _write(tmp_path, "broken.py", "def (broken\n")
        issues = _scan(guard, tmp_path)
        assert issues == []


# ------------------------------------------------------------------
# Well-documented code should not trigger
# ------------------------------------------------------------------

class TestCleanCode:
    def test_fully_documented_no_issues(self, guard, tmp_path):
        code = (
            '"""A well-documented module."""\n'
            '\n'
            'def greet(name):\n'
            '    """Say hello.\n\n'
            '    :param name: The name to greet.\n'
            '    """\n'
            '    return f"Hello {name}"\n'
        )
        _write(tmp_path, "app.py", code)
        issues = _scan(guard, tmp_path)
        assert issues == []
