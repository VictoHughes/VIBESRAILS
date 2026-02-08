"""Tests for storage/migrations.py — V3 migration (learning_events + developer_profile)."""

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


class TestMigrationV3:
    """Tests for V3 migration — learning_events + developer_profile tables."""

    def test_learning_events_table_created(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='learning_events'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_developer_profile_table_created(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='developer_profile'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent_v3(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        migrate(db)  # second call must not crash
        conn = sqlite3.connect(str(db))
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('learning_events', 'developer_profile')"
            ).fetchall()
        }
        conn.close()
        assert tables == {"learning_events", "developer_profile"}

    def test_learning_events_index_exists(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_learning_events_type_date'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_schema_version_is_3(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        version = get_current_version(conn)
        conn.close()
        assert version == 3
        assert SCHEMA_VERSION == 3

    def test_learning_events_columns(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(learning_events)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {"id", "session_id", "event_type", "event_data", "created_at"}
        assert columns == expected

    def test_developer_profile_columns(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute("PRAGMA table_info(developer_profile)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {"id", "metric_name", "metric_value", "updated_at"}
        assert columns == expected

    def test_v1_v2_tables_still_exist(self, tmp_path):
        db = tmp_path / "v3.db"
        migrate(db)
        conn = sqlite3.connect(str(db))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        v1_v2_tables = {
            "meta", "sessions", "violations", "drift_snapshots",
            "package_cache", "brief_history",
        }
        assert v1_v2_tables.issubset(tables)
