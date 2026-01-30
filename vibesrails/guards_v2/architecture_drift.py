"""Architecture Drift Guard — Detects violations and AI bypasses."""

import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .dependency_audit import V2GuardIssue

GUARD = "ArchitectureDriftGuard"

LAYER_DEFS: dict[str, tuple[list[str], list[str]]] = {
    "domain": (
        ["domain", "models"],
        [],
    ),
    "infrastructure": (
        ["infrastructure", "adapters"],
        ["domain"],
    ),
    "service": (
        ["services", "application"],
        ["domain"],
    ),
    "presentation": (
        ["api", "routes", "views"],
        ["service"],
    ),
}


def _layer_for_dir(dirname: str) -> str | None:
    """Return layer name for a directory, or None."""
    for layer, (dirs, _) in LAYER_DEFS.items():
        if dirname in dirs:
            return layer
    return None


def _allowed_deps(layer: str) -> list[str]:
    """Return allowed dependency layers for a given layer."""
    for name, (_, deps) in LAYER_DEFS.items():
        if name == layer:
            return deps
    return []


def _all_layer_dirs() -> set[str]:
    """All directory names that map to a layer."""
    result: set[str] = set()
    for _, (dirs, _) in LAYER_DEFS.items():
        result.update(dirs)
    return result


def _dirs_for_layer(layer: str) -> list[str]:
    """Return directory names for a layer."""
    for name, (dirs, _) in LAYER_DEFS.items():
        if name == layer:
            return dirs
    return []


class ArchitectureDriftGuard:
    """Detect architecture drift and AI bypass patterns."""

    def scan(self, project_root: Path) -> list[V2GuardIssue]:
        """Run all architecture checks."""
        issues: list[V2GuardIssue] = []
        issues.extend(self.scan_with_linter(project_root))
        issues.extend(self.scan_ai_bypasses(project_root))
        drift = self._track_drift(
            project_root, len(issues)
        )
        issues.extend(drift)
        return issues

    def scan_with_linter(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Run import-linter if available."""
        issues: list[V2GuardIssue] = []
        config = project_root / ".importlinter"
        if not config.exists():
            generated = self._auto_generate_config(
                project_root
            )
            if generated:
                issues.append(V2GuardIssue(
                    guard=GUARD,
                    severity="info",
                    message=(
                        "Generated .importlinter config "
                        "from directory structure"
                    ),
                    file=str(generated),
                ))
                config = generated
        if not config.exists():
            return issues
        try:
            result = subprocess.run(
                [sys.executable, "-m", "importlinter"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if (
                        "BROKEN" in line
                        or "violated" in line.lower()
                    ):
                        issues.append(V2GuardIssue(
                            guard=GUARD,
                            severity="block",
                            message=f"Import violation: {line}",
                        ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return issues

    def _auto_generate_config(
        self, project_root: Path
    ) -> Path | None:
        """Generate .importlinter from directory structure."""
        detected: dict[str, str] = {}
        for child in project_root.iterdir():
            if child.is_dir():
                layer = _layer_for_dir(child.name)
                if layer:
                    detected[child.name] = layer
        if len(detected) < 2:
            return None
        lines = [
            "[importlinter]",
            f"root_package = {project_root.name}",
            "",
        ]
        contract_idx = 0
        for dirname, layer in detected.items():
            deps = _allowed_deps(layer)
            if not deps:
                continue
            allowed_dirs: list[str] = []
            for dep_layer in deps:
                for d, lyr in detected.items():
                    if lyr == dep_layer:
                        allowed_dirs.append(d)
            if allowed_dirs:
                contract_idx += 1
                cname = f"contract_{contract_idx}"
                lines.append(f"[importlinter:contract:{cname}]")
                lines.append(f"name = {layer} depends on allowed")
                lines.append("type = forbidden")
                lines.append(f"source_modules = {dirname}")
                forbidden = [
                    d for d in detected
                    if d != dirname
                    and d not in allowed_dirs
                ]
                if forbidden:
                    lines.append(
                        "forbidden_modules = "
                        + "\n    ".join(forbidden)
                    )
                lines.append("")
        if contract_idx == 0:
            return None
        config_path = project_root / ".importlinter"
        config_path.write_text("\n".join(lines))
        return config_path

    def detect_layers(
        self, project_root: Path
    ) -> dict[str, str]:
        """Auto-detect layers from directory names."""
        detected: dict[str, str] = {}
        for child in project_root.iterdir():
            if child.is_dir():
                layer = _layer_for_dir(child.name)
                if layer:
                    detected[child.name] = layer
        return detected

    def scan_ai_bypasses(
        self, project_root: Path
    ) -> list[V2GuardIssue]:
        """Detect AI bypass patterns via AST analysis."""
        issues: list[V2GuardIssue] = []
        issues.extend(self._detect_reexport_modules(project_root))
        issues.extend(self._detect_wrapper_classes(project_root))
        issues.extend(self._detect_function_level_imports(project_root))
        issues.extend(self._detect_type_checking_bypass(project_root))
        return issues

    def _detect_reexport_modules(self, root: Path) -> list[V2GuardIssue]:
        from . import architecture_bypass as bp
        return bp.detect_reexport_modules(self, root)

    def _detect_wrapper_classes(self, root: Path) -> list[V2GuardIssue]:
        from . import architecture_bypass as bp
        return bp.detect_wrapper_classes(self, root)

    def _detect_function_level_imports(self, root: Path) -> list[V2GuardIssue]:
        from . import architecture_bypass as bp
        return bp.detect_function_level_imports(self, root)

    def _detect_type_checking_bypass(self, root: Path) -> list[V2GuardIssue]:
        from . import architecture_bypass as bp
        return bp.detect_type_checking_bypass(self, root)

    _SKIP_DIRS = frozenset({
        ".venv", "venv", ".env", "env",
        "node_modules", "__pycache__",
        ".git", ".tox", ".nox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache",
        "site-packages", "dist", "build",
    })

    def _iter_py_files(self, project_root: Path) -> list[Path]:
        results: list[Path] = []
        for py_file in sorted(project_root.rglob("*.py")):
            if not any(part in self._SKIP_DIRS for part in py_file.parts):
                results.append(py_file)
        return results

    def _parse_file(self, path: Path) -> ast.Module | None:
        try:
            return ast.parse(path.read_text())
        except (SyntaxError, UnicodeDecodeError):
            return None

    def _track_drift(self, project_root: Path, current_violations: int) -> list[V2GuardIssue]:
        """Track violation count over time."""
        issues: list[V2GuardIssue] = []
        metrics_dir = project_root / ".vibesrails" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        drift_file = metrics_dir / "architecture_drift.jsonl"
        previous = None
        if drift_file.exists():
            lines = drift_file.read_text().strip().splitlines()
            if lines:
                try:
                    previous = json.loads(lines[-1])
                except json.JSONDecodeError:
                    pass
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "violations": current_violations,
        }
        with open(drift_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        if previous and previous.get("violations", 0) > 0:
            prev_count = previous["violations"]
            if current_violations > prev_count:
                issues.append(V2GuardIssue(
                    guard=GUARD,
                    severity="warn",
                    message=(
                        "Architecture drift increasing: "
                        f"{prev_count} -> {current_violations}"
                    ),
                ))
        return issues

    def take_snapshot(self, project_root: Path) -> Path:
        """Save current import graph snapshot."""
        snapshot_dir = project_root / ".vibesrails"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = (
            snapshot_dir / "architecture_snapshot.json"
        )
        graph: dict[str, list[str]] = {}
        for py_file in self._iter_py_files(project_root):
            tree = self._parse_file(py_file)
            if tree is None:
                continue
            rel = str(py_file.relative_to(project_root))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
            if imports:
                graph[rel] = sorted(set(imports))
        snapshot_path.write_text(
            json.dumps(graph, indent=2, sort_keys=True)
        )
        return snapshot_path

    def generate_report(self, project_root: Path) -> str:
        """Generate a text report of architecture status."""
        issues = self.scan(project_root)
        if not issues:
            return "Architecture: OK (no violations)"
        lines = [f"Architecture Report: {len(issues)} issues"]
        for iss in issues:
            loc = ""
            if iss.file:
                loc = f" [{iss.file}:{iss.line}]" if iss.line else f" [{iss.file}]"
            lines.append(f"  [{iss.severity}]{loc} {iss.message}")
        return "\n".join(lines)
