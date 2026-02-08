"""Drift Velocity Index — measures the SPEED of architectural drift.

Captures project-level code metrics snapshots and computes the rate
of change (velocity) between sessions. High velocity = architecture
transforming fast = likely unsupervised AI-driven changes.

Metrics per snapshot:
  - import_count, class_count, function_count
  - dependency_count (external imports)
  - complexity_avg (simple cyclomatic via AST)
  - public_api_surface (count of public functions/classes)

Persists snapshots in the drift_snapshots SQLite table.
"""

from __future__ import annotations

import ast
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from storage.migrations import get_db_path, migrate

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────

VELOCITY_NORMAL = 5.0       # 0-5%
VELOCITY_WARNING = 15.0     # 5-15%
CONSECUTIVE_THRESHOLD = 10.0  # >10% triggers consecutive counter
CONSECUTIVE_LIMIT = 3         # 3+ consecutive = review_required

# Weights for velocity calculation
_METRIC_WEIGHTS = {
    "import_count": 0.15,
    "class_count": 0.15,
    "function_count": 0.20,
    "dependency_count": 0.15,
    "complexity_avg": 0.20,
    "public_api_surface": 0.15,
}


def classify_velocity(score: float) -> str:
    """Classify velocity score into a level."""
    if score <= VELOCITY_NORMAL:
        return "normal"
    if score <= VELOCITY_WARNING:
        return "warning"
    return "critical"


# ── AST Complexity Visitor ────────────────────────────────────────────


class _ComplexityVisitor(ast.NodeVisitor):
    """Count branching nodes for simple cyclomatic complexity."""

    def __init__(self):
        self.branches = 0

    def visit_If(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.branches += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each and/or adds a branch path
        self.branches += len(node.values) - 1
        self.generic_visit(node)


def _compute_complexity(tree: ast.AST) -> int:
    """Compute simple cyclomatic complexity of an AST.

    Base complexity is 1, plus 1 for each branching node.
    """
    visitor = _ComplexityVisitor()
    visitor.visit(tree)
    return 1 + visitor.branches


# ── AST Metrics Extraction ────────────────────────────────────────────


_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def analyze_file(file_path: Path) -> dict | None:
    """Analyze a single Python file and return metrics.

    Returns None if the file cannot be parsed or exceeds 10 MB.
    """
    try:
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            return None
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, OSError):
        return None

    import_count = 0
    dependency_count = 0
    class_count = 0
    function_count = 0
    public_api = 0

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            import_count += len(node.names)
        elif isinstance(node, ast.ImportFrom):
            import_count += len(node.names) if node.names else 1
            if node.level == 0 and node.module:
                dependency_count += 1
        elif isinstance(node, ast.ClassDef):
            class_count += 1
            if not node.name.startswith("_"):
                public_api += 1
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            function_count += 1
            if not node.name.startswith("_"):
                public_api += 1

    complexity = _compute_complexity(tree)

    return {
        "import_count": import_count,
        "class_count": class_count,
        "function_count": function_count,
        "dependency_count": dependency_count,
        "complexity_avg": float(complexity),
        "public_api_surface": public_api,
    }


_MAX_FILES = 1000


def aggregate_metrics(project_path: Path, *, max_files: int = _MAX_FILES) -> dict:
    """Aggregate metrics across all .py files in a project.

    Stops after max_files to prevent resource exhaustion on huge repos.
    """
    totals = {
        "import_count": 0,
        "class_count": 0,
        "function_count": 0,
        "dependency_count": 0,
        "complexity_avg": 0.0,
        "public_api_surface": 0,
    }

    file_count = 0
    total_complexity = 0.0

    for py_file in sorted(project_path.rglob("*.py")):
        if file_count >= max_files:
            break

        # Skip hidden dirs and __pycache__
        parts = py_file.relative_to(project_path).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue

        metrics = analyze_file(py_file)
        if metrics is None:
            continue

        file_count += 1
        totals["import_count"] += metrics["import_count"]
        totals["class_count"] += metrics["class_count"]
        totals["function_count"] += metrics["function_count"]
        totals["dependency_count"] += metrics["dependency_count"]
        totals["public_api_surface"] += metrics["public_api_surface"]
        total_complexity += metrics["complexity_avg"]

    if file_count > 0:
        totals["complexity_avg"] = round(total_complexity / file_count, 2)

    totals["file_count"] = file_count
    return totals


# ── DriftTracker ──────────────────────────────────────────────────────


class DriftTracker:
    """Tracks architectural drift velocity across sessions."""

    def __init__(self, db_path: str | None = None):
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = get_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        migrate(db_path=str(self._db_path))

    def take_snapshot(self, project_path: str, session_id: str | None = None) -> dict:
        """Capture a metrics snapshot for the project.

        Args:
            project_path: Path to the project directory.
            session_id: Optional session ID to associate with.

        Returns:
            Dict with the aggregated metrics and metadata.
        """
        root = Path(project_path)
        if not root.is_dir():
            return {"error": f"Not a directory: {project_path}"}

        metrics = aggregate_metrics(root)
        now = datetime.now(timezone.utc).isoformat()

        # Store in SQLite
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(
                "INSERT INTO drift_snapshots (session_id, file_path, timestamp, metrics) "
                "VALUES (?, ?, ?, ?)",
                (session_id, str(root), now, json.dumps(metrics)),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "timestamp": now,
            "project_path": str(root),
            "session_id": session_id,
            "metrics": metrics,
        }

    def compute_velocity(self, project_path: str) -> dict | None:
        """Compute drift velocity by comparing the two most recent snapshots.

        Returns None if fewer than 2 snapshots exist.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "SELECT metrics, timestamp FROM drift_snapshots "
                "WHERE file_path = ? ORDER BY timestamp DESC LIMIT 2",
                (str(Path(project_path)),),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        if len(rows) < 2:
            return None

        current = json.loads(rows[0][0])
        previous = json.loads(rows[1][0])

        metrics_delta = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for metric, weight in _METRIC_WEIGHTS.items():
            old_val = previous.get(metric, 0)
            new_val = current.get(metric, 0)

            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                pct_change = abs(new_val - old_val) / max(old_val, 1) * 100
            else:
                pct_change = 0.0

            metrics_delta[metric] = {
                "previous": old_val,
                "current": new_val,
                "change_pct": round(pct_change, 2),
            }
            weighted_sum += pct_change * weight
            total_weight += weight

        velocity_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

        # Determine trend
        trend = self._compute_trend(project_path, velocity_score)

        # Count consecutive high-drift sessions
        consecutive_high = self._count_consecutive_high(project_path)

        return {
            "velocity_score": velocity_score,
            "velocity_level": classify_velocity(velocity_score),
            "trend": trend,
            "metrics_delta": metrics_delta,
            "consecutive_high": consecutive_high,
            "review_required": consecutive_high >= CONSECUTIVE_LIMIT,
        }

    def _compute_trend(self, project_path: str, current_velocity: float) -> str:
        """Determine trend by comparing with previous velocity."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "SELECT metrics FROM drift_snapshots "
                "WHERE file_path = ? ORDER BY timestamp DESC LIMIT 3",
                (str(Path(project_path)),),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        if len(rows) < 3:
            return "stable"

        # Compute velocity between snapshot[-2] and snapshot[-3]
        mid = json.loads(rows[1][0])
        old = json.loads(rows[2][0])

        prev_weighted_sum = 0.0
        prev_total_weight = 0.0
        for metric, weight in _METRIC_WEIGHTS.items():
            old_val = old.get(metric, 0)
            mid_val = mid.get(metric, 0)
            if isinstance(old_val, (int, float)) and isinstance(mid_val, (int, float)):
                pct = abs(mid_val - old_val) / max(old_val, 1) * 100
            else:
                pct = 0.0
            prev_weighted_sum += pct * weight
            prev_total_weight += weight

        prev_velocity = prev_weighted_sum / prev_total_weight if prev_total_weight > 0 else 0.0

        diff = current_velocity - prev_velocity
        if diff > 2.0:
            return "accelerating"
        if diff < -2.0:
            return "decelerating"
        return "stable"

    def _count_consecutive_high(self, project_path: str) -> int:
        """Count consecutive snapshots with velocity > CONSECUTIVE_THRESHOLD.

        Works backward from most recent, counting pairs with >10% drift.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "SELECT metrics FROM drift_snapshots "
                "WHERE file_path = ? ORDER BY timestamp DESC",
                (str(Path(project_path)),),
            )
            rows = cursor.fetchall()
        finally:
            conn.close()

        if len(rows) < 2:
            return 0

        consecutive = 0
        for i in range(len(rows) - 1):
            current = json.loads(rows[i][0])
            previous = json.loads(rows[i + 1][0])

            weighted_sum = 0.0
            total_weight = 0.0
            for metric, weight in _METRIC_WEIGHTS.items():
                old_val = previous.get(metric, 0)
                new_val = current.get(metric, 0)
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    pct = abs(new_val - old_val) / max(old_val, 1) * 100
                else:
                    pct = 0.0
                weighted_sum += pct * weight
                total_weight += weight

            velocity = weighted_sum / total_weight if total_weight > 0 else 0.0

            if velocity > CONSECUTIVE_THRESHOLD:
                consecutive += 1
            else:
                break

        return consecutive

    def get_snapshot_count(self, project_path: str) -> int:
        """Get the number of snapshots for a project."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM drift_snapshots WHERE file_path = ?",
                (str(Path(project_path)),),
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()
