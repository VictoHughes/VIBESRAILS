"""Tests for PerformanceGuard — real files, real AST parsing, no mocks."""

from pathlib import Path

import pytest

from vibesrails.guards_v2.performance import PerformanceGuard


@pytest.fixture
def guard():
    return PerformanceGuard()


def _write(tmp_path: Path, code: str, name: str = "app.py") -> Path:
    """Write a real .py file and return its path."""
    f = tmp_path / name
    f.write_text(code)
    return f


# ── N+1 queries (real files) ─────────────────────────────────────


def test_nplus1_cursor_execute(guard, tmp_path):
    _write(tmp_path, "for row in rows:\n    cursor.execute('SELECT 1')\n")
    issues = guard.scan(tmp_path)
    assert any("N+1" in i.message for i in issues)


def test_nplus1_objects_filter(guard, tmp_path):
    _write(tmp_path, "for u in users:\n    Profile.objects.filter(user=u)\n")
    issues = guard.scan(tmp_path)
    assert any("N+1" in i.message for i in issues)


def test_no_nplus1_outside_loop(guard, tmp_path):
    _write(tmp_path, "cursor.execute('SELECT 1')\n")
    issues = guard.scan(tmp_path)
    assert not any("N+1" in i.message for i in issues)


# ── SELECT * (real files) ────────────────────────────────────────


def test_select_star_detected(guard, tmp_path):
    _write(tmp_path, 'q = "SELECT * FROM users"\n')
    issues = guard.scan(tmp_path)
    assert any("SELECT *" in i.message for i in issues)


def test_select_columns_ok(guard, tmp_path):
    _write(tmp_path, 'q = "SELECT id, name FROM users LIMIT 10"\n')
    issues = guard.scan(tmp_path)
    assert not any("SELECT *" in i.message for i in issues)


# ── Regex in loop (real files) ───────────────────────────────────


def test_regex_in_for_loop(guard, tmp_path):
    _write(tmp_path, 'for line in lines:\n    re.search(r"foo", line)\n')
    issues = guard.scan(tmp_path)
    assert any("re.search" in i.message for i in issues)


def test_regex_in_while_loop(guard, tmp_path):
    _write(tmp_path, 'while True:\n    re.match(r"bar", text)\n')
    issues = guard.scan(tmp_path)
    assert any("re.match" in i.message for i in issues)


def test_compiled_regex_no_issue(guard, tmp_path):
    code = 'pat = re.compile(r"foo")\nfor line in lines:\n    pat.search(line)\n'
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert not any("re.search" in i.message for i in issues)


# ── String concat in loop (real files) ───────────────────────────


def test_string_concat_in_loop(guard, tmp_path):
    code = 'result = ""\nfor x in items:\n    result += str(x)\n'
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("+=" in i.message for i in issues)


def test_no_concat_outside_loop(guard, tmp_path):
    _write(tmp_path, 'result += "hello"\n')
    issues = guard.scan(tmp_path)
    assert not any("+=" in i.message and "loop" in i.message for i in issues)


# ── No LIMIT on SQL (real files) ─────────────────────────────────


def test_no_limit_on_select(guard, tmp_path):
    _write(tmp_path, 'q = "SELECT id, name FROM users"\n')
    issues = guard.scan(tmp_path)
    assert any("LIMIT" in i.message for i in issues)


def test_limit_present_ok(guard, tmp_path):
    _write(tmp_path, 'q = "SELECT id FROM users LIMIT 100"\n')
    issues = guard.scan(tmp_path)
    assert not any("without LIMIT" in i.message for i in issues)


# ── time.sleep (real files) ──────────────────────────────────────


def test_time_sleep_in_app_code(guard, tmp_path):
    _write(tmp_path, "time.sleep(5)\n", name="app.py")
    issues = guard.scan(tmp_path)
    assert any("time.sleep" in i.message for i in issues)


def test_time_sleep_in_test_file_ok(guard, tmp_path):
    _write(tmp_path, "time.sleep(1)\n", name="test_foo.py")
    issues = guard.scan(tmp_path)
    assert not any("time.sleep" in i.message for i in issues)


# ── .read() without limit (real files) ───────────────────────────


def test_read_no_limit(guard, tmp_path):
    _write(tmp_path, "data = f.read()\n")
    issues = guard.scan(tmp_path)
    assert any(".read()" in i.message for i in issues)


def test_read_with_limit_ok(guard, tmp_path):
    _write(tmp_path, "data = f.read(1024)\n")
    issues = guard.scan(tmp_path)
    assert not any(".read()" in i.message for i in issues)


# ── len(listcomp) (real files) ───────────────────────────────────


def test_len_listcomp_detected(guard, tmp_path):
    _write(tmp_path, "n = len([x for x in items if x > 0])\n")
    issues = guard.scan(tmp_path)
    assert any("sum(1 for" in i.message for i in issues)


def test_len_normal_list_ok(guard, tmp_path):
    _write(tmp_path, "n = len(items)\n")
    issues = guard.scan(tmp_path)
    assert not any("sum(1 for" in i.message for i in issues)


# ── Global state mutation (real files) ───────────────────────────


def test_global_mutation_detected(guard, tmp_path):
    code = "counter = 0\n\ndef increment():\n    global counter\n    counter += 1\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert any("Global state" in i.message for i in issues)


def test_no_global_keyword_ok(guard, tmp_path):
    code = "counter = 0\n\ndef read():\n    print(counter)\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert not any("Global state" in i.message for i in issues)


# ── Clean file produces no issues ────────────────────────────────


def test_clean_file_no_issues(guard, tmp_path):
    code = "def greet(name):\n    return f'Hello {name}'\n"
    _write(tmp_path, code)
    issues = guard.scan(tmp_path)
    assert issues == []


# ── scan_file with syntax error ──────────────────────────────────


def test_syntax_error_returns_partial(guard):
    """Regex checks still run; AST checks are skipped on syntax error."""
    issues = guard.scan_file(Path("bad.py"), "def (broken")
    # Should not crash; returns whatever regex checks found
    assert isinstance(issues, list)
