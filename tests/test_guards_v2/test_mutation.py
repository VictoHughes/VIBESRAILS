"""Tests for MutationGuard — mutation testing engine."""

import ast
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from vibesrails.guards_v2.mutation import (
    MutationGuard,
    _count_targets,
)


@pytest.fixture
def guard():
    return MutationGuard()


@pytest.fixture
def calculator_project(tmp_path):
    """Create a real mini-project with source and test."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "calculator.py").write_text(textwrap.dedent("""\
        def add(a, b):
            return a + b

        def is_positive(x):
            if x > 0:
                return True
            return False

        def logic_gate(a, b):
            return a and b
    """))

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_calculator.py").write_text(textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, r"{src}")
        from calculator import add, is_positive, logic_gate

        def test_add():
            assert add(2, 3) == 5
            assert add(-1, 1) == 0

        def test_is_positive():
            assert is_positive(5) is True
            assert is_positive(-3) is False
            assert is_positive(0) is False

        def test_logic_gate():
            assert logic_gate(True, True) is True
            assert logic_gate(True, False) is False
    """))
    return tmp_path


@pytest.fixture
def fake_test_project(tmp_path):
    """Project with fake tests that don't verify anything."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "calculator.py").write_text(textwrap.dedent("""\
        def add(a, b):
            return a + b

        def is_positive(x):
            if x > 0:
                return True
            return False
    """))

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_calculator.py").write_text(textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, r"{src}")
        from calculator import add, is_positive

        def test_add():
            add(2, 3)
            assert True

        def test_is_positive():
            is_positive(5)
            assert True
    """))
    return tmp_path


# --- Test _apply_mutation ---


def test_comparison_swap(guard):
    """Test that comparison operators get swapped."""
    code = "x = 1 > 0"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(tree, "comparison_swap", 0)
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "<" in result


def test_boolean_swap(guard):
    """Test that True gets swapped to False."""
    code = "x = True"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(tree, "boolean_swap", 0)
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "False" in result


def test_return_none_swap(guard):
    """Test that return values get replaced with None."""
    code = "def f():\n    return 42"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(tree, "return_none", 0)
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "None" in result


def test_arithmetic_swap(guard):
    """Test that + gets swapped to -."""
    code = "x = 1 + 2"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(tree, "arithmetic_swap", 0)
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "-" in result


def test_statement_remove(guard):
    """Test that a statement gets removed from function body."""
    code = "def f():\n    x = 1\n    return x"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(
        tree, "statement_remove", 0
    )
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "x = 1" not in result


def test_apply_mutation_invalid_type(guard):
    """Test that invalid mutation type returns None."""
    tree = ast.parse("x = 1")
    assert guard._apply_mutation(tree, "invalid", 0) is None


def test_apply_mutation_out_of_range(guard):
    """Test that out-of-range index returns None."""
    tree = ast.parse("x = 1 > 0")
    result = guard._apply_mutation(
        tree, "comparison_swap", 999
    )
    assert result is None


# --- Test _find_test_file ---


def test_find_test_file_found(guard, tmp_path):
    """Test finding a test file that exists."""
    src = tmp_path / "src" / "foo.py"
    src.parent.mkdir(parents=True)
    src.touch()
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_foo.py"
    test_file.touch()
    result = guard._find_test_file(src, tmp_path)
    assert result == test_file


def test_find_test_file_not_found(guard, tmp_path):
    """Test when no test file exists."""
    src = tmp_path / "src" / "bar.py"
    src.parent.mkdir(parents=True)
    src.touch()
    result = guard._find_test_file(src, tmp_path)
    assert result is None


def test_find_test_file_test_dir(guard, tmp_path):
    """Test finding test in 'test/' directory."""
    src = tmp_path / "src" / "baz.py"
    src.parent.mkdir(parents=True)
    src.touch()
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "test_baz.py").touch()
    result = guard._find_test_file(src, tmp_path)
    assert result is not None


# --- Test _count_targets ---


def test_count_targets_comparison():
    """Test counting comparison targets."""
    tree = ast.parse("x = 1 > 0\ny = 2 < 3")
    assert _count_targets(tree, "comparison_swap") == 2


def test_count_targets_no_targets():
    """Test counting with no targets."""
    tree = ast.parse("x = 1")
    assert _count_targets(tree, "comparison_swap") == 0


# --- Test _run_tests_on_mutant ---


def test_run_tests_killed(guard, calculator_project):
    """Test that a mutant gets killed by good tests."""
    src = calculator_project / "src" / "calculator.py"
    test = (
        calculator_project / "tests" / "test_calculator.py"
    )
    tree = ast.parse(src.read_text())
    mutated = guard._apply_mutation(
        tree, "arithmetic_swap", 0
    )
    assert mutated is not None
    mutant_code = ast.unparse(mutated)
    src.write_text(mutant_code)
    survived = guard._run_tests_on_mutant(src, test)
    assert not survived, "Mutant should be killed"


def test_run_tests_survived(guard, fake_test_project):
    """Test that mutants survive fake tests."""
    src = fake_test_project / "src" / "calculator.py"
    test = (
        fake_test_project / "tests" / "test_calculator.py"
    )
    tree = ast.parse(src.read_text())
    mutated = guard._apply_mutation(
        tree, "arithmetic_swap", 0
    )
    assert mutated is not None
    mutant_code = ast.unparse(mutated)
    src.write_text(mutant_code)
    survived = guard._run_tests_on_mutant(src, test)
    assert survived, "Mutant should survive fake tests"


# --- Test scan_quick with mocked git ---


def test_scan_quick_no_changes(guard, tmp_path):
    """Test quick scan with no git changes."""
    with patch.object(
        guard, "_get_changed_functions", return_value={}
    ):
        issues = guard.scan_quick(tmp_path)
    assert issues == []


def test_scan_quick_with_changes(
    guard, calculator_project
):
    """Test quick scan with mocked changed functions."""
    changed = {"src/calculator.py": {"add"}}
    with patch.object(
        guard, "_get_changed_functions",
        return_value=changed,
    ):
        issues = guard.scan_quick(calculator_project)
    # Should run without error; results depend on mutations
    assert isinstance(issues, list)


# --- Test scan_with_mutmut ---


def test_mutmut_not_installed(guard, tmp_path):
    """Test mutmut integration when not installed."""
    with patch("shutil.which", return_value=None):
        issues = guard.scan_with_mutmut(tmp_path)
    assert len(issues) == 1
    assert "not installed" in issues[0].message


def test_mutmut_integration_success(guard, tmp_path):
    """Test mutmut integration with mocked subprocess."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    with (
        patch("shutil.which", return_value="/usr/bin/mutmut"),
        patch("subprocess.run") as mock_run,
    ):
        # First call: mutmut run
        run_result = MagicMock()
        run_result.returncode = 0
        # Second call: mutmut results
        results_result = MagicMock()
        results_result.stdout = (
            "Killed 8\nSurvived 2\n"
            "Killed\nKilled\nKilled\nKilled\n"
            "Killed\nKilled\nKilled\nKilled\n"
            "Survived\nSurvived\n"
        )
        mock_run.side_effect = [run_result, results_result]
        issues = guard.scan_with_mutmut(tmp_path)
    # 8 killed + 2 survived = 80% > 60%, no issues
    assert all(
        i.severity != "block" for i in issues
    )


def test_mutmut_low_score(guard, tmp_path):
    """Test mutmut with low mutation score."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    with (
        patch("shutil.which", return_value="/usr/bin/mutmut"),
        patch("subprocess.run") as mock_run,
    ):
        run_result = MagicMock()
        run_result.returncode = 0
        results_result = MagicMock()
        # 1 killed, 9 survived = 10% < 30%
        results_result.stdout = (
            "Killed\n" + "Survived\n" * 9
        )
        mock_run.side_effect = [run_result, results_result]
        issues = guard.scan_with_mutmut(tmp_path)
    assert any(i.severity == "block" for i in issues)


# --- Test generate_report ---


def test_generate_report_no_files(guard, tmp_path):
    """Test report with no source files."""
    report = guard.generate_report(tmp_path)
    assert "No mutation testing results" in report


def test_generate_report_with_results(
    guard, calculator_project
):
    """Test report generation with real project."""
    report = guard.generate_report(calculator_project)
    assert "Mutation Testing Report" in report
    assert "calculator.py" in report


# --- Test boolean and/or swap ---


def test_boolean_and_or_swap(guard):
    """Test that 'and' gets swapped to 'or'."""
    code = "x = a and b"
    tree = ast.parse(code)
    mutated = guard._apply_mutation(
        tree, "boolean_swap", 0
    )
    assert mutated is not None
    result = ast.unparse(mutated)
    assert "or" in result


# --- Test _get_source_files ---


def test_get_source_files_skips_init(guard, tmp_path):
    """Test that __init__.py is skipped."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "real.py").write_text("x = 1")
    files = guard._get_source_files(tmp_path)
    names = [f.name for f in files]
    assert "__init__.py" not in names
    assert "real.py" in names


def test_get_source_files_skips_tests(guard, tmp_path):
    """Test that test files are skipped."""
    (tmp_path / "module.py").write_text("x = 1")
    (tmp_path / "test_module.py").write_text("x = 1")
    files = guard._get_source_files(tmp_path)
    names = [f.name for f in files]
    assert "module.py" in names
    assert "test_module.py" not in names
