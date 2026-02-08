"""Tests for tools/check_drift.py — MCP check_drift tool."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.check_drift import check_drift  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────

def _make_project(tmp_path: Path, files: dict[str, str]) -> Path:
    proj = tmp_path / "project"
    proj.mkdir()
    for name, content in files.items():
        f = proj / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return proj


# ── Baseline scan ────────────────────────────────────────────────────


class TestBaselineScan:
    """Tests for the first scan (no prior snapshot)."""

    def test_first_scan_returns_baseline(self, tmp_path):
        proj = _make_project(tmp_path, {
            "app.py": "import os\ndef main():\n    pass\n",
        })
        db = tmp_path / "drift.db"
        result = check_drift(
            project_path=str(proj), db_path=str(db),
        )
        assert result["status"] == "info"
        assert result["is_baseline"] is True
        assert result["velocity_score"] is None
        assert result["pedagogy"] is not None

    def test_baseline_has_snapshot_metrics(self, tmp_path):
        proj = _make_project(tmp_path, {
            "app.py": "class Foo:\n    pass\n",
        })
        db = tmp_path / "drift.db"
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert result["snapshot"]["class_count"] == 1


# ── Velocity scan ────────────────────────────────────────────────────


class TestVelocityScan:
    """Tests for subsequent scans with velocity calculation."""

    def test_second_scan_has_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        db = tmp_path / "drift.db"
        check_drift(project_path=str(proj), db_path=str(db))
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert result["is_baseline"] is False
        assert result["velocity_score"] is not None
        assert result["velocity_level"] is not None

    def test_identical_code_normal_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {
            "a.py": "import os\ndef foo():\n    pass\n",
        })
        db = tmp_path / "drift.db"
        check_drift(project_path=str(proj), db_path=str(db))
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert result["velocity_level"] == "normal"
        assert result["status"] == "pass"

    def test_large_change_higher_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "def f1():\n    pass\n"})
        db = tmp_path / "drift.db"
        check_drift(project_path=str(proj), db_path=str(db))

        # Major architectural change
        (proj / "a.py").write_text(
            "import os\nimport sys\nimport json\n"
            "class A:\n    pass\nclass B:\n    pass\nclass C:\n    pass\n"
            "def f1():\n    pass\ndef f2():\n    pass\ndef f3():\n    pass\n"
            "def f4():\n    pass\ndef f5():\n    pass\n"
        )
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert result["velocity_score"] > 5.0
        assert result["velocity_level"] in ("warning", "critical")


# ── Pedagogy ─────────────────────────────────────────────────────────


class TestPedagogy:
    """Tests for pedagogy in results."""

    def test_baseline_has_pedagogy(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        db = tmp_path / "drift.db"
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert "pedagogy" in result
        p = result["pedagogy"]
        assert "why" in p
        assert "recommendation" in p

    def test_velocity_has_pedagogy(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        db = tmp_path / "drift.db"
        check_drift(project_path=str(proj), db_path=str(db))
        result = check_drift(project_path=str(proj), db_path=str(db))
        assert "pedagogy" in result
        assert "why" in result["pedagogy"]


# ── Error handling ───────────────────────────────────────────────────


class TestErrorHandling:
    """Tests for error cases."""

    def test_nonexistent_path(self, tmp_path):
        db = tmp_path / "drift.db"
        result = check_drift(
            project_path=str(tmp_path / "nonexistent"),
            db_path=str(db),
        )
        assert result["status"] == "error"

    def test_file_not_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("not a dir")
        db = tmp_path / "drift.db"
        result = check_drift(project_path=str(f), db_path=str(db))
        assert result["status"] == "error"


# ── Result structure ─────────────────────────────────────────────────


class TestResultStructure:
    """Tests for consistent result structure."""

    def test_result_has_required_keys(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        db = tmp_path / "drift.db"
        result = check_drift(project_path=str(proj), db_path=str(db))
        for key in ("status", "is_baseline", "snapshot", "velocity_score",
                     "velocity_level", "trend", "metrics_delta",
                     "consecutive_high", "review_required", "pedagogy"):
            assert key in result, f"Missing key: {key}"
