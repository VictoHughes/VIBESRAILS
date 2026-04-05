"""Tests for vibesrails/guards_v2/impact_check.py."""

from __future__ import annotations

from pathlib import Path

from vibesrails.guards_v2.impact_check import (
    ImpactCheckGuard,
    build_call_index,
)

# ---------------------------------------------------------------------------
# 1. Simple direct call is indexed
# ---------------------------------------------------------------------------

def test_build_call_index_simple(tmp_path: Path) -> None:
    """lib.py defines helper(); app.py calls helper() — helper must appear in index."""
    lib = tmp_path / "lib.py"
    lib.write_text("def helper():\n    pass\n")

    app = tmp_path / "app.py"
    app.write_text("from lib import helper\n\ndef main():\n    helper()\n")

    index = build_call_index(tmp_path)

    assert "helper" in index.callers, "Expected 'helper' to be indexed as called"
    refs = index.get_callers("helper")
    assert len(refs) >= 1
    assert any(ref.caller_name == "main" for ref in refs)


# ---------------------------------------------------------------------------
# 2. Attribute (method) call is indexed under the method name
# ---------------------------------------------------------------------------

def test_build_call_index_method_call(tmp_path: Path) -> None:
    """handler.py calls db.query() — 'query' must appear in the index."""
    handler = tmp_path / "handler.py"
    handler.write_text(
        "def handle(db):\n"
        "    result = db.query('SELECT 1')\n"
        "    return result\n"
    )

    index = build_call_index(tmp_path)

    assert "query" in index.callers, "Expected attribute call 'db.query()' to be indexed"
    refs = index.get_callers("query")
    assert any(ref.caller_name == "handle" for ref in refs)


# ---------------------------------------------------------------------------
# 3. A function never called → empty callers list
# ---------------------------------------------------------------------------

def test_build_call_index_no_callers(tmp_path: Path) -> None:
    """A function that is defined but never called should not appear in the index."""
    lonely = tmp_path / "lonely.py"
    lonely.write_text("def lonely_func():\n    return 42\n")

    index = build_call_index(tmp_path)

    refs = index.get_callers("lonely_func")
    assert refs == [], "lonely_func should have no callers"


# ---------------------------------------------------------------------------
# 4. ImpactCheckGuard.check_removed raises block issue when callers exist
# ---------------------------------------------------------------------------

def test_impact_guard_detects_removed(tmp_path: Path) -> None:
    """A removed function that is still called should produce a block-severity issue."""
    caller_file = tmp_path / "service.py"
    caller_file.write_text(
        "def process():\n"
        "    removed_func()\n"
    )

    index = build_call_index(tmp_path)
    guard = ImpactCheckGuard()
    issues = guard.check_removed(["removed_func"], index)

    assert len(issues) >= 1
    assert all(issue.severity == "block" for issue in issues)
    assert any("removed_func" in issue.message for issue in issues)


# ---------------------------------------------------------------------------
# 5. check_removed produces no issues when function has no callers
# ---------------------------------------------------------------------------

def test_impact_guard_no_issues_when_no_callers(tmp_path: Path) -> None:
    """Removing a function with zero callers should produce no guard issues."""
    lib = tmp_path / "lib.py"
    lib.write_text("def orphan():\n    pass\n")

    index = build_call_index(tmp_path)
    guard = ImpactCheckGuard()
    issues = guard.check_removed(["orphan"], index)

    assert issues == [], "No issues expected when removed function has no callers"


# ---------------------------------------------------------------------------
# 6. Files inside the tests/ directory are not indexed
# ---------------------------------------------------------------------------

def test_call_index_skips_tests(tmp_path: Path) -> None:
    """test_* files and files under tests/ must not be included in the call index."""
    # Source file that defines a function
    src = tmp_path / "mymodule.py"
    src.write_text("def real_func():\n    pass\n")

    # Test file that calls real_func — should NOT be indexed
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_mymodule.py"
    test_file.write_text(
        "from mymodule import real_func\n\n"
        "def test_real_func():\n"
        "    real_func()\n"
    )

    # Also a top-level test_*.py file
    top_test = tmp_path / "test_extra.py"
    top_test.write_text("def test_something():\n    real_func()\n")

    index = build_call_index(tmp_path)

    # real_func is called only from test files; the index should have no callers
    refs = index.get_callers("real_func")
    assert refs == [], (
        f"Expected no callers for real_func (only test files call it), got: {refs}"
    )
