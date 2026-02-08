"""Tests for core/drift_tracker.py — Drift Velocity Index."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.drift_tracker import (  # noqa: E402
    DriftTracker,
    _compute_complexity,
    aggregate_metrics,
    analyze_file,
    classify_velocity,
)

# ── Helpers ───────────────────────────────────────────────────────────

def _tracker(tmp_path: Path) -> DriftTracker:
    db = tmp_path / "drift_test.db"
    return DriftTracker(db_path=str(db))


def _make_project(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a project directory with given Python files."""
    proj = tmp_path / "project"
    proj.mkdir()
    for name, content in files.items():
        f = proj / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return proj


# ── analyze_file ─────────────────────────────────────────────────────


class TestAnalyzeFile:
    """Tests for single-file analysis."""

    def test_counts_imports(self, tmp_path):
        f = tmp_path / "test_file.py"
        f.write_text("import os\nimport sys\nfrom pathlib import Path\n")
        m = analyze_file(f)
        assert m["import_count"] == 3  # os, sys, Path

    def test_counts_classes(self, tmp_path):
        f = tmp_path / "test_file.py"
        f.write_text("class Foo:\n    pass\n\nclass Bar:\n    pass\n")
        m = analyze_file(f)
        assert m["class_count"] == 2

    def test_counts_functions(self, tmp_path):
        f = tmp_path / "test_file.py"
        f.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
        m = analyze_file(f)
        assert m["function_count"] == 2

    def test_counts_public_api(self, tmp_path):
        f = tmp_path / "test_file.py"
        f.write_text(
            "def public_fn():\n    pass\n\n"
            "def _private_fn():\n    pass\n\n"
            "class PublicClass:\n    pass\n\n"
            "class _PrivateClass:\n    pass\n"
        )
        m = analyze_file(f)
        assert m["public_api_surface"] == 2  # public_fn + PublicClass

    def test_counts_dependencies(self, tmp_path):
        f = tmp_path / "test_file.py"
        f.write_text("from os import path\nfrom . import local\nfrom sys import argv\n")
        m = analyze_file(f)
        # Only absolute imports count: os and sys
        assert m["dependency_count"] == 2

    def test_syntax_error_returns_none(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        assert analyze_file(f) is None


# ── Complexity ───────────────────────────────────────────────────────


class TestComplexity:
    """Tests for cyclomatic complexity calculation."""

    def test_empty_file_complexity_1(self, tmp_path):
        import ast
        tree = ast.parse("")
        assert _compute_complexity(tree) == 1

    def test_branching_adds_complexity(self, tmp_path):
        import ast
        code = "if x:\n    pass\nfor i in y:\n    pass\nwhile z:\n    pass\n"
        tree = ast.parse(code)
        # Base 1 + if + for + while = 4
        assert _compute_complexity(tree) == 4

    def test_bool_ops_add_complexity(self, tmp_path):
        import ast
        code = "if a and b or c:\n    pass\n"
        tree = ast.parse(code)
        # Base 1 + if + BoolOp(or: 2 values → +1) + BoolOp(and: 2 values → +1) = 4
        assert _compute_complexity(tree) >= 3


# ── aggregate_metrics ────────────────────────────────────────────────


class TestAggregateMetrics:
    """Tests for project-level aggregation."""

    def test_aggregates_multiple_files(self, tmp_path):
        proj = _make_project(tmp_path, {
            "a.py": "import os\ndef foo():\n    pass\n",
            "b.py": "import sys\nclass Bar:\n    pass\n",
        })
        m = aggregate_metrics(proj)
        assert m["file_count"] == 2
        assert m["import_count"] == 2
        assert m["function_count"] == 1
        assert m["class_count"] == 1

    def test_empty_project(self, tmp_path):
        proj = _make_project(tmp_path, {})
        m = aggregate_metrics(proj)
        assert m["file_count"] == 0
        assert m["import_count"] == 0

    def test_skips_pycache(self, tmp_path):
        proj = _make_project(tmp_path, {
            "main.py": "x = 1\n",
            "__pycache__/cached.py": "y = 2\n",
        })
        m = aggregate_metrics(proj)
        assert m["file_count"] == 1


# ── classify_velocity ────────────────────────────────────────────────


class TestClassifyVelocity:
    """Tests for velocity classification."""

    def test_normal(self):
        assert classify_velocity(0.0) == "normal"
        assert classify_velocity(3.0) == "normal"
        assert classify_velocity(5.0) == "normal"

    def test_warning(self):
        assert classify_velocity(5.1) == "warning"
        assert classify_velocity(10.0) == "warning"
        assert classify_velocity(15.0) == "warning"

    def test_critical(self):
        assert classify_velocity(15.1) == "critical"
        assert classify_velocity(50.0) == "critical"


# ── take_snapshot ────────────────────────────────────────────────────


class TestTakeSnapshot:
    """Tests for snapshot capture."""

    def test_snapshot_captures_metrics(self, tmp_path):
        proj = _make_project(tmp_path, {
            "app.py": "import os\ndef main():\n    pass\n",
        })
        t = _tracker(tmp_path)
        snap = t.take_snapshot(str(proj))
        assert "metrics" in snap
        assert snap["metrics"]["import_count"] == 1
        assert snap["metrics"]["function_count"] == 1

    def test_snapshot_persists_to_db(self, tmp_path):
        proj = _make_project(tmp_path, {"x.py": "x = 1\n"})
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj), session_id="s1")
        assert t.get_snapshot_count(str(proj)) == 1

    def test_not_a_directory_returns_error(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("not a dir")
        t = _tracker(tmp_path)
        result = t.take_snapshot(str(f))
        assert "error" in result


# ── compute_velocity ─────────────────────────────────────────────────


class TestComputeVelocity:
    """Tests for velocity calculation."""

    def test_first_snapshot_no_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj))
        assert t.compute_velocity(str(proj)) is None

    def test_two_identical_snapshots_zero_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {
            "a.py": "import os\ndef foo():\n    pass\n",
        })
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj), session_id="s1")
        t.take_snapshot(str(proj), session_id="s2")
        v = t.compute_velocity(str(proj))
        assert v is not None
        assert v["velocity_score"] == 0.0
        assert v["velocity_level"] == "normal"

    def test_adding_function_increases_velocity(self, tmp_path):
        proj = _make_project(tmp_path, {
            "a.py": "def foo():\n    pass\n",
        })
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj), session_id="s1")

        # Add a second function
        (proj / "a.py").write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
        t.take_snapshot(str(proj), session_id="s2")

        v = t.compute_velocity(str(proj))
        assert v is not None
        assert v["velocity_score"] > 0
        assert "function_count" in v["metrics_delta"]
        fcount = v["metrics_delta"]["function_count"]
        assert fcount["previous"] == 1
        assert fcount["current"] == 2

    def test_velocity_has_all_fields(self, tmp_path):
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj))
        t.take_snapshot(str(proj))
        v = t.compute_velocity(str(proj))
        assert "velocity_score" in v
        assert "velocity_level" in v
        assert "trend" in v
        assert "metrics_delta" in v
        assert "consecutive_high" in v
        assert "review_required" in v


# ── Trend detection ──────────────────────────────────────────────────


class TestTrend:
    """Tests for trend detection."""

    def test_stable_with_two_snapshots(self, tmp_path):
        """With only 2 snapshots, trend is always stable."""
        proj = _make_project(tmp_path, {"a.py": "x = 1\n"})
        t = _tracker(tmp_path)
        t.take_snapshot(str(proj))
        t.take_snapshot(str(proj))
        v = t.compute_velocity(str(proj))
        assert v["trend"] == "stable"

    def test_accelerating_trend(self, tmp_path):
        """Increasing drift rate = accelerating."""
        proj = _make_project(tmp_path, {"a.py": "def f1():\n    pass\n"})
        t = _tracker(tmp_path)

        # Snapshot 1: baseline
        t.take_snapshot(str(proj))

        # Snapshot 2: small change
        (proj / "a.py").write_text("def f1():\n    pass\ndef f2():\n    pass\n")
        t.take_snapshot(str(proj))

        # Snapshot 3: big change
        (proj / "a.py").write_text(
            "def f1():\n    pass\ndef f2():\n    pass\n"
            "def f3():\n    pass\ndef f4():\n    pass\n"
            "def f5():\n    pass\ndef f6():\n    pass\n"
            "class Big:\n    pass\n"
        )
        t.take_snapshot(str(proj))

        v = t.compute_velocity(str(proj))
        assert v["trend"] == "accelerating"


# ── Consecutive high ─────────────────────────────────────────────────


class TestConsecutiveHigh:
    """Tests for consecutive high-drift detection."""

    def test_consecutive_counter_increments(self, tmp_path):
        """Multiple high-drift sessions increment the counter."""
        db = tmp_path / "consec.db"
        t = DriftTracker(db_path=str(db))
        proj_path = str(tmp_path / "proj")

        # Manually insert snapshots with increasing metrics to simulate high drift
        conn = sqlite3.connect(str(db))
        base_metrics = {
            "import_count": 10, "class_count": 5, "function_count": 10,
            "dependency_count": 5, "complexity_avg": 3.0,
            "public_api_surface": 8, "file_count": 3,
        }
        # Each subsequent snapshot has ~20% more of everything (well above 10%)
        for i in range(4):
            factor = 1.0 + (i * 0.25)
            metrics = {k: (v * factor if isinstance(v, (int, float)) else v)
                       for k, v in base_metrics.items()}
            metrics = {k: (round(v, 2) if isinstance(v, float) else int(v))
                       for k, v in metrics.items()}
            conn.execute(
                "INSERT INTO drift_snapshots (session_id, file_path, timestamp, metrics) "
                "VALUES (?, ?, ?, ?)",
                (f"s{i}", proj_path, f"2026-01-01T0{i}:00:00+00:00", json.dumps(metrics)),
            )
        conn.commit()
        conn.close()

        v = t.compute_velocity(proj_path)
        assert v is not None
        assert v["consecutive_high"] >= 2
        # With 4 snapshots and escalating metrics, at least 2 should be >10%

    def test_review_required_after_three(self, tmp_path):
        """3+ consecutive high sessions → review_required."""
        db = tmp_path / "review.db"
        t = DriftTracker(db_path=str(db))
        proj_path = str(tmp_path / "proj")

        conn = sqlite3.connect(str(db))
        # Create 5 snapshots, each 30% bigger than previous
        for i in range(5):
            factor = 1.0 + (i * 0.35)
            metrics = {
                "import_count": int(10 * factor),
                "class_count": int(5 * factor),
                "function_count": int(10 * factor),
                "dependency_count": int(5 * factor),
                "complexity_avg": round(3.0 * factor, 2),
                "public_api_surface": int(8 * factor),
                "file_count": 3,
            }
            conn.execute(
                "INSERT INTO drift_snapshots (session_id, file_path, timestamp, metrics) "
                "VALUES (?, ?, ?, ?)",
                (f"s{i}", proj_path, f"2026-01-01T0{i}:00:00+00:00", json.dumps(metrics)),
            )
        conn.commit()
        conn.close()

        v = t.compute_velocity(proj_path)
        assert v is not None
        assert v["consecutive_high"] >= 3
        assert v["review_required"] is True
