"""sync-memory — Auto-generate PROJECT_MEMORY.md from runtime data.

Regenerates sections wrapped in <!-- AUTO:name --> / <!-- /AUTO:name --> markers.
Preserves everything outside these markers (manual sections like Decisions Log).

Data sources:
  - SQLite DB (~/.vibesrails/sessions.db): learning engine, drift, sessions
  - vibesrails.yaml: assertions
  - Git + filesystem: context detection
  - Static AST: module dependency flows
"""

import ast
import json
import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_SKIP_DIRS = ("__pycache__", ".venv", "venv", ".git", "build", "dist", ".egg")


# ── DB helpers (fail gracefully if no DB) ─────────────────────────


def _get_db_connection() -> sqlite3.Connection | None:
    """Try to connect to the vibesrails DB. Returns None if unavailable."""
    try:
        from storage.migrations import get_db_path

        db_path = get_db_path()
        if not db_path.exists():
            return None
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


# ── Section generators ────────────────────────────────────────────


def generate_health(root: Path) -> str:
    """Generate Project Health section from sessions DB."""
    conn = _get_db_connection()
    if not conn:
        return "_No session data yet. Use VibesRails MCP tools to start collecting._"

    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, AVG(entropy_score) AS avg_e "
            "FROM sessions"
        ).fetchone()
        sessions_count = row["cnt"] or 0
        avg_entropy = row["avg_e"]

        if sessions_count == 0:
            return "_No sessions recorded yet._"

        # Brief score trend from learning_events
        brief_rows = conn.execute(
            "SELECT event_data FROM learning_events "
            "WHERE event_type = 'brief_score' "
            "ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        brief_scores = []
        for r in brief_rows:
            data = json.loads(r["event_data"])
            if "score" in data:
                brief_scores.append(data["score"])

        # Classify entropy
        if avg_entropy is not None:
            if avg_entropy < 0.3:
                level = "safe"
            elif avg_entropy < 0.6:
                level = "warning"
            elif avg_entropy < 0.8:
                level = "elevated"
            else:
                level = "critical"
        else:
            level = "unknown"

        lines = [
            f"- **Sessions tracked:** {sessions_count}",
            f"- **Average entropy:** {avg_entropy:.2f} ({level})"
            if avg_entropy is not None
            else "- **Average entropy:** N/A",
        ]

        if brief_scores:
            avg_brief = sum(brief_scores) / len(brief_scores)
            lines.append(
                f"- **Recent brief score:** {avg_brief:.0f}/100"
                f" (last {len(brief_scores)} sessions)"
            )

        return "\n".join(lines)
    finally:
        conn.close()


def generate_drift(root: Path) -> str:
    """Generate Architecture Drift section from drift_snapshots DB."""
    conn = _get_db_connection()
    if not conn:
        return "_No drift data yet. Run `check_drift` MCP tool to start tracking._"

    try:
        rows = conn.execute(
            "SELECT metrics, timestamp FROM drift_snapshots "
            "WHERE file_path = ? ORDER BY timestamp DESC LIMIT 3",
            (str(root),),
        ).fetchall()

        if len(rows) < 2:
            return "_Need at least 2 snapshots. Run `check_drift` MCP tool._"

        current = json.loads(rows[0]["metrics"])
        previous = json.loads(rows[1]["metrics"])

        weights = {
            "import_count": 0.15,
            "class_count": 0.15,
            "function_count": 0.20,
            "dependency_count": 0.15,
            "complexity_avg": 0.20,
            "public_api_surface": 0.15,
        }

        deltas = []
        weighted_sum = 0.0
        for metric, weight in weights.items():
            old_val = previous.get(metric, 0)
            new_val = current.get(metric, 0)
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                pct = abs(new_val - old_val) / max(old_val, 1) * 100
            else:
                pct = 0.0
            weighted_sum += pct * weight
            if pct > 1.0:
                direction = "+" if new_val > old_val else "-"
                deltas.append(f"{metric}: {direction}{pct:.1f}%")

        velocity = round(weighted_sum, 1)
        if velocity < 5:
            level = "normal"
        elif velocity < 15:
            level = "warning"
        else:
            level = "critical"

        # Trend from 3 snapshots
        trend = "stable"
        if len(rows) >= 3:
            third = json.loads(rows[2]["metrics"])
            prev_velocity = 0.0
            for metric, weight in weights.items():
                old_v = third.get(metric, 0)
                mid_v = previous.get(metric, 0)
                if isinstance(old_v, (int, float)) and isinstance(mid_v, (int, float)):
                    pct = abs(mid_v - old_v) / max(old_v, 1) * 100
                else:
                    pct = 0.0
                prev_velocity += pct * weight
            if velocity > prev_velocity * 1.2:
                trend = "accelerating"
            elif velocity < prev_velocity * 0.8:
                trend = "decelerating"

        lines = [
            f"- **Velocity:** {velocity}% ({level})",
            f"- **Trend:** {trend}",
            f"- **Last snapshot:** {rows[0]['timestamp'][:19]}",
        ]
        if deltas:
            lines.append(f"- **Moving metrics:** {', '.join(deltas)}")

        return "\n".join(lines)
    finally:
        conn.close()


def generate_quality(root: Path) -> str:
    """Generate Quality Trends section from learning engine."""
    conn = _get_db_connection()
    if not conn:
        return "_No quality data yet. Use VibesRails tools to start profiling._"

    try:
        # Developer profile
        profile_rows = conn.execute(
            "SELECT metric_name, metric_value FROM developer_profile"
        ).fetchall()

        if not profile_rows:
            return "_No developer profile yet. Use scan tools across sessions._"

        profile = {}
        for row in profile_rows:
            profile[row["metric_name"]] = json.loads(row["metric_value"])

        lines = []

        # Top violations
        top_v = profile.get("top_violations", [])
        if top_v:
            items = [f"{v['guard']} ({v['count']})" for v in top_v[:5]]
            lines.append(f"- **Top violations:** {', '.join(items)}")

        # Hallucination rate (halluc_count / sessions — per session average)
        halluc = profile.get("hallucination_rate", 0)
        if halluc:
            lines.append(f"- **Hallucination rate:** {halluc:.1f}/session")

        # Improvement rate
        improvement = profile.get("improvement_rate")
        if improvement is not None:
            direction = "improving" if improvement > 0 else "regressing"
            lines.append(
                f"- **Brief score trend:** {improvement:+.0f}% ({direction})"
            )

        # Common drift areas
        drift_areas = profile.get("common_drift_areas", [])
        if drift_areas:
            areas = [f"{d['metric']} ({d['count']})" for d in drift_areas[:3]]
            lines.append(f"- **Common drift areas:** {', '.join(areas)}")

        # Sessions count
        sessions = profile.get("sessions_count", 0)
        if sessions:
            lines.append(f"- **Profiled over:** {sessions} sessions")

        return "\n".join(lines) if lines else "_Profile empty._"
    finally:
        conn.close()


def generate_flows(root: Path) -> str:
    """Generate Execution Flows section via static AST import analysis."""
    packages = ["vibesrails", "core", "tools", "adapters", "storage"]
    dep_map: dict[str, list[str]] = {}

    for pkg in packages:
        pkg_dir = root / pkg
        if not pkg_dir.is_dir():
            continue
        for py_file in sorted(pkg_dir.rglob("*.py")):
            if any(skip in py_file.parts for skip in _SKIP_DIRS):
                continue
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            rel = py_file.relative_to(root)
            module = str(rel).replace("/", ".").removesuffix(".py")
            if module.endswith(".__init__"):
                module = module.removesuffix(".__init__")

            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue

            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    if top in packages and top != pkg:
                        imports.add(top)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in packages and top != pkg:
                            imports.add(top)

            if imports:
                dep_map.setdefault(pkg, set()).update(imports)

    if not dep_map:
        return "_No cross-package dependencies detected._"

    lines = ["```"]
    for pkg in packages:
        deps = dep_map.get(pkg)
        if deps:
            lines.append(f"{pkg} -> {', '.join(sorted(deps))}")
        elif (root / pkg).is_dir():
            lines.append(f"{pkg} -> (standalone)")
    lines.append("```")

    # Data flow summary
    lines.append("")
    lines.append("**Data flow:** CLI (`vibesrails/`) -> Guards (`vibesrails/guards_v2/`)"
                 " -> Scanner (`vibesrails/scanner.py`)")
    lines.append("**MCP flow:** `mcp_server.py` -> Tools (`tools/`) -> Core (`core/`)"
                 " -> Storage (`storage/`)")

    return "\n".join(lines)


def generate_baselines(root: Path) -> str:
    """Generate Baselines section from vibesrails.yaml assertions."""
    yaml_path = root / "vibesrails.yaml"
    if not yaml_path.exists():
        return "_No vibesrails.yaml found._"

    try:
        import yaml

        config = yaml.safe_load(yaml_path.read_text())
    except Exception:
        return "_Could not parse vibesrails.yaml._"

    assertions = config.get("assertions", {})
    if not assertions:
        return "_No assertions configured in vibesrails.yaml._"

    lines = []

    # Values
    values = assertions.get("values", {})
    if values:
        items = [f"`{k}`: {v}" for k, v in values.items()]
        lines.append(f"- **Values:** {', '.join(items)}")

    # Rules
    rules = assertions.get("rules", {})
    if rules:
        items = [f"`{k}`: {'enabled' if v else 'disabled'}"
                 for k, v in rules.items() if not isinstance(v, list)]
        if items:
            lines.append(f"- **Rules:** {', '.join(items)}")

    # Baselines
    baselines = assertions.get("baselines", {})
    if baselines:
        items = [f"`{k}`: {v}" for k, v in baselines.items()]
        lines.append(f"- **Baselines:** {', '.join(items)}")

    return "\n".join(lines) if lines else "_No assertions data._"


def generate_context(root: Path) -> str:
    """Generate Session Context section from context detector."""
    try:
        from vibesrails.context.detector import ContextDetector
        from vibesrails.context.scorer import ContextScorer

        detector = ContextDetector(root)
        signals = detector.detect()
        result = ContextScorer().score(signals)

        lines = [
            f"- **Mode:** {result.mode.value} (score: {result.score:.2f},"
            f" confidence: {result.confidence:.0%})",
        ]
        if signals.branch_name:
            lines.append(
                f"- **Branch:** {signals.branch_name} ({signals.branch_type})"
            )
        if signals.uncommitted_count is not None:
            lines.append(f"- **Uncommitted files:** {signals.uncommitted_count}")
        if signals.commit_frequency is not None:
            lines.append(f"- **Commit frequency:** {signals.commit_frequency}/hour")
        if signals.diff_spread is not None:
            lines.append(f"- **Diff spread:** {signals.diff_spread} directories")

        return "\n".join(lines)
    except Exception as e:
        return f"_Context detection unavailable: {e}_"


# ── Section map ───────────────────────────────────────────────────


_SECTION_GENERATORS = {
    "health": generate_health,
    "drift": generate_drift,
    "quality": generate_quality,
    "flows": generate_flows,
    "baselines": generate_baselines,
    "context": generate_context,
}


# ── Merge engine ──────────────────────────────────────────────────


def merge_sections(existing: str, root: Path) -> str:
    """Replace AUTO sections in existing content, preserve everything else."""
    result = existing

    for section_name, generator in _SECTION_GENERATORS.items():
        open_tag = f"<!-- AUTO:{section_name} -->"
        close_tag = f"<!-- /AUTO:{section_name} -->"

        if open_tag in result and close_tag in result:
            new_content = generator(root)
            pattern = re.compile(
                re.escape(open_tag) + r".*?" + re.escape(close_tag),
                re.DOTALL,
            )
            replacement = f"{open_tag}\n{new_content}\n{close_tag}"
            result = pattern.sub(replacement, result)

    return result


# ── Template ──────────────────────────────────────────────────────


_TEMPLATE = """\
# Project Memory — VibesRails

_Auto-generated by `vibesrails --sync-memory`. Manual sections are preserved._

<!-- AUTO:health -->
## Project Health
_No data yet._
<!-- /AUTO:health -->

<!-- AUTO:drift -->
## Architecture Drift
_No data yet._
<!-- /AUTO:drift -->

<!-- AUTO:quality -->
## Quality Trends
_No data yet._
<!-- /AUTO:quality -->

<!-- AUTO:flows -->
## Execution Flows
_No data yet._
<!-- /AUTO:flows -->

<!-- AUTO:baselines -->
## Baselines & Assertions
_No data yet._
<!-- /AUTO:baselines -->

<!-- AUTO:context -->
## Session Context
_No data yet._
<!-- /AUTO:context -->

## Decisions Log

_Record architecture decisions here. This section is preserved across syncs._

| Date | Decision | Context |
|------|----------|---------|
| | | |

## Known Issues

_Track known bugs and workarounds here. This section is preserved across syncs._

- (none)
"""


# ── Main entry point ──────────────────────────────────────────────


def sync_memory(root: Path, dry_run: bool = False) -> str:
    """Sync PROJECT_MEMORY.md with auto-generated content.

    Creates the file from template if it doesn't exist.
    Returns the new content. Writes to disk unless dry_run=True.
    """
    memory_md = root / "PROJECT_MEMORY.md"

    if not memory_md.exists():
        existing = _TEMPLATE
    else:
        existing = memory_md.read_text()

    new_content = merge_sections(existing, root)

    if dry_run:
        return new_content

    if not memory_md.exists() or new_content != existing:
        memory_md.write_text(new_content)
        logger.info("PROJECT_MEMORY.md updated")
    else:
        logger.info("PROJECT_MEMORY.md already up to date")

    return new_content
