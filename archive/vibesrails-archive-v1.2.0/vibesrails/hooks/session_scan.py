"""SessionStart hook: full project scan with fast V2 + Senior guards.

Runs all fast guards on every .py file in the project (~5s for 400+ files).
No Semgrep, no mutation testing — only AST-based analysis.
Run as: python3 -m vibesrails.hooks.session_scan
"""

import sys
from pathlib import Path

_SKIP_DIRS = frozenset({
    "__pycache__", ".venv", "venv", "node_modules", ".git",
    "build", "dist", ".egg", "site-packages", "checkpoints",
    ".vibesrails", ".claude", "tests", "test",
})


def _collect_py_files(root: Path) -> list[Path]:
    """Collect all Python files, skipping excluded dirs."""
    return [
        py for py in sorted(root.rglob("*.py"))
        if not any(p in py.parts for p in _SKIP_DIRS)
    ]


def _load_v2_guards() -> list:
    """Import and instantiate V2 guard classes."""
    try:
        from vibesrails.guards_v2.api_design import APIDesignGuard
        from vibesrails.guards_v2.complexity import ComplexityGuard
        from vibesrails.guards_v2.database_safety import DatabaseSafetyGuard
        from vibesrails.guards_v2.dead_code import DeadCodeGuard
        from vibesrails.guards_v2.env_safety import EnvSafetyGuard
        from vibesrails.guards_v2.observability import ObservabilityGuard
        from vibesrails.guards_v2.performance import PerformanceGuard
        from vibesrails.guards_v2.type_safety import TypeSafetyGuard

        return [g() for g in (
            DeadCodeGuard, ObservabilityGuard, ComplexityGuard,
            PerformanceGuard, TypeSafetyGuard, APIDesignGuard,
            DatabaseSafetyGuard, EnvSafetyGuard,
        )]
    except ImportError:
        return []


def _load_senior_guards() -> list:
    """Import and return Senior guard instances."""
    try:
        from vibesrails.senior_mode.guards import SeniorGuards
        sg = SeniorGuards()
        return [
            sg.error_guard, sg.hallucination_guard,
            sg.lazy_guard, sg.bypass_guard, sg.resilience_guard,
        ]
    except ImportError:
        return []


def _scan_file_v2(guard, filepath: Path, content: str) -> list:
    """Run a single V2 guard on a file, return issues."""
    try:
        return list(guard.scan_file(filepath, content))
    except Exception:  # noqa: BLE001
        return []


def _scan_file_senior(guard, content: str, fpath: str) -> list:
    """Run a single Senior guard on a file, return issues."""
    try:
        return list(guard.check(content, fpath))
    except Exception:  # noqa: BLE001
        return []


def _tally_issue(issue, blocks: list, warns: list) -> tuple[int, int, int]:
    """Classify an issue and append to appropriate detail list. Returns (b, w, i) counts."""
    if issue.severity == "block":
        blocks.append(f"  \U0001f6d1 {issue.file}:L{issue.line} [{getattr(issue, 'guard', '?')}] {issue.message}")
        return (1, 0, 0)
    if issue.severity == "warn":
        if len(warns) < 20:
            warns.append(f"  \u26a0\ufe0f  {issue.file}:L{issue.line} [{getattr(issue, 'guard', '?')}] {issue.message}")
        return (0, 1, 0)
    return (0, 0, 1)


def main() -> None:
    """Run fast V2 + Senior guards on all project .py files."""
    root = Path.cwd()
    v2_guards = _load_v2_guards()
    senior_guards = _load_senior_guards()

    if not v2_guards and not senior_guards:
        sys.exit(0)

    py_files = _collect_py_files(root)
    blocks_n = warns_n = infos_n = 0
    block_details: list[str] = []
    warn_details: list[str] = []

    for py in py_files:
        try:
            content = py.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = str(py.relative_to(root))

        for guard in v2_guards:
            for issue in _scan_file_v2(guard, py, content):
                issue_file_bak = issue.file
                issue.file = rel
                b, w, i = _tally_issue(issue, block_details, warn_details)
                issue.file = issue_file_bak
                blocks_n += b
                warns_n += w
                infos_n += i

        for guard in senior_guards:
            for issue in _scan_file_senior(guard, content, rel):
                b, w, i = _tally_issue(issue, block_details, warn_details)
                blocks_n += b
                warns_n += w
                infos_n += i

    # Output summary
    sys.stdout.write(
        f"VibesRails session scan: {len(py_files)} files | "
        f"{blocks_n} blocking | {warns_n} warnings | {infos_n} info\n"
    )
    if block_details:
        sys.stdout.write("BLOCKING issues:\n")
        sys.stdout.write("\n".join(block_details) + "\n")
    if warn_details:
        sys.stdout.write("Top warnings:\n")
        sys.stdout.write("\n".join(warn_details) + "\n")
        if warns_n > 20:
            sys.stdout.write(f"  ... and {warns_n - 20} more warnings\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
