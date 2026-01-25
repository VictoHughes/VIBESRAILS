#!/usr/bin/env python3
"""
vibesrails CLI - Entry point for pip-installed package.

Handles config discovery, initialization, and delegates to scanner.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .scanner import (
    scan_file,
    load_config,
    show_patterns,
    validate_config,
    get_staged_files,
    get_all_python_files,
    ScanResult,
    RED, YELLOW, GREEN, BLUE, NC,
)


def find_config() -> Path | None:
    """Find vibesrails.yaml in project or user home."""
    # Priority order:
    # 1. ./vibesrails.yaml (project root)
    # 2. ./config/vibesrails.yaml
    # 3. ~/.config/vibesrails/vibesrails.yaml

    candidates = [
        Path("vibesrails.yaml"),
        Path("config/vibesrails.yaml"),
        Path.home() / ".config" / "vibesrails" / "vibesrails.yaml",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def get_default_config_path() -> Path:
    """Get path to bundled default.yaml."""
    return Path(__file__).parent / "config" / "default.yaml"


def init_config(target: Path = Path("vibesrails.yaml")) -> bool:
    """Initialize vibesrails.yaml in current project."""
    if target.exists():
        print(f"{YELLOW}vibesrails.yaml already exists{NC}")
        return False

    default_config = get_default_config_path()
    if not default_config.exists():
        print(f"{RED}ERROR: Default config not found at {default_config}{NC}")
        return False

    shutil.copy(default_config, target)
    print(f"{GREEN}Created {target}{NC}")
    print(f"\nNext steps:")
    print(f"  1. Edit {target} to customize patterns")
    print(f"  2. Run: vibesrails --hook  (install git pre-commit)")
    print(f"  3. Code freely - vibesrails runs on every commit")
    return True


def install_hook() -> bool:
    """Install git pre-commit hook."""
    git_dir = Path(".git")
    if not git_dir.exists():
        print(f"{RED}ERROR: Not a git repository{NC}")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    # Check if hook already exists
    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            print(f"{YELLOW}vibesrails hook already installed{NC}")
            return True

        # Append to existing hook
        print(f"{YELLOW}Appending to existing pre-commit hook{NC}")
        with open(hook_path, "a") as f:
            f.write("\n\n# vibesrails security check\nvibesrails\n")
    else:
        # Create new hook with smart command detection
        hook_content = """#!/bin/bash
# vibesrails pre-commit hook
# Scale up your vibe coding - safely

# Find vibesrails command (PATH, local venv, or python -m)
if command -v vibesrails &> /dev/null; then
    vibesrails
elif [ -f ".venv/bin/vibesrails" ]; then
    .venv/bin/vibesrails
elif [ -f "venv/bin/vibesrails" ]; then
    venv/bin/vibesrails
else
    python3 -m vibesrails
fi
"""
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

    print(f"{GREEN}Git hook installed at {hook_path}{NC}")
    return True


def run_scan(config: dict, files: list[str]) -> int:
    """Run scan and return exit code."""
    print(f"{BLUE}vibesrails - Security Scan{NC}")
    print("=" * 30)

    if not files:
        print(f"{GREEN}No Python files to scan{NC}")
        return 0

    print(f"Scanning {len(files)} file(s)...\n")

    all_results = []
    for filepath in files:
        results = scan_file(filepath, config)
        all_results.extend(results)

    # Report results
    blocking = [r for r in all_results if r.level == "BLOCK"]
    warnings = [r for r in all_results if r.level == "WARN"]

    for r in blocking:
        print(f"{RED}BLOCK{NC} {r.file}:{r.line}")
        print(f"  [{r.pattern_id}] {r.message}")

    for r in warnings:
        print(f"{YELLOW}WARN{NC} {r.file}:{r.line}")
        print(f"  [{r.pattern_id}] {r.message}")

    print("=" * 30)
    print(f"BLOCKING: {len(blocking)} | WARNINGS: {len(warnings)}")

    if blocking:
        print(f"\n{RED}Fix blocking issues or use: git commit --no-verify{NC}")
        return 1

    print(f"\n{GREEN}vibesrails: PASSED{NC}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="vibesrails - Scale up your vibe coding safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vibesrails              Scan staged files (default)
  vibesrails --all        Scan entire project
  vibesrails --show       Show configured patterns
  vibesrails --init       Initialize vibesrails.yaml
  vibesrails --hook       Install git pre-commit hook
  vibesrails --learn      Claude-powered pattern discovery
  vibesrails --watch      Live scanning on file save
        """,
    )
    parser.add_argument("--version", "-v", action="version", version=f"vibesrails {__version__}")
    parser.add_argument("--init", action="store_true", help="Initialize vibesrails.yaml")
    parser.add_argument("--hook", action="store_true", help="Install git pre-commit hook")
    parser.add_argument("--validate", action="store_true", help="Validate YAML config")
    parser.add_argument("--show", action="store_true", help="Show all patterns")
    parser.add_argument("--all", action="store_true", help="Scan all Python files")
    parser.add_argument("--file", "-f", help="Scan specific file")
    parser.add_argument("--config", "-c", help="Path to vibesrails.yaml")
    parser.add_argument("--learn", action="store_true", help="Claude-powered pattern discovery")
    parser.add_argument("--watch", action="store_true", help="Live scanning on file save")
    args = parser.parse_args()

    # Handle watch mode
    if args.watch:
        from .watch import run_watch_mode
        config_path = Path(args.config) if args.config else find_config()
        sys.exit(0 if run_watch_mode(config_path) else 1)

    # Handle learn mode (doesn't need config, uses Claude API)
    if args.learn:
        from .learn import run_learn_mode
        sys.exit(0 if run_learn_mode() else 1)

    # Handle init (doesn't need config)
    if args.init:
        sys.exit(0 if init_config() else 1)

    # Handle hook (doesn't need config)
    if args.hook:
        sys.exit(0 if install_hook() else 1)

    # Find config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = find_config()

    if not config_path or not config_path.exists():
        print(f"{RED}ERROR: No vibesrails.yaml found{NC}")
        print(f"\nRun: vibesrails --init")
        sys.exit(1)

    config = load_config(config_path)

    if args.validate:
        sys.exit(0 if validate_config(config) else 1)

    if args.show:
        show_patterns(config)
        sys.exit(0)

    # Determine files to scan
    if args.file:
        files = [args.file] if Path(args.file).exists() else []
    elif args.all:
        files = get_all_python_files()
    else:
        files = get_staged_files()

    sys.exit(run_scan(config, files))


if __name__ == "__main__":
    main()
