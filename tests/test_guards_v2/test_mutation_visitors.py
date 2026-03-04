"""Tests for mutation_visitors.py — AST visitors and data classes."""

import ast

from vibesrails.guards_v2.mutation_visitors import (
    ArithmeticSwapper,
    BooleanSwapper,
    ComparisonSwapper,
    FileMutationReport,
    MutantResult,
    ReturnNoneSwapper,
    StatementRemover,
    _count_targets,
)


def _parse(code: str) -> ast.Module:
    return ast.parse(code)


def _apply(visitor_cls, code: str, target_idx: int = 0) -> str:
    """Apply a visitor and return the mutated code."""
    tree = _parse(code)
    visitor = visitor_cls(target_idx)
    mutated = visitor.visit(tree)
    ast.fix_missing_locations(mutated)
    return ast.unparse(mutated), visitor.applied


# ── MutantResult dataclass ───────────────────────────────


def test_mutant_result_fields():
    r = MutantResult(file="a.py", function="foo", mutation_type="cmp", line=10, killed=True)
    assert r.file == "a.py"
    assert r.killed is True


# ── FileMutationReport dataclass ─────────────────────────


def test_report_score_no_mutations():
    r = FileMutationReport(file="a.py")
    assert r.score == 1.0


def test_report_score_all_killed():
    r = FileMutationReport(file="a.py", total=5, killed=5, survived=0)
    assert r.score == 1.0


def test_report_score_half():
    r = FileMutationReport(file="a.py", total=4, killed=2, survived=2)
    assert r.score == 0.5


def test_report_defaults():
    r = FileMutationReport(file="a.py")
    assert r.total == 0
    assert r.results == []


# ── ComparisonSwapper ────────────────────────────────────


def test_comparison_swap_gt_to_lt():
    code = "x > 0"
    result, applied = _apply(ComparisonSwapper, code)
    assert applied is True
    assert "<" in result


def test_comparison_swap_eq_to_noteq():
    code = "x == y"
    result, applied = _apply(ComparisonSwapper, code)
    assert applied is True
    assert "!=" in result


def test_comparison_swap_no_target():
    code = "x + 1"
    _, applied = _apply(ComparisonSwapper, code)
    assert applied is False


def test_comparison_swap_index_out_of_range():
    code = "x > 0"
    _, applied = _apply(ComparisonSwapper, code, target_idx=99)
    assert applied is False


# ── BooleanSwapper ───────────────────────────────────────


def test_boolean_swap_true_to_false():
    code = "x = True"
    result, applied = _apply(BooleanSwapper, code)
    assert applied is True
    assert "False" in result


def test_boolean_swap_and_to_or():
    # True counts as idx 0, so `and` is idx 1 (after the True booleans)
    code = "a and b"
    result, applied = _apply(BooleanSwapper, code, target_idx=0)
    assert applied is True
    assert "or" in result


def test_boolean_swap_no_booleans():
    code = "x = 1"
    _, applied = _apply(BooleanSwapper, code)
    assert applied is False


# ── ReturnNoneSwapper ────────────────────────────────────


def test_return_none_swaps_value():
    code = "def f():\n    return 42\n"
    result, applied = _apply(ReturnNoneSwapper, code)
    assert applied is True
    assert "return None" in result


def test_return_none_ignores_bare_return():
    code = "def f():\n    return\n"
    _, applied = _apply(ReturnNoneSwapper, code)
    assert applied is False


def test_return_none_no_return():
    code = "def f():\n    pass\n"
    _, applied = _apply(ReturnNoneSwapper, code)
    assert applied is False


# ── ArithmeticSwapper ────────────────────────────────────


def test_arithmetic_swap_add_to_sub():
    code = "x + y"
    result, applied = _apply(ArithmeticSwapper, code)
    assert applied is True
    assert "-" in result


def test_arithmetic_swap_mult_to_div():
    code = "x * y"
    result, applied = _apply(ArithmeticSwapper, code)
    assert applied is True
    assert "/" in result


def test_arithmetic_swap_no_target():
    code = "x = 1"
    _, applied = _apply(ArithmeticSwapper, code)
    assert applied is False


# ── StatementRemover ─────────────────────────────────────


def test_statement_remover_removes_statement():
    code = "def f():\n    x = 1\n    return x\n"
    result, applied = _apply(StatementRemover, code)
    assert applied is True
    assert "x = 1" not in result
    assert "return" in result


def test_statement_remover_single_statement_skipped():
    code = "def f():\n    return 1\n"
    _, applied = _apply(StatementRemover, code)
    assert applied is False


def test_statement_remover_index_out_of_range():
    code = "def f():\n    x = 1\n    return x\n"
    _, applied = _apply(StatementRemover, code, target_idx=99)
    assert applied is False


# ── _count_targets ───────────────────────────────────────


def test_count_targets_comparisons():
    tree = _parse("x > 0\ny < 1\n")
    assert _count_targets(tree, "comparison_swap") == 2


def test_count_targets_no_matches():
    tree = _parse("x = 1\n")
    assert _count_targets(tree, "comparison_swap") == 0


def test_count_targets_arithmetic():
    tree = _parse("a + b - c\n")
    assert _count_targets(tree, "arithmetic_swap") == 2
