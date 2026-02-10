#!/usr/bin/env python3
"""
vibesrails CLI - Entry point for pip-installed package.

Handles argparse setup and dispatches to sub-modules.
Setup/config functions are in cli_setup.py.
V2 guard handlers are in cli_v2.py.
"""

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .cli_setup import (
    find_config,
    get_default_config_path,  # noqa: F401 - re-exported for tests
    init_config,
    install_hook,
    run_senior_mode,
    uninstall,
)
from .cli_v2 import dispatch_v2_commands
from .learn_runner import handle_learn_command
from .scan_runner import run_scan
from .scanner import (
    NC,
    RED,
    get_all_python_files,
    get_staged_files,
    load_config,
    show_patterns,
    validate_config,
)

logger = logging.getLogger(__name__)


def _parse_args():
    """Parse command-line arguments and return the parsed args."""
    parser = argparse.ArgumentParser(
        description="VibesRails 2.1.0 — by SM",
        epilog="Examples: vibesrails --all | --show | --stats | --learn | --watch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", "-v", action="version",
                        version=f"VibesRails {__version__} — by SM")

    # --- Setup & Config ---
    g_setup = parser.add_argument_group("Setup & Config")
    g_setup.add_argument("--init", action="store_true", help="Initialize vibesrails.yaml")
    g_setup.add_argument("--setup", action="store_true", help="Smart auto-setup (analyzes project)")
    g_setup.add_argument("--hook", action="store_true", help="Install git pre-commit hook")
    g_setup.add_argument("--uninstall", action="store_true", help="Remove vibesrails from project")
    g_setup.add_argument("--force", action="store_true", help="Force overwrite existing config")
    g_setup.add_argument("--config", "-c", help="Path to vibesrails.yaml")
    g_setup.add_argument("--validate", action="store_true", help="Validate YAML config")

    # --- Scanning ---
    g_scan = parser.add_argument_group("Scanning")
    g_scan.add_argument("--all", action="store_true", help="Scan all Python files")
    g_scan.add_argument("--file", "-f", help="Scan specific file")
    g_scan.add_argument("--senior", action="store_true",
                        help="Run Senior Mode (architecture + guards + review)")
    g_scan.add_argument("--senior-v2", action="store_true", help="Run ALL v2 guards (comprehensive scan)")
    g_scan.add_argument("--show", action="store_true", help="Show all active patterns")
    g_scan.add_argument("--stats", action="store_true", help="Show scan statistics and metrics")
    g_scan.add_argument("--fixable", action="store_true", help="Show auto-fixable patterns")

    # --- Auto-fix ---
    g_fix = parser.add_argument_group("Auto-fix")
    g_fix.add_argument("--fix", action="store_true", help="Auto-fix simple patterns")
    g_fix.add_argument("--dry-run", action="store_true", help="Show what --fix would change")
    g_fix.add_argument("--no-backup", action="store_true", help="Don't create .bak files with --fix")

    # --- Specialized Guards ---
    g_guards = parser.add_argument_group("Specialized Guards")
    g_guards.add_argument("--audit-deps", action="store_true", help="Audit dependencies for CVEs and risks")
    g_guards.add_argument("--complexity", action="store_true", help="Analyze code complexity")
    g_guards.add_argument("--dead-code", action="store_true", help="Detect unused code")
    g_guards.add_argument("--env-check", action="store_true", help="Check environment safety")
    g_guards.add_argument("--test-integrity", action="store_true",
                          help="Detect fake/lazy tests (over-mocking, no assertions)")
    g_guards.add_argument("--mutation", action="store_true",
                          help="Mutation testing -- verify tests catch real bugs")
    g_guards.add_argument("--mutation-quick", action="store_true",
                          help="Mutation testing on changed functions only")
    g_guards.add_argument("--pr-check", action="store_true", help="Generate PR review checklist")
    g_guards.add_argument("--pre-deploy", action="store_true", help="Pre-deployment verification")

    # --- Community & Extensions ---
    g_community = parser.add_argument_group("Community & Extensions")
    g_community.add_argument("--install-pack", metavar="PACK", help="Install community pack (@user/repo)")
    g_community.add_argument("--remove-pack", metavar="PACK", help="Remove installed pack")
    g_community.add_argument("--list-packs", action="store_true", help="List installed and available packs")
    g_community.add_argument("--upgrade", action="store_true", help="Check for dependency upgrades")
    g_community.add_argument("--learn", action="store_true", help="Claude-powered pattern discovery")

    # --- Session Management ---
    g_session = parser.add_argument_group("Session Management")
    g_session.add_argument("--watch", action="store_true", help="Live scanning on file save")
    g_session.add_argument("--queue", metavar="MSG", help="Send a task to other Claude Code sessions")
    g_session.add_argument("--inbox", metavar="MSG", help="Add instruction to mobile inbox")
    g_session.add_argument("--throttle-status", action="store_true",
                           help="Show write throttle counter")
    g_session.add_argument("--throttle-reset", action="store_true",
                           help="Reset write throttle counter")

    # --- Guardian ---
    g_guardian = parser.add_argument_group("Guardian (AI mode)")
    g_guardian.add_argument("--guardian-stats", action="store_true",
                            help="Show AI coding block statistics")

    parser.add_argument("--about", action="store_true", help=argparse.SUPPRESS)

    return parser.parse_args()


def _handle_info_commands(args) -> None:
    """Handle stats/info commands. Exits if handled."""
    if args.about:
        print(f"VibesRails {__version__} — by SM")
        print("ABH AMH.")
        print("")
        print("First program. 22 tests to 1812.")
        print("pip install vibesrails")
        sys.exit(0)

    if args.throttle_status:
        from .hooks.throttle import get_writes_since_check
        count = get_writes_since_check(Path(".vibesrails"))
        logger.info("Writes since last check: %d/5", count)
        sys.exit(0)

    if args.throttle_reset:
        from .hooks.throttle import reset_state
        reset_state(Path(".vibesrails"))
        logger.info("Throttle reset.")
        sys.exit(0)

    if args.guardian_stats:
        from .ai_guardian import show_guardian_stats
        show_guardian_stats()
        sys.exit(0)

    if args.stats:
        from .metrics import MetricsCollector
        MetricsCollector().show_stats()
        sys.exit(0)

    if args.fixable:
        from .autofix import show_fixable_patterns
        show_fixable_patterns()
        sys.exit(0)

    if args.watch:
        from .watch import run_watch_mode
        config_path = Path(args.config) if args.config else find_config()
        sys.exit(0 if run_watch_mode(config_path) else 1)


def _handle_setup_commands(args) -> None:
    """Handle setup/install commands. Exits if handled."""
    if args.learn:
        from .learn import run_learn_mode
        sys.exit(0 if run_learn_mode() else 1)

    if args.setup:
        from .smart_setup import run_smart_setup_cli
        sys.exit(0 if run_smart_setup_cli(force=args.force, dry_run=args.dry_run) else 1)

    if args.init:
        sys.exit(0 if init_config() else 1)
    if args.hook:
        sys.exit(0 if install_hook() else 1)
    if args.uninstall:
        sys.exit(0 if uninstall() else 1)


def _handle_hook_commands(args) -> None:
    """Handle V2 inter-session hook commands. Exits if handled."""
    if args.queue:
        from .hooks.queue_processor import add_task
        queue_file = Path(".claude/queue.jsonl")
        task_id = add_task(queue_file, args.queue, source="cli")
        logger.info("Task queued [%s]: %s", task_id, args.queue)
        sys.exit(0)

    if args.inbox:
        from .hooks.inbox import create_inbox
        inbox_file = Path(".claude/inbox.md")
        create_inbox(inbox_file)
        with inbox_file.open("a") as f:
            f.write(args.inbox + "\n")
        logger.info("Added to inbox: %s", args.inbox)
        sys.exit(0)


def _handle_standalone_commands(args):
    """Handle commands that don't need a config file. Returns True if handled."""
    _handle_info_commands(args)
    _handle_hook_commands(args)
    dispatch_v2_commands(args)
    _handle_setup_commands(args)


def _handle_config_commands(args, config, files):
    """Handle commands that require a loaded config."""
    if args.validate:
        sys.exit(0 if validate_config(config) else 1)

    if args.show:
        show_patterns(config)
        sys.exit(0)

    if args.senior:
        sys.exit(run_senior_mode(files))

    if args.fix or args.dry_run:
        from .autofix import run_autofix
        run_autofix(config, files, dry_run=args.dry_run, backup=not args.no_backup)
        if args.dry_run:
            sys.exit(0)
        logger.info("")

    sys.exit(run_scan(config, files))


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    # Handle learn command (positional argument)
    if len(sys.argv) > 1 and sys.argv[1] == "learn":
        sys.exit(handle_learn_command())

    args = _parse_args()

    _handle_standalone_commands(args)

    # Find config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = find_config()

    if not config_path or not config_path.exists():
        logger.error("%sERROR: No vibesrails.yaml found%s", RED, NC)
        logger.info("Run: vibesrails --init")
        sys.exit(1)

    try:
        config = load_config(config_path)
    except ValueError as e:
        logger.error("%s%s%s", RED, e, NC)
        sys.exit(1)

    # Determine files to scan
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error("%sError: file not found: %s%s", RED, args.file, NC)
            sys.exit(1)
        try:
            file_path.read_bytes()[:1]  # test read permission
        except PermissionError:
            logger.error("%sError: permission denied: %s%s", RED, args.file, NC)
            sys.exit(1)
        files = [args.file]
    elif args.all:
        files = get_all_python_files()
    else:
        files = get_staged_files()

    _handle_config_commands(args, config, files)


if __name__ == "__main__":
    main()
