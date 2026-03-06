"""Tests for vibesrails sync-memory — PROJECT_MEMORY.md auto-generation."""

import json
import sqlite3
from unittest import mock

import yaml

from vibesrails.sync_memory import (
    _TEMPLATE,
    generate_baselines,
    generate_context,
    generate_drift,
    generate_flows,
    generate_health,
    generate_quality,
    merge_sections,
    sync_memory,
)

# ============================================
# generate_health
# ============================================


def test_generate_health_no_db():
    """Returns fallback message when no DB available."""
    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = generate_health(None)
    assert "No session data" in result


def test_generate_health_empty_sessions(tmp_path):
    """Returns fallback when sessions table is empty."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE sessions (entropy_score REAL)"
    )
    conn.execute(
        "CREATE TABLE learning_events "
        "(event_type TEXT, event_data TEXT, created_at TEXT)"
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=conn):
        result = generate_health(tmp_path)
    assert "No sessions recorded" in result


def test_generate_health_with_data(tmp_path):
    """Generates health section from session data."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE sessions (entropy_score REAL)")
    conn.execute("INSERT INTO sessions VALUES (0.4)")
    conn.execute("INSERT INTO sessions VALUES (0.6)")
    conn.execute(
        "CREATE TABLE learning_events "
        "(event_type TEXT, event_data TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO learning_events VALUES "
        "('brief_score', '{\"score\": 80}', '2026-01-01')"
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=conn):
        result = generate_health(tmp_path)
    assert "Sessions tracked" in result
    assert "2" in result
    assert "warning" in result
    assert "brief score" in result.lower()


# ============================================
# generate_drift
# ============================================


def test_generate_drift_no_db():
    """Returns fallback when no DB."""
    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = generate_drift(None)
    assert "No drift data" in result


def test_generate_drift_one_snapshot(tmp_path):
    """Returns fallback when only 1 snapshot."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE drift_snapshots "
        "(session_id TEXT, file_path TEXT, timestamp TEXT, metrics TEXT)"
    )
    conn.execute(
        "INSERT INTO drift_snapshots VALUES "
        "('s1', ?, '2026-01-01', '{}')",
        (str(tmp_path),),
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=conn):
        result = generate_drift(tmp_path)
    assert "Need at least 2" in result


def test_generate_drift_with_data(tmp_path):
    """Computes velocity from 2 snapshots."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE drift_snapshots "
        "(session_id TEXT, file_path TEXT, timestamp TEXT, metrics TEXT)"
    )
    m1 = json.dumps({"import_count": 100, "class_count": 20,
                      "function_count": 50, "dependency_count": 10,
                      "complexity_avg": 5.0, "public_api_surface": 30})
    m2 = json.dumps({"import_count": 110, "class_count": 22,
                      "function_count": 55, "dependency_count": 12,
                      "complexity_avg": 6.0, "public_api_surface": 33})
    conn.execute(
        "INSERT INTO drift_snapshots VALUES ('s1', ?, '2026-01-01', ?)",
        (str(tmp_path), m1),
    )
    conn.execute(
        "INSERT INTO drift_snapshots VALUES ('s2', ?, '2026-01-02', ?)",
        (str(tmp_path), m2),
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=conn):
        result = generate_drift(tmp_path)
    assert "Velocity" in result
    assert "%" in result


# ============================================
# generate_quality
# ============================================


def test_generate_quality_no_db():
    """Returns fallback when no DB."""
    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = generate_quality(None)
    assert "No quality data" in result


def test_generate_quality_with_profile(tmp_path):
    """Generates quality from developer profile."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE developer_profile (metric_name TEXT, metric_value TEXT)"
    )
    conn.execute(
        "INSERT INTO developer_profile VALUES "
        "('top_violations', ?)",
        (json.dumps([{"guard": "dead-code", "count": 10}]),),
    )
    conn.execute(
        "INSERT INTO developer_profile VALUES "
        "('sessions_count', '5')",
    )
    conn.execute(
        "INSERT INTO developer_profile VALUES "
        "('hallucination_rate', '2.5')",
    )
    conn.commit()
    conn.row_factory = sqlite3.Row

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=conn):
        result = generate_quality(tmp_path)
    assert "dead-code" in result
    assert "2.5/session" in result
    assert "5 sessions" in result


# ============================================
# generate_flows
# ============================================


def test_generate_flows_empty(tmp_path):
    """Returns fallback when no packages."""
    result = generate_flows(tmp_path)
    assert "No cross-package" in result


def test_generate_flows_with_imports(tmp_path):
    """Detects cross-package imports."""
    pkg1 = tmp_path / "vibesrails"
    pkg1.mkdir()
    (pkg1 / "__init__.py").write_text("")
    (pkg1 / "foo.py").write_text("from core.bar import baz\n")

    pkg2 = tmp_path / "core"
    pkg2.mkdir()
    (pkg2 / "__init__.py").write_text("")
    (pkg2 / "bar.py").write_text("x = 1\n")

    result = generate_flows(tmp_path)
    assert "vibesrails -> core" in result
    assert "Data flow" in result


# ============================================
# generate_baselines
# ============================================


def test_generate_baselines_no_yaml(tmp_path):
    """Returns fallback when no vibesrails.yaml."""
    result = generate_baselines(tmp_path)
    assert "No vibesrails.yaml" in result


def test_generate_baselines_with_assertions(tmp_path):
    """Reads assertions from vibesrails.yaml."""
    config = {
        "assertions": {
            "values": {"version": "1.0.0"},
            "rules": {"fail_closed": True},
            "baselines": {"test_count": 100},
        }
    }
    (tmp_path / "vibesrails.yaml").write_text(yaml.dump(config))

    result = generate_baselines(tmp_path)
    assert "1.0.0" in result
    assert "fail_closed" in result
    assert "100" in result


# ============================================
# generate_context
# ============================================


def test_generate_context_unavailable(tmp_path):
    """Falls back gracefully when context detector fails."""
    with mock.patch(
        "vibesrails.context.detector.ContextDetector.detect",
        side_effect=RuntimeError("no git"),
    ):
        result = generate_context(tmp_path)
    assert "unavailable" in result.lower()


# ============================================
# merge_sections
# ============================================


def test_merge_preserves_manual_sections(tmp_path):
    """Manual sections outside AUTO markers are preserved."""
    existing = (
        "<!-- AUTO:baselines -->\nold\n<!-- /AUTO:baselines -->\n\n"
        "## My Manual Section\nDon't touch this."
    )
    config = {
        "assertions": {
            "values": {"version": "2.0"},
        }
    }
    (tmp_path / "vibesrails.yaml").write_text(yaml.dump(config))

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = merge_sections(existing, tmp_path)

    assert "My Manual Section" in result
    assert "Don't touch this" in result
    assert "2.0" in result
    assert "old" not in result


# ============================================
# sync_memory
# ============================================


def test_sync_memory_creates_file(tmp_path):
    """Creates PROJECT_MEMORY.md from template when missing."""
    (tmp_path / "vibesrails.yaml").write_text("assertions: {}")

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = sync_memory(tmp_path)

    memory_file = tmp_path / "PROJECT_MEMORY.md"
    assert memory_file.exists()
    assert "Project Memory" in result
    assert "Decisions Log" in result


def test_sync_memory_preserves_manual(tmp_path):
    """Re-running sync preserves manual edits."""
    (tmp_path / "vibesrails.yaml").write_text("assertions: {}")

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        sync_memory(tmp_path)

    # Add manual content
    memory_file = tmp_path / "PROJECT_MEMORY.md"
    content = memory_file.read_text()
    content = content.replace("- (none)", "- BUG-001: known issue")
    memory_file.write_text(content)

    # Re-sync
    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = sync_memory(tmp_path)

    assert "BUG-001" in result


def test_sync_memory_dry_run(tmp_path):
    """Dry run returns content without writing."""
    (tmp_path / "vibesrails.yaml").write_text("assertions: {}")

    with mock.patch("vibesrails.sync_memory._get_db_connection", return_value=None):
        result = sync_memory(tmp_path, dry_run=True)

    assert not (tmp_path / "PROJECT_MEMORY.md").exists()
    assert "Project Memory" in result


def test_template_has_all_auto_sections():
    """Template includes all AUTO markers."""
    for section in ["health", "drift", "quality", "flows", "baselines", "context"]:
        assert f"<!-- AUTO:{section} -->" in _TEMPLATE
        assert f"<!-- /AUTO:{section} -->" in _TEMPLATE
