"""PostToolUse hook: verify files AFTER Claude writes or runs commands.

- Write/Edit on .py: V1 scanner (regex) + V2 guards (AST) + Senior guards
- Bash after git commit: DiffSizeGuard + TestCoverageGuard + ArchitectureDriftGuard

Warn-only (always exit 0) -- we just report issues.
Run as: python3 -m vibesrails.hooks.post_tool_use
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# ── V2 guards (per-file, AST-based) ──────────────────────────────
# Heavy guards (mutation, dependency_audit, vulture, git_workflow, pre_deploy,
# pr_checklist, env_safety) are left for --senior-v2 CLI.
_FAST_V2_GUARDS = None


def _get_fast_v2_guards():  # noqa: ANN202
    """Lazy-import fast V2 guard classes."""
    global _FAST_V2_GUARDS  # noqa: PLW0603
    if _FAST_V2_GUARDS is not None:
        return _FAST_V2_GUARDS
    try:
        from vibesrails.guards_v2.api_design import APIDesignGuard
        from vibesrails.guards_v2.complexity import ComplexityGuard
        from vibesrails.guards_v2.database_safety import DatabaseSafetyGuard
        from vibesrails.guards_v2.dead_code import DeadCodeGuard
        from vibesrails.guards_v2.env_safety import EnvSafetyGuard
        from vibesrails.guards_v2.observability import ObservabilityGuard
        from vibesrails.guards_v2.performance import PerformanceGuard
        from vibesrails.guards_v2.type_safety import TypeSafetyGuard

        _FAST_V2_GUARDS = (
            DeadCodeGuard, ObservabilityGuard, ComplexityGuard,
            PerformanceGuard, TypeSafetyGuard, APIDesignGuard,
            DatabaseSafetyGuard, EnvSafetyGuard,
        )
    except ImportError:
        _FAST_V2_GUARDS = ()
    return _FAST_V2_GUARDS


def _run_v2_guards(filepath: Path, content: str) -> list[str]:
    """Run fast V2 guards on a single file."""
    lines: list[str] = []
    for guard_cls in _get_fast_v2_guards():
        guard = guard_cls()
        try:
            issues = guard.scan_file(filepath, content)
        except Exception:  # noqa: BLE001
            continue
        for issue in issues:
            sev = issue.severity.upper()
            lines.append(f"  - L{issue.line} [{sev}] [{issue.guard}] {issue.message}")
    return lines


# ── Senior guards (per-file, regex+AST) ──────────────────────────
def _run_senior_guards(filepath: str, content: str) -> list[str]:
    """Run Senior Mode guards on a single file."""
    lines: list[str] = []
    try:
        from vibesrails.senior_mode.guards import SeniorGuards

        sg = SeniorGuards()
        issues = []
        issues.extend(sg.error_guard.check(content, filepath))
        issues.extend(sg.hallucination_guard.check(content, filepath))
        issues.extend(sg.lazy_guard.check(content, filepath))
        issues.extend(sg.bypass_guard.check(content, filepath))
        issues.extend(sg.resilience_guard.check(content, filepath))
        for issue in issues:
            sev = issue.severity.upper()
            lines.append(f"  - L{issue.line} [{sev}] [{issue.guard}] {issue.message}")
    except Exception:  # noqa: BLE001
        pass
    return lines


# ── Post-commit guards (project-level) ───────────────────────────
def _run_post_commit_guards() -> list[str]:
    """Run guards relevant after a git commit."""
    lines: list[str] = []
    try:
        from vibesrails.senior_mode.guards import SeniorGuards

        sg = SeniorGuards()

        # DiffSizeGuard — check last commit size
        diff = subprocess.run(
            ["git", "diff", "HEAD~1", "--", "*.py"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        if diff:
            for issue in sg.diff_guard.check(diff):
                lines.append(f"  - [{issue.severity.upper()}] [{issue.guard}] {issue.message}")

            # TestCoverageGuard — code vs test ratio
            test_diff = subprocess.run(
                ["git", "diff", "HEAD~1", "--", "test_*", "tests/"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            for issue in sg.test_guard.check(diff, test_diff):
                lines.append(f"  - [{issue.severity.upper()}] [{issue.guard}] {issue.message}")
    except Exception:  # noqa: BLE001
        pass

    # ArchitectureDriftGuard — check layer violations on changed files
    try:
        from vibesrails.guards_v2.architecture_drift import ArchitectureDriftGuard

        changed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "--", "*.py"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()
        guard = ArchitectureDriftGuard()
        for fpath in changed:
            p = Path(fpath)
            if p.is_file():
                try:
                    content = p.read_text(encoding="utf-8")
                    for issue in guard.scan_file(p, content):
                        sev = issue.severity.upper()
                        lines.append(f"  - {fpath}:L{issue.line} [{sev}] [{issue.guard}] {issue.message}")
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass

    return lines


# ── Main dispatch ─────────────────────────────────────────────────
def _handle_write_edit(tool_input: dict) -> None:
    """Scan a written/edited Python file with V1 + V2 + Senior guards."""
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py") or not os.path.isfile(file_path):
        sys.exit(0)

    basename = os.path.basename(file_path)
    all_issues: list[str] = []

    # V1 scanner (regex patterns from vibesrails.yaml)
    try:
        from vibesrails.scanner import load_config, scan_file
        config = load_config()
        for r in scan_file(file_path, config):
            all_issues.append(f"  - L{r.line} [{r.level}] {r.message}")
    except Exception:  # noqa: BLE001
        pass

    # V2 guards (AST-based)
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        all_issues.extend(_run_v2_guards(Path(file_path), content))
        all_issues.extend(_run_senior_guards(file_path, content))
    except Exception:  # noqa: BLE001
        pass

    if all_issues:
        sys.stdout.write(
            f"\U0001f7e1 VibesRails: {len(all_issues)} issue(s) in {basename}:\n"
        )
        sys.stdout.write("\n".join(all_issues) + "\n")
    else:
        sys.stdout.write(f"\U0001f7e2 VibesRails: {basename} scanned clean\n")


def _handle_bash(tool_input: dict) -> None:
    """After a git commit, run post-commit guards."""
    command = tool_input.get("command", "")
    if "git commit" not in command and "git merge" not in command:
        sys.exit(0)

    issues = _run_post_commit_guards()
    if issues:
        sys.stdout.write(
            f"\U0001f7e1 VibesRails post-commit: {len(issues)} issue(s):\n"
        )
        sys.stdout.write("\n".join(issues) + "\n")


def main() -> None:
    """CLI entry point -- reads JSON from stdin, always exits 0."""
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name in ("Write", "Edit"):
        _handle_write_edit(tool_input)
    elif tool_name == "Bash":
        _handle_bash(tool_input)

    sys.exit(0)


if __name__ == "__main__":
    main()
