"""Tests for storage/migrations.py — SQLite schema migrations."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from storage.migrations import (  # noqa: E402
    MIGRATIONS,
    SCHEMA_VERSION,
    get_current_version,
    get_db_path,
    migrate,
)

EXPECTED_TABLES = {
    "meta", "sessions", "violations", "drift_snapshots", "package_cache",
    "brief_history", "learning_events", "developer_profile",
}


def _get_tables(db_path: Path) -> set[str]:
    """Return the set of user table names in the database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tables


class TestMigrate:
    """Tests for the migrate() function."""

    def test_creates_all_tables(self, tmp_path):
        db = tmp_path / "test.db"
        migrate(db)
        tables = _get_tables(db)
        assert tables == EXPECTED_TABLES

    def test_idempotent(self, tmp_path):
        db = tmp_path / "test.db"
        migrate(db)
        migrate(db)  # second call must not crash
        tables = _get_tables(db)
        assert tables == EXPECTED_TABLES

    def test_version_after_migration(self, tmp_path):
        db = tmp_path / "test.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        version = get_current_version(conn)
        conn.close()
        assert version == SCHEMA_VERSION

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        db = nested / "test.db"
        migrate(db)
        assert db.exists()
        assert _get_tables(db) == EXPECTED_TABLES

    def test_empty_db_gets_full_migration(self, tmp_path):
        db = tmp_path / "empty.db"
        # Pre-create an empty database
        sqlite3.connect(str(db)).close()
        migrate(db)
        assert _get_tables(db) == EXPECTED_TABLES

    def test_schema_version_constant(self):
        assert SCHEMA_VERSION == max(MIGRATIONS.keys())


class TestGetCurrentVersion:
    """Tests for get_current_version()."""

    def test_returns_zero_on_fresh_db(self, tmp_path):
        db = tmp_path / "fresh.db"
        conn = sqlite3.connect(str(db))
        assert get_current_version(conn) == 0
        conn.close()

    def test_returns_version_after_migrate(self, tmp_path):
        db = tmp_path / "migrated.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        assert get_current_version(conn) == SCHEMA_VERSION
        conn.close()


class TestGetDbPath:
    """Tests for get_db_path()."""

    def test_returns_path_object(self):
        result = get_db_path()
        assert isinstance(result, Path)

    def test_path_ends_with_sessions_db(self):
        result = get_db_path()
        assert result.name == "sessions.db"
        assert result.parent.name == ".vibesrails"


class TestSessionsTable:
    """Verify sessions table schema."""

    def test_sessions_columns(self, tmp_path):
        db = tmp_path / "schema.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {
            "id", "start_time", "end_time", "ai_tool", "files_modified",
            "total_changes_loc", "violations_count", "entropy_score", "project_path",
        }
        assert columns == expected


class TestViolationsTable:
    """Verify violations table schema."""

    def test_violations_columns(self, tmp_path):
        db = tmp_path / "schema.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(violations)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {
            "id", "session_id", "timestamp", "guard_name",
            "file_path", "severity", "message", "pedagogy_shown",
        }
        assert columns == expected


class TestPackageCacheTable:
    """Verify package_cache table schema."""

    def test_package_cache_columns(self, tmp_path):
        db = tmp_path / "schema.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(package_cache)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {
            "package_name", "ecosystem", "exists_flag",
            "api_surface", "version", "cached_at",
        }
        assert columns == expected
