"""Tests for DatabaseSafetyGuard — real Python files, no mocking."""

from pathlib import Path

from vibesrails.guards_v2.database_safety import DatabaseSafetyGuard

GUARD = DatabaseSafetyGuard()


def _write_and_scan(tmp_path: Path, code: str) -> list:
    """Write code to a .py file and scan the project."""
    f = tmp_path / "app.py"
    f.write_text(code)
    return GUARD.scan(tmp_path)


# ── Raw SQL injection patterns ──────────────────────────


def test_fstring_in_execute(tmp_path):
    issues = _write_and_scan(tmp_path, 'cursor.execute(f"SELECT * FROM {table}")\n')
    assert any(i.severity == "block" and "Raw SQL" in i.message for i in issues)


def test_format_in_execute(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'cursor.execute("SELECT * FROM users WHERE id={}".format(uid))\n'
    )
    assert any(i.severity == "block" and "Raw SQL" in i.message for i in issues)


def test_percent_in_execute(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'cursor.execute("SELECT * FROM users WHERE id=%s" % uid)\n'
    )
    assert any(i.severity == "block" and "Raw SQL" in i.message for i in issues)


def test_parameterized_query_is_clean(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'cursor.execute("SELECT * FROM users WHERE id=?", (uid,))\n'
    )
    assert not any("Raw SQL" in i.message for i in issues)


# ── Dangerous DDL/DML ───────────────────────────────────


def test_drop_table_blocked(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "DROP TABLE users"\n')
    assert any(i.severity == "block" and "DROP" in i.message for i in issues)


def test_truncate_table_blocked(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "TRUNCATE TABLE sessions"\n')
    assert any(i.severity == "block" for i in issues)


def test_delete_without_where(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "DELETE FROM users"\n')
    assert any("DELETE" in i.message for i in issues)


def test_delete_with_where_is_clean(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'sql = "DELETE FROM users WHERE id=1"\n'
    )
    assert not any("DELETE" in i.message and "without WHERE" in i.message for i in issues)


# ── SELECT without LIMIT ────────────────────────────────


def test_select_without_limit_warned(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "SELECT * FROM users"\n')
    assert any(i.severity == "warn" and "LIMIT" in i.message for i in issues)


def test_select_with_limit_is_clean(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "SELECT * FROM users LIMIT 100"\n')
    assert not any("LIMIT" in i.message for i in issues)


def test_select_count_is_clean(tmp_path):
    issues = _write_and_scan(tmp_path, 'sql = "SELECT COUNT(*) FROM users"\n')
    assert not any("LIMIT" in i.message for i in issues)


# ── Connection without timeout ──────────────────────────


def test_connection_without_timeout(tmp_path):
    issues = _write_and_scan(tmp_path, 'conn = psycopg2.connect(dbname="mydb")\n')
    assert any("timeout" in i.message.lower() for i in issues)


def test_connection_with_timeout_is_clean(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'conn = psycopg2.connect(dbname="mydb", connect_timeout=5)\n'
    )
    assert not any("timeout" in i.message.lower() for i in issues)


# ── Django patterns ─────────────────────────────────────


def test_django_raw_fstring(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'qs = MyModel.objects.raw(f"SELECT * FROM {table}")\n'
    )
    assert any("Django raw()" in i.message for i in issues)


def test_django_extra_warned(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'qs = MyModel.objects.extra(where=["id > 5"])\n'
    )
    assert any("extra()" in i.message for i in issues)


# ── SQLAlchemy patterns ─────────────────────────────────


def test_sqlalchemy_text_fstring(tmp_path):
    issues = _write_and_scan(
        tmp_path, 'stmt = text(f"SELECT * FROM {table}")\n'
    )
    assert any("SQLAlchemy text()" in i.message for i in issues)


# ── Edge cases ──────────────────────────────────────────


def test_comments_are_ignored(tmp_path):
    issues = _write_and_scan(
        tmp_path, '# cursor.execute(f"SELECT * FROM users")\n'
    )
    assert len(issues) == 0


def test_hidden_dirs_excluded(tmp_path):
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "bad.py").write_text('cursor.execute(f"DROP TABLE x")\n')
    issues = GUARD.scan(tmp_path)
    assert len(issues) == 0


def test_pycache_excluded(tmp_path):
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "bad.py").write_text('cursor.execute(f"DROP TABLE x")\n')
    issues = GUARD.scan(tmp_path)
    assert len(issues) == 0


def test_clean_orm_code_no_issues(tmp_path):
    code = (
        "from django.db import models\n\n"
        "class User(models.Model):\n"
        "    name = models.CharField(max_length=100)\n\n"
        "users = User.objects.filter(active=True)[:10]\n"
    )
    issues = _write_and_scan(tmp_path, code)
    assert len(issues) == 0


def test_multiple_issues_in_one_file(tmp_path):
    code = (
        'cursor.execute(f"SELECT * FROM {t}")\n'
        'sql = "DROP TABLE sessions"\n'
        'conn = psycopg2.connect(dbname="x")\n'
    )
    issues = _write_and_scan(tmp_path, code)
    assert len(issues) >= 3
