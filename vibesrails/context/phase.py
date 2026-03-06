"""Project phase detection — identify where a project is in its lifecycle.

Phases:
  0 DECIDE     — Architecture decisions, ADR, contracts (no code yet)
  1 SKELETON   — Walking skeleton, minimal end-to-end path
  2 FLESH_OUT  — Real logic, growing test coverage
  3 STABILIZE  — Shadow run, metrics, bug fixes only
  4 DEPLOY     — Progressive confidence, monitoring, production

Detection is based on filesystem and git signals. Each phase has
prerequisite gates; the highest phase whose gates are ALL satisfied
is the detected phase. Manual override via methodology.yaml.
"""

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

logger = logging.getLogger(__name__)

_SKIP_DIRS = {"__pycache__", ".venv", "venv", ".git", "build", "dist", ".egg", "node_modules"}


class ProjectPhase(IntEnum):
    """Project lifecycle phases (ordered)."""
    DECIDE = 0
    SKELETON = 1
    FLESH_OUT = 2
    STABILIZE = 3
    DEPLOY = 4


@dataclass
class PhaseSignals:
    """Raw filesystem/git signals for phase detection."""
    has_readme: bool = False
    has_claude_md: bool = False
    has_adr: bool = False
    has_decisions_md: bool = False
    has_contracts: bool = False  # typed functions with return annotations
    test_count: int = 0
    has_integration_tests: bool = False
    module_count: int = 0  # .py files in src/package dirs
    has_ci: bool = False
    has_docker: bool = False
    has_monitoring: bool = False
    release_tag_count: int = 0
    has_changelog: bool = False
    has_vibesrails_yaml: bool = False


@dataclass
class PhaseResult:
    """Result of phase detection."""
    phase: ProjectPhase
    signals: PhaseSignals
    missing_for_next: list[str] = field(default_factory=list)
    is_override: bool = False


# ── Gate definitions ────────────────────────────────────────────

# Each gate maps phase N → N+1. ALL conditions must be True to pass.
# Conditions are (signal_name, check_fn) pairs.

_GATES: dict[str, list[tuple[str, callable]]] = {
    "decide_to_skeleton": [
        ("has_readme", lambda s: s.has_readme),
        ("has_decisions", lambda s: s.has_adr or s.has_decisions_md),
        ("has_contracts", lambda s: s.has_contracts),
    ],
    "skeleton_to_flesh": [
        ("test_count >= 5", lambda s: s.test_count >= 5),
        ("module_count >= 3", lambda s: s.module_count >= 3),
    ],
    "flesh_to_stabilize": [
        ("test_count >= 50", lambda s: s.test_count >= 50),
        ("has_ci", lambda s: s.has_ci),
        ("has_changelog", lambda s: s.has_changelog),
    ],
    "stabilize_to_deploy": [
        ("has_monitoring", lambda s: s.has_monitoring),
        ("release_tags >= 1", lambda s: s.release_tag_count >= 1),
    ],
}

_GATE_ORDER = [
    ("decide_to_skeleton", ProjectPhase.SKELETON),
    ("skeleton_to_flesh", ProjectPhase.FLESH_OUT),
    ("flesh_to_stabilize", ProjectPhase.STABILIZE),
    ("stabilize_to_deploy", ProjectPhase.DEPLOY),
]


# ── PhaseDetector ───────────────────────────────────────────────


class PhaseDetector:
    """Detect project lifecycle phase from filesystem and git signals."""

    def __init__(self, root: Path):
        self.root = root

    def collect_signals(self) -> PhaseSignals:
        """Collect all filesystem/git signals."""
        r = self.root
        signals = PhaseSignals()

        # File existence checks
        signals.has_readme = (r / "README.md").exists() or (r / "README.rst").exists()
        signals.has_claude_md = (r / "CLAUDE.md").exists()
        signals.has_vibesrails_yaml = (
            (r / "vibesrails.yaml").exists() or (r / "vibesafe.yaml").exists()
        )
        signals.has_changelog = (r / "CHANGELOG.md").exists()

        # ADR directory
        for adr_dir in ["ADR", "adr", "docs/adr", "docs/ADR", "docs/decisions"]:
            path = r / adr_dir
            if path.is_dir() and any(path.iterdir()):
                signals.has_adr = True
                break

        # decisions.md
        for loc in ["docs/decisions.md", "decisions.md", ".vibesrails/decisions.md"]:
            if (r / loc).exists():
                signals.has_decisions_md = True
                break

        # Typed functions (contracts) — sample up to 20 .py files
        signals.has_contracts = self._detect_contracts()

        # Test count
        signals.test_count = self._count_tests()

        # Integration tests
        signals.has_integration_tests = self._detect_integration_tests()

        # Module count (non-test .py files)
        signals.module_count = self._count_modules()

        # CI
        signals.has_ci = (
            (r / ".github" / "workflows").is_dir()
            or (r / ".gitlab-ci.yml").exists()
            or (r / ".circleci").is_dir()
            or (r / "Jenkinsfile").exists()
        )

        # Docker
        signals.has_docker = (
            (r / "Dockerfile").exists()
            or (r / "docker-compose.yml").exists()
            or (r / "docker-compose.yaml").exists()
        )

        # Monitoring
        signals.has_monitoring = self._detect_monitoring()

        # Release tags
        signals.release_tag_count = self._count_release_tags()

        return signals

    def detect(self) -> PhaseResult:
        """Detect current project phase."""
        # Check for manual override first
        override = self._read_methodology_override()
        if override is not None:
            signals = self.collect_signals()
            return PhaseResult(
                phase=ProjectPhase(override),
                signals=signals,
                missing_for_next=self._missing_for_next(
                    ProjectPhase(override), signals
                ),
                is_override=True,
            )

        signals = self.collect_signals()
        phase = ProjectPhase.DECIDE  # Start at lowest

        for gate_name, target_phase in _GATE_ORDER:
            conditions = _GATES[gate_name]
            if all(check(signals) for _, check in conditions):
                phase = target_phase
            else:
                break  # Can't skip phases

        missing = self._missing_for_next(phase, signals)
        return PhaseResult(phase=phase, signals=signals, missing_for_next=missing)

    # ── Private helpers ─────────────────────────────────────────

    def _detect_contracts(self) -> bool:
        """Check if project uses type annotations (return type hints)."""
        count = 0
        for py_file in self._iter_py_files(limit=30):
            try:
                content = py_file.read_text(errors="ignore")
                # Look for "def foo(...) -> Type:" pattern
                if re.search(r"def \w+\([^)]*\)\s*->\s*\w", content):
                    count += 1
                    if count >= 3:
                        return True
            except OSError:
                continue
        return False

    def _count_tests(self) -> int:
        """Count tests via pytest --collect-only (fast) or file heuristic."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", "--timeout=30"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            combined = result.stdout + "\n" + result.stderr
            for line in reversed(combined.splitlines()):
                match = re.search(r"(\d+)\s+tests?\s", line)
                if match:
                    return int(match.group(1))
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Fallback: count test_ functions in test files
        count = 0
        tests_dir = self.root / "tests"
        if tests_dir.is_dir():
            for py_file in tests_dir.rglob("test_*.py"):
                try:
                    content = py_file.read_text(errors="ignore")
                    count += len(re.findall(r"^def test_", content, re.MULTILINE))
                except OSError:
                    continue
        return count

    def _detect_integration_tests(self) -> bool:
        """Check for integration test markers."""
        tests_dir = self.root / "tests"
        if not tests_dir.is_dir():
            return False

        # Check for integration test directories
        for name in ["integration", "test_integration", "e2e", "test_e2e"]:
            if (tests_dir / name).is_dir():
                return True

        # Check for integration markers in test files (sample 10)
        for i, py_file in enumerate(tests_dir.rglob("test_*.py")):
            if i >= 10:
                break
            try:
                content = py_file.read_text(errors="ignore")
                if "integration" in content.lower() or "@pytest.mark.e2e" in content:
                    return True
            except OSError:
                continue
        return False

    def _count_modules(self) -> int:
        """Count non-test Python modules."""
        count = 0
        for py_file in self._iter_py_files(limit=500):
            if not py_file.name.startswith("test_") and "_test.py" not in py_file.name:
                count += 1
        return count

    def _detect_monitoring(self) -> bool:
        """Check for monitoring/observability dependencies."""
        patterns = ["sentry", "datadog", "prometheus", "opentelemetry", "newrelic"]
        # Check requirements files
        for req_file in ["requirements.txt", "requirements.in", "pyproject.toml"]:
            path = self.root / req_file
            if path.exists():
                try:
                    content = path.read_text(errors="ignore").lower()
                    if any(p in content for p in patterns):
                        return True
                except OSError:
                    continue
        return False

    def _count_release_tags(self) -> int:
        """Count git tags matching version patterns."""
        try:
            result = subprocess.run(
                ["git", "tag", "--list", "v*"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                tags = [t for t in result.stdout.strip().splitlines() if t]
                return len(tags)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return 0

    def _read_methodology_override(self) -> int | None:
        """Read manual phase override from .vibesrails/methodology.yaml."""
        yaml_path = self.root / ".vibesrails" / "methodology.yaml"
        if not yaml_path.exists():
            return None
        try:
            import yaml
            config = yaml.safe_load(yaml_path.read_text())
            phase_val = (config or {}).get("methodology", {}).get("current_phase", "auto")
            if phase_val == "auto" or phase_val is None:
                return None
            return int(phase_val)
        except Exception:
            return None

    def _iter_py_files(self, limit: int = 100):
        """Iterate .py files in the project, skipping common non-source dirs."""
        count = 0
        for py_file in sorted(self.root.rglob("*.py")):
            if any(skip in py_file.parts for skip in _SKIP_DIRS):
                continue
            yield py_file
            count += 1
            if count >= limit:
                break

    @staticmethod
    def _missing_for_next(phase: ProjectPhase, signals: PhaseSignals) -> list[str]:
        """Return list of unmet conditions for the next phase gate."""
        if phase >= ProjectPhase.DEPLOY:
            return []

        # Find the gate to the next phase
        gate_index = phase  # DECIDE=0 → gate[0], SKELETON=1 → gate[1], etc.
        if gate_index >= len(_GATE_ORDER):
            return []

        gate_name, _ = _GATE_ORDER[gate_index]
        conditions = _GATES[gate_name]

        missing = []
        for label, check in conditions:
            if not check(signals):
                missing.append(label)
        return missing
