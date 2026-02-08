"""Tests for storage/migrations.py — V2 migration (brief_history table)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from storage.migrations import (  # noqa: E402
    SCHEMA_VERSION,
    get_current_version,
    migrate,
)


class TestMigrationV2:
    """Tests for V2 migration — brief_history table."""

    def test_brief_history_table_created(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='brief_history'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent_v2(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        migrate(db)  # Second call must not crash
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='brief_history'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_session_id_index_exists(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_brief_history_session'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_schema_version_at_least_2(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        version = get_current_version(conn)
        conn.close()
        assert version >= 2
        assert SCHEMA_VERSION >= 2

    def test_brief_history_columns(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(brief_history)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {"id", "session_id", "brief_json", "score", "level", "created_at"}
        assert columns == expected

    def test_v1_tables_still_exist(self, tmp_path):
        db = tmp_path / "v2.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        # All V1 tables must still be present
        v1_tables = {"meta", "sessions", "violations", "drift_snapshots", "package_cache"}
        assert v1_tables.issubset(tables)
