"""Drift metrics extraction — AST analysis and aggregation.

Provides file-level and project-level code metrics used by
DriftTracker to compute drift velocity.

Metrics per file:
  - import_count, class_count, function_count
  - dependency_count (external imports)
  - complexity_avg (simple cyclomatic via AST)
  - public_api_surface (count of public functions/classes)
"""

from __future__ import annotations

import ast
from pathlib import Path

# ── Velocity Thresholds ──────────────────────────────────────────────

VELOCITY_NORMAL = 5.0       # 0-5%
VELOCITY_WARNING = 15.0     # 5-15%


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
