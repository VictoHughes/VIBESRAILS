"""
CLI v2 guard handlers — extracted from cli.py.

Handles: _print_v2_issues, _get_staged_diff, _run_senior_v2,
and all --flag dispatch for v2 guards.
"""

import argparse
import logging
import sys
from pathlib import Path

from .scanner import BLUE, GREEN, NC, RED, YELLOW

logger = logging.getLogger(__name__)


def _print_v2_issues(title: str, issues: list) -> None:
    """Print v2 guard issues in a formatted way."""
    logger.info(f"\n{BLUE}VibesRails v2 — {title}{NC}")
    logger.info("=" * 50)
    if not issues:
        logger.info(f"{GREEN}✅ No issues found{NC}")
        return
    blocks = [i for i in issues if i.severity == "block"]
    warns = [i for i in issues if i.severity == "warn"]
    infos = [i for i in issues if i.severity == "info"]
    for issue in blocks:
        loc = f" ({issue.file}:{issue.line})" if issue.file else ""
        logger.error(f"{RED}🚫 [BLOCK]{loc} {issue.message}{NC}")
    for issue in warns:
        loc = f" ({issue.file}:{issue.line})" if issue.file else ""
        logger.warning(f"{YELLOW}⚠️  [WARN]{loc} {issue.message}{NC}")
    for issue in infos:
        loc = f" ({issue.file}:{issue.line})" if issue.file else ""
        logger.info(f"ℹ️  [INFO]{loc} {issue.message}")
    logger.info(f"\n{len(blocks)} blocking | {len(warns)} warnings | {len(infos)} info")


def _get_staged_diff() -> str:
    """Get staged git diff."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception:
        logger.debug("Failed to get staged diff")
        return ""


_SKIP_DIRS = ("__pycache__", ".venv", "venv", "node_modules", ".git", "build", "dist", ".egg")


def _collect_v1_files(root: Path) -> list[tuple[str, str]]:
    """Collect Python files for V1 guard scanning."""
    files = []
    for py_file in root.glob("**/*.py"):
        if any(p in str(py_file) for p in _SKIP_DIRS):
            continue
        try:
            files.append((str(py_file), py_file.read_text()))
        except Exception:
            logger.debug("Failed to read file for senior scan")
    return files[:50]


def _print_guard_status(name: str, issues: list) -> None:
    """Print colored status line for a guard."""
    blocks = sum(1 for i in issues if i.severity == "block")
    warns = sum(1 for i in issues if i.severity == "warn")
    if blocks:
        logger.error(f"{RED}🚫 {name}: {blocks} blocking, {warns} warnings{NC}")
    elif warns:
        logger.warning(f"{YELLOW}⚠️  {name}: {warns} warnings{NC}")
    else:
        logger.info(f"{GREEN}✅ {name}: clean{NC}")


def _get_v2_guards() -> list[tuple[str, object]]:
    """Import and instantiate all V2 guards."""
    from .guards_v2.api_design import APIDesignGuard
    from .guards_v2.architecture_drift import ArchitectureDriftGuard
    from .guards_v2.complexity import ComplexityGuard
    from .guards_v2.database_safety import DatabaseSafetyGuard
    from .guards_v2.dead_code import DeadCodeGuard
    from .guards_v2.dependency_audit import DependencyAuditGuard
    from .guards_v2.docstring import DocstringGuard
    from .guards_v2.env_safety import EnvSafetyGuard
    from .guards_v2.git_workflow import GitWorkflowGuard
    from .guards_v2.observability import ObservabilityGuard
    from .guards_v2.performance import PerformanceGuard
    from .guards_v2.test_integrity import TestIntegrityGuard
    from .guards_v2.type_safety import TypeSafetyGuard

    return [
        ("Dependency Audit", DependencyAuditGuard()),
        ("Performance", PerformanceGuard()),
        ("Complexity", ComplexityGuard()),
        ("Env Safety", EnvSafetyGuard()),
        ("Git Workflow", GitWorkflowGuard()),
        ("Dead Code", DeadCodeGuard()),
        ("Observability", ObservabilityGuard()),
        ("Type Safety", TypeSafetyGuard()),
        ("Docstring", DocstringGuard()),
        ("Database Safety", DatabaseSafetyGuard()),
        ("API Design", APIDesignGuard()),
        ("Test Integrity", TestIntegrityGuard()),
        ("Architecture Drift", ArchitectureDriftGuard()),
    ]


def _run_senior_v2() -> int:
    """Run ALL v2 guards — comprehensive senior scan."""
    from .senior_mode.guards import SeniorGuards

    root = Path.cwd()
    all_issues = []

    logger.info(f"\n{BLUE}╔══════════════════════════════════════════════╗{NC}")
    logger.info(f"{BLUE}║     🎓 VIBESRAILS v2 — SENIOR SCAN          ║{NC}")
    logger.info(f"{BLUE}╚══════════════════════════════════════════════╝{NC}\n")

    logger.info(f"{BLUE}── V1 Guards (Senior Mode) ──{NC}")
    v1_issues = SeniorGuards().check_all(code_diff="", files=_collect_v1_files(root))
    _print_guard_status("Senior Guards", v1_issues)

    logger.info(f"\n{BLUE}── V2 Guards ──{NC}")
    for name, guard in _get_v2_guards():
        issues = guard.scan(root)
        all_issues.extend(issues)
        _print_guard_status(name, issues)

    total_blocks = sum(1 for i in all_issues if i.severity == "block")
    total_warns = sum(1 for i in all_issues if i.severity == "warn")
    logger.info(f"\n{'=' * 46}")
    logger.info(f"Total: {total_blocks} blocking | {total_warns} warnings")

    if total_blocks:
        logger.error(f"\n{RED}🚫 BLOCKED — Fix blocking issues before shipping{NC}")
        return 1
    if total_warns:
        logger.warning(f"\n{YELLOW}⚠️  Warnings found — review before shipping{NC}")
    else:
        logger.info(f"\n{GREEN}✅ All clear — ship it!{NC}")
    return 0


def _run_guard_and_exit(guard_cls, title: str) -> None:
    """Run a single guard, print results, and exit."""
    issues = guard_cls().scan(Path.cwd())
    _print_v2_issues(title, issues)
    sys.exit(1 if any(i.severity == "block" for i in issues) else 0)


def _dispatch_single_guard(args) -> None:
    """Handle individual guard flags (audit_deps, complexity, dead_code, etc.)."""
    if args.audit_deps:
        from .guards_v2.dependency_audit import DependencyAuditGuard
        _run_guard_and_exit(DependencyAuditGuard, "Dependency Audit")

    if args.complexity:
        from .guards_v2.complexity import ComplexityGuard
        _run_guard_and_exit(ComplexityGuard, "Complexity Analysis")

    if args.dead_code:
        from .guards_v2.dead_code import DeadCodeGuard
        _run_guard_and_exit(DeadCodeGuard, "Dead Code Detection")

    if args.env_check:
        from .guards_v2.env_safety import EnvSafetyGuard
        _run_guard_and_exit(EnvSafetyGuard, "Environment Safety")

    if args.pr_check:
        from .guards_v2.pr_checklist import PRChecklistGuard
        guard = PRChecklistGuard()
        guard.scan(Path.cwd())
        logger.info(guard.generate_checklist(_get_staged_diff()))
        sys.exit(0)

    if args.pre_deploy:
        from .guards_v2.pre_deploy import PreDeployGuard
        guard = PreDeployGuard()
        issues = guard.run_all(Path.cwd())
        logger.info(guard.generate_report(issues))
        sys.exit(1 if any(i.severity == "block" for i in issues) else 0)

    if args.upgrade:
        from .advisors.upgrade_advisor import UpgradeAdvisor
        logger.info(UpgradeAdvisor().generate_report(Path.cwd()))
        sys.exit(0)


def _dispatch_pack_commands(args) -> None:
    """Handle install_pack, remove_pack, list_packs commands."""
    if args.install_pack:
        from .community.pack_manager import PackManager
        ok = PackManager().install(args.install_pack, Path.cwd())
        sys.exit(0 if ok else 1)

    if args.remove_pack:
        from .community.pack_manager import PackManager
        ok = PackManager().uninstall(args.remove_pack, Path.cwd())
        sys.exit(0 if ok else 1)

    if args.list_packs:
        from .community.pack_manager import PackManager
        mgr = PackManager()
        installed = mgr.list_installed(Path.cwd())
        available = mgr.list_available()
        logger.info(f"{BLUE}Installed packs:{NC}")
        for p in installed:
            logger.info(f"  - {p.get('pack_id', '?')}")
        if not installed:
            logger.info("  (none)")
        logger.info(f"\n{BLUE}Available official packs:{NC}")
        for p in available:
            logger.info(f"  - {p['id']}: {p['description']}")
        sys.exit(0)


def _dispatch_test_mutation(args) -> None:
    """Handle test_integrity, mutation, mutation_quick, senior_v2 commands."""
    if args.test_integrity:
        from .guards_v2.test_integrity import TestIntegrityGuard
        issues = TestIntegrityGuard().scan(Path.cwd())
        _print_v2_issues("Test Integrity", issues)
        sys.exit(1 if any(i.severity == "block" for i in issues) else 0)

    if args.mutation:
        from .guards_v2.mutation import MutationGuard
        guard = MutationGuard()
        logger.info(guard.generate_report(Path.cwd()))
        issues = guard.scan(Path.cwd())
        _print_v2_issues("Mutation Testing", issues)
        sys.exit(1 if any(i.severity == "block" for i in issues) else 0)

    if args.mutation_quick:
        from .guards_v2.mutation import MutationGuard
        issues = MutationGuard().scan_quick(Path.cwd())
        _print_v2_issues("Mutation Testing (quick)", issues)
        sys.exit(1 if any(i.severity == "block" for i in issues) else 0)

    if args.senior_v2:
        sys.exit(_run_senior_v2())


def dispatch_v2_commands(args: argparse.Namespace) -> bool:
    """Dispatch v2 guard commands. Returns True if a command was handled."""
    _dispatch_single_guard(args)
    _dispatch_pack_commands(args)
    _dispatch_test_mutation(args)
    return False
