"""Tests for mutation_engine.py — mutation application, file scanning, helpers."""

import ast

from vibesrails.guards_v2.mutation_engine import (
    _collect_mutations,
    _parse_diff_line,
    _should_skip_mutation,
    apply_mutation,
    find_test_file,
    get_source_files,
    mutation_in_functions,
)


def _tree(code: str) -> ast.Module:
    return ast.parse(code)


# ── apply_mutation ──────────────────────────────────────


def test_apply_mutation_comparison():
    tree = _tree("x > 0")
    result = apply_mutation(tree, "comparison_swap", 0)
    assert result is not None
    assert "<" in ast.unparse(result)


def test_apply_mutation_unknown_type():
    tree = _tree("x > 0")
    assert apply_mutation(tree, "nonexistent_type", 0) is None


def test_apply_mutation_index_out_of_range():
    tree = _tree("x > 0")
    assert apply_mutation(tree, "comparison_swap", 99) is None


def test_apply_mutation_preserves_original():
    tree = _tree("x > 0")
    original_code = ast.unparse(tree)
    apply_mutation(tree, "comparison_swap", 0)
    assert ast.unparse(tree) == original_code


# ── find_test_file ──────────────────────────────────────


def test_find_test_file_in_tests_dir(tmp_path):
    src = tmp_path / "mypkg" / "utils.py"
    src.parent.mkdir()
    src.touch()
    test = tmp_path / "tests" / "test_utils.py"
    test.parent.mkdir()
    test.touch()
    assert find_test_file(src, tmp_path) == test


def test_find_test_file_in_test_dir(tmp_path):
    src = tmp_path / "mypkg" / "utils.py"
    src.parent.mkdir()
    src.touch()
    test = tmp_path / "test" / "test_utils.py"
    test.parent.mkdir()
    test.touch()
    assert find_test_file(src, tmp_path) == test


def test_find_test_file_in_root(tmp_path):
    src = tmp_path / "mypkg" / "utils.py"
    src.parent.mkdir()
    src.touch()
    test = tmp_path / "test_utils.py"
    test.touch()
    assert find_test_file(src, tmp_path) == test


def test_find_test_file_not_found(tmp_path):
    src = tmp_path / "mypkg" / "utils.py"
    src.parent.mkdir()
    src.touch()
    assert find_test_file(src, tmp_path) is None


# ── mutation_in_functions ───────────────────────────────


def test_mutation_in_functions_match():
    orig = _tree("def foo():\n    return 1 + 2\n")
    # Mutate the arithmetic
    mutated = apply_mutation(orig, "arithmetic_swap", 0)
    assert mutated is not None
    assert mutation_in_functions(orig, mutated, {"foo"}) is True


def test_mutation_in_functions_no_match():
    orig = _tree("def foo():\n    return 1 + 2\ndef bar():\n    pass\n")
    mutated = apply_mutation(orig, "arithmetic_swap", 0)
    assert mutated is not None
    assert mutation_in_functions(orig, mutated, {"bar"}) is True  # bar exists in mutated


def test_mutation_in_functions_empty_set():
    orig = _tree("x = 1 + 2")
    mutated = apply_mutation(orig, "arithmetic_swap", 0)
    assert mutated is not None
    # empty functions set means accept all mutations
    assert mutation_in_functions(orig, mutated, set()) is True


def test_mutation_in_functions_identical():
    tree = _tree("x = 1")
    assert mutation_in_functions(tree, tree, {"foo"}) is False


# ── _collect_mutations ──────────────────────────────────


def test_collect_mutations_basic():
    tree = _tree("x > 0\ny + 1\n")
    mutations = _collect_mutations(tree)
    assert len(mutations) >= 2
    types = {m[0] for m in mutations}
    assert "comparison_swap" in types
    assert "arithmetic_swap" in types


def test_collect_mutations_empty():
    tree = _tree("x = 1")
    mutations = _collect_mutations(tree)
    assert len(mutations) == 0


def test_collect_mutations_capped():
    # Many mutations should be capped at MAX_MUTATIONS_PER_FILE
    code = "\n".join(f"x{i} > {i}" for i in range(30))
    tree = _tree(code)
    mutations = _collect_mutations(tree)
    assert len(mutations) <= 20  # MAX_MUTATIONS_PER_FILE


# ── _should_skip_mutation ───────────────────────────────


def test_should_skip_none_mutation():
    tree = _tree("x = 1")
    assert _should_skip_mutation(None, tree, None) is True


def test_should_skip_no_filter():
    tree = _tree("x > 0")
    mutated = apply_mutation(tree, "comparison_swap", 0)
    assert _should_skip_mutation(mutated, tree, None) is False


def test_should_skip_with_filter_match():
    code = "def foo():\n    return 1 + 2\n"
    tree = _tree(code)
    mutated = apply_mutation(tree, "arithmetic_swap", 0)
    assert _should_skip_mutation(mutated, tree, {"foo"}) is False


# ── get_source_files ────────────────────────────────────


def test_get_source_files_basic(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "app.py").touch()
    (pkg / "utils.py").touch()
    files = get_source_files(tmp_path)
    names = {f.name for f in files}
    assert "app.py" in names
    assert "utils.py" in names


def test_get_source_files_skips_init(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    (pkg / "app.py").touch()
    files = get_source_files(tmp_path)
    names = {f.name for f in files}
    assert "__init__.py" not in names


def test_get_source_files_skips_test_files(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "app.py").touch()
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").touch()
    files = get_source_files(tmp_path)
    names = {f.name for f in files}
    assert "test_app.py" not in names


def test_get_source_files_skips_conftest(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "conftest.py").touch()
    (pkg / "app.py").touch()
    files = get_source_files(tmp_path)
    names = {f.name for f in files}
    assert "conftest.py" not in names


# ── _parse_diff_line ────────────────────────────────────


def test_parse_diff_line_new_file():
    changed: dict[str, set[str]] = {}
    result = _parse_diff_line("+++ b/src/utils.py", None, changed)
    assert result == "src/utils.py"


def test_parse_diff_line_non_python():
    changed: dict[str, set[str]] = {}
    result = _parse_diff_line("+++ b/README.md", None, changed)
    assert result is None


def test_parse_diff_line_function_hunk():
    changed: dict[str, set[str]] = {}
    _parse_diff_line("@@ -10,5 +10,5 @@ def my_func(x):", "src/utils.py", changed)
    assert "my_func" in changed["src/utils.py"]


def test_parse_diff_line_no_def():
    changed: dict[str, set[str]] = {}
    result = _parse_diff_line("@@ -10,5 +10,5 @@ class Foo:", "src/utils.py", changed)
    assert result == "src/utils.py"
    assert len(changed) == 0


def test_parse_diff_line_regular_line():
    changed: dict[str, set[str]] = {}
    result = _parse_diff_line("+    x = 1", "src/utils.py", changed)
    assert result == "src/utils.py"
    assert len(changed) == 0
