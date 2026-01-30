"""Tests for DeadCodeGuard — real files, real filesystem, no mocking except subprocess."""

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from vibesrails.guards_v2.dead_code import DeadCodeGuard


@pytest.fixture
def guard():
    return DeadCodeGuard()


# ── Unused imports (real files) ──────────────────────────────


def test_unused_import_detected(guard, tmp_path: Path):
    """Detect unused import in a real file."""
    f = tmp_path / "app.py"
    f.write_text("import os\nx = 1\n")
    issues = guard.scan_file(f, f.read_text())
    assert any("Unused import: 'os'" in i.message for i in issues)


def test_used_import_not_flagged(guard, tmp_path: Path):
    """Used import should not be flagged."""
    f = tmp_path / "app.py"
    f.write_text("import os\nprint(os.getcwd())\n")
    issues = guard.scan_file(f, f.read_text())
    unused = [i for i in issues if "Unused import" in i.message]
    assert unused == []


def test_unused_from_import(guard, tmp_path: Path):
    """Detect unused from-import."""
    f = tmp_path / "app.py"
    f.write_text("from os.path import join\nx = 1\n")
    issues = guard.scan_file(f, f.read_text())
    assert any("'join'" in i.message for i in issues)


def test_aliased_import_used(guard, tmp_path: Path):
    """Aliased import that is used should not flag."""
    f = tmp_path / "app.py"
    f.write_text("import collections as col\nprint(col.OrderedDict())\n")
    issues = guard.scan_file(f, f.read_text())
    unused = [i for i in issues if "Unused import" in i.message]
    assert unused == []


def test_star_import_ignored(guard, tmp_path: Path):
    """Star imports should not be flagged as unused."""
    f = tmp_path / "app.py"
    f.write_text("from os import *\nprint(getcwd())\n")
    issues = guard.scan_file(f, f.read_text())
    unused = [i for i in issues if "Unused import" in i.message]
    assert unused == []


def test_multiple_unused_imports(guard, tmp_path: Path):
    """Detect multiple unused imports."""
    f = tmp_path / "app.py"
    f.write_text("import os\nimport sys\nimport json\nx = 1\n")
    issues = guard.scan_file(f, f.read_text())
    unused = [i for i in issues if "Unused import" in i.message]
    assert len(unused) == 3


# ── Unreachable code (real files) ────────────────────────────


def test_unreachable_after_return(guard, tmp_path: Path):
    """Detect code after return."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            return 1
            x = 2
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Unreachable" in i.message for i in issues)


def test_unreachable_after_raise(guard, tmp_path: Path):
    """Detect code after raise."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            raise ValueError("bad")
            x = 2
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Unreachable" in i.message for i in issues)


def test_no_unreachable_normal_flow(guard, tmp_path: Path):
    """Normal flow should not flag unreachable."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            x = 1
            return x
    """))
    issues = guard.scan_file(f, f.read_text())
    assert not any("Unreachable" in i.message for i in issues)


def test_unreachable_after_break(guard, tmp_path: Path):
    """Detect code after break in a loop."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            for i in range(10):
                break
                x = 1
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Unreachable" in i.message for i in issues)


# ── Unused variables (real files) ────────────────────────────


def test_unused_variable_detected(guard, tmp_path: Path):
    """Detect unused variable in a real file."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            x = 1
            return 0
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Unused variable: 'x'" in i.message for i in issues)


def test_used_variable_not_flagged(guard, tmp_path: Path):
    """Used variable should not be flagged."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            x = 1
            return x
    """))
    issues = guard.scan_file(f, f.read_text())
    unused_vars = [i for i in issues if "Unused variable" in i.message]
    assert unused_vars == []


def test_underscore_variable_skipped(guard, tmp_path: Path):
    """Variables starting with _ should be skipped."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            _tmp = 1
            return 0
    """))
    issues = guard.scan_file(f, f.read_text())
    assert not any("_tmp" in i.message for i in issues)


def test_multiple_unused_variables(guard, tmp_path: Path):
    """Detect multiple unused variables."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def f():
            a = 1
            b = 2
            c = 3
            return 0
    """))
    issues = guard.scan_file(f, f.read_text())
    unused = [i for i in issues if "Unused variable" in i.message]
    assert len(unused) == 3


# ── Empty functions (real files) ─────────────────────────────


def test_empty_pass_function(guard, tmp_path: Path):
    """Detect function with only pass."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def stub():
            pass
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Empty function: 'stub'" in i.message for i in issues)


def test_empty_ellipsis_function(guard, tmp_path: Path):
    """Detect function with only ellipsis."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def stub():
            ...
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("Empty function: 'stub'" in i.message for i in issues)


def test_docstring_only_not_empty(guard, tmp_path: Path):
    """Function with only docstring is NOT considered empty."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent('''\
        def documented():
            """This has a docstring."""
    '''))
    issues = guard.scan_file(f, f.read_text())
    empty = [i for i in issues if "Empty function" in i.message]
    assert empty == []


def test_real_function_not_empty(guard, tmp_path: Path):
    """Function with real logic is NOT empty."""
    f = tmp_path / "app.py"
    f.write_text(textwrap.dedent("""\
        def add(a, b):
            return a + b
    """))
    issues = guard.scan_file(f, f.read_text())
    empty = [i for i in issues if "Empty function" in i.message]
    assert empty == []


# ── Clean code (no issues) ──────────────────────────────────


def test_clean_code_no_issues(guard, tmp_path: Path):
    """Clean, well-written code should not trigger any issues."""
    f = tmp_path / "clean.py"
    f.write_text(textwrap.dedent("""\
        import os

        def get_home():
            home = os.path.expanduser("~")
            return home

        def greet(name):
            msg = f"Hello, {name}!"
            print(msg)
            return msg
    """))
    issues = guard.scan_file(f, f.read_text())
    assert issues == []


# ── Syntax error handling ────────────────────────────────────


def test_syntax_error_returns_empty(guard, tmp_path: Path):
    """Syntax error should return empty list, not crash."""
    f = tmp_path / "broken.py"
    f.write_text("def (broken\n")
    issues = guard.scan_file(f, f.read_text())
    assert issues == []


# ── Vulture integration (mocked — external tool) ────────────


def test_vulture_parses_output(guard):
    """Vulture output is parsed into issues."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = "app.py:10: unused variable 'x' (60% confidence)"
    with patch("subprocess.run",
               return_value=mock_result):
        issues = guard._run_vulture(Path("."))
    assert len(issues) == 1
    assert issues[0].line == 10


def test_vulture_not_installed(guard):
    """Missing vulture returns empty list."""
    with patch("subprocess.run",
               side_effect=FileNotFoundError):
        issues = guard._run_vulture(Path("."))
    assert issues == []


# ── scan() directory walk (real filesystem) ──────────────────


def test_scan_walks_directory(guard, tmp_path: Path):
    """scan() finds issues across multiple real files."""
    (tmp_path / "a.py").write_text("import os\nx = 1\n")
    (tmp_path / "b.py").write_text(textwrap.dedent("""\
        def f():
            return 1
            x = 2
    """))
    with patch("subprocess.run",
               side_effect=FileNotFoundError):
        issues = guard.scan(tmp_path)
    assert any("Unused import" in i.message for i in issues)
    assert any("Unreachable" in i.message for i in issues)


def test_scan_skips_hidden_dirs(guard, tmp_path: Path):
    """scan() should skip hidden directories."""
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "bad.py").write_text("import os\nx = 1\n")
    (tmp_path / "good.py").write_text("import os\nprint(os.getcwd())\n")
    with patch("subprocess.run",
               side_effect=FileNotFoundError):
        issues = guard.scan(tmp_path)
    # Should not find the unused import in hidden dir
    assert not any(".hidden" in (i.file or "") for i in issues)


def test_scan_skips_venv(guard, tmp_path: Path):
    """scan() should skip venv directories."""
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "bad.py").write_text("import os\nx = 1\n")
    with patch("subprocess.run",
               side_effect=FileNotFoundError):
        issues = guard.scan(tmp_path)
    assert not any("venv" in (i.file or "") for i in issues)
