#!/usr/bin/env python3
"""
vibesrails CLI - Entry point for pip-installed package.

Handles config discovery, initialization, and delegates to scanner.
"""

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .scanner import (
    BLUE,
    GREEN,
    NC,
    RED,
    YELLOW,
    get_all_python_files,
    get_staged_files,
    load_config,
    scan_file,
    show_patterns,
    validate_config,
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
    print("\nNext steps:")
    print(f"  1. Edit {target} to customize patterns")
    print("  2. Run: vibesrails --hook  (install git pre-commit)")
    print("  3. Code freely - vibesrails runs on every commit")
    return True


def uninstall() -> bool:
    """Uninstall vibesrails from current project."""
    removed = []

    # Remove vibesrails.yaml if exists
    config_file = Path("vibesrails.yaml")
    if config_file.exists():
        config_file.unlink()
        removed.append(str(config_file))

    # Remove hook
    hook_path = Path(".git/hooks/pre-commit")
    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            # Remove vibesrails lines from hook
            lines = content.split("\n")
            new_lines = [line for line in lines if "vibesrails" not in line.lower()]
            new_content = "\n".join(new_lines).strip()

            if new_content and new_content != "#!/bin/bash":
                hook_path.write_text(new_content)
                print(f"{YELLOW}Removed vibesrails from pre-commit hook{NC}")
            else:
                hook_path.unlink()
                removed.append(str(hook_path))

    # Remove .vibesrails directory (guardian logs, etc.)
    vibesrails_dir = Path(".vibesrails")
    if vibesrails_dir.exists():
        import shutil
        shutil.rmtree(vibesrails_dir)
        removed.append(str(vibesrails_dir))

    if removed:
        print(f"{GREEN}Removed:{NC}")
        for f in removed:
            print(f"  - {f}")
        print(f"\n{GREEN}vibesrails uninstalled from this project{NC}")
        print("To uninstall the package: pip uninstall vibesrails")
    else:
        print(f"{YELLOW}Nothing to uninstall{NC}")

    return True


def install_hook(architecture_enabled: bool = False) -> bool:
    """Install git pre-commit hook.

    Args:
        architecture_enabled: If True, also run architecture check (import-linter)
    """
    git_dir = Path(".git")
    if not git_dir.exists():
        print(f"{RED}ERROR: Not a git repository{NC}")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    # Architecture check command (resilient - doesn't fail if tool missing)
    arch_check = ""
    if architecture_enabled:
        arch_check = """
# Architecture check (optional - fails silently if not installed)
if command -v lint-imports &> /dev/null; then
    echo "Checking architecture..."
    lint-imports || echo "Architecture check failed (non-blocking)"
fi
"""

    # Check if hook already exists
    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            # Update hook if architecture enabled and not present
            if architecture_enabled and "lint-imports" not in content:
                content = content.rstrip() + "\n" + arch_check
                hook_path.write_text(content)
                print(f"{YELLOW}Updated pre-commit hook with architecture check{NC}")
            else:
                print(f"{YELLOW}VibesRails hook already installed{NC}")
            return True

        # Append to existing hook
        print(f"{YELLOW}Appending to existing pre-commit hook{NC}")
        with open(hook_path, "a") as f:
            f.write("\n\n# vibesrails security check\nvibesrails\n")
            if architecture_enabled:
                f.write(arch_check)
    else:
        # Create new hook with smart command detection
        hook_content = f"""#!/bin/bash
# VibesRails pre-commit hook
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
{arch_check}"""
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

    print(f"{GREEN}Git hook installed at {hook_path}{NC}")
    return True


def run_scan(config: dict, files: list[str]) -> int:
    """Run scan with Semgrep + VibesRails orchestration and return exit code."""
    from .guardian import (
        apply_guardian_rules,
        get_ai_agent_name,
        log_guardian_block,
        print_guardian_status,
        should_apply_guardian,
    )
    from .result_merger import ResultMerger
    from .semgrep_adapter import SemgrepAdapter

    print(f"{BLUE}VibesRails - Security Scan{NC}")
    print("=" * 30)

    # Show guardian status if active
    print_guardian_status(config)

    if not files:
        print(f"{GREEN}No Python files to scan{NC}")
        return 0

    print(f"Scanning {len(files)} file(s)...\n")

    # Initialize Semgrep adapter
    semgrep_config = config.get("semgrep", {"enabled": True, "preset": "auto"})
    semgrep = SemgrepAdapter(semgrep_config)

    # Ensure Semgrep is installed (auto-install if needed)
    semgrep_available = False
    if semgrep.enabled:
        if not semgrep.is_installed():
            print("📦 Installing Semgrep (enhanced scanning)...")
            semgrep_available = semgrep.install(quiet=False)
            if semgrep_available:
                print(f"{GREEN}✅ Semgrep installed{NC}\n")
            else:
                print(f"{YELLOW}⚠️  Semgrep install failed, continuing with VibesRails only{NC}\n")
        else:
            semgrep_available = True

    # Run Semgrep scan (if available)
    semgrep_results = []
    if semgrep_available and semgrep.enabled:
        print("🔍 Running Semgrep scan...")
        semgrep_results = semgrep.scan(files)
        print(f"   Found {len(semgrep_results)} issue(s)")

    # Run VibesRails scan
    print("🔍 Running VibesRails scan...")
    vibesrails_results = []
    guardian_active = should_apply_guardian(config)
    agent_name = get_ai_agent_name() if guardian_active else None

    for filepath in files:
        results = scan_file(filepath, config)

        # Apply guardian rules if active
        if guardian_active:
            results = apply_guardian_rules(results, config, filepath)

        vibesrails_results.extend(results)

    print(f"   Found {len(vibesrails_results)} issue(s)\n")

    # Merge results
    merger = ResultMerger()
    unified_results, stats = merger.merge(semgrep_results, vibesrails_results)

    # Display statistics
    if semgrep_results or vibesrails_results:
        print(f"{BLUE}📊 Scan Statistics:{NC}")
        print(f"   Semgrep:     {stats['semgrep']} issues")
        print(f"   VibesRails:  {stats['vibesrails']} issues")
        if stats['duplicates'] > 0:
            print(f"   Duplicates:  {stats['duplicates']} (merged)")
        print(f"   Total:       {stats['total']} unique issues\n")

    # Categorize and display results
    blocking = [r for r in unified_results if r.level == "BLOCK"]
    warnings = [r for r in unified_results if r.level == "WARN"]

    # Display by category
    categories = merger.group_by_category(unified_results)
    for category, results in categories.items():
        category_emoji = {
            "security": "🔒",
            "architecture": "🏗️",
            "guardian": "🛡️",
            "bugs": "🐛",
            "general": "⚙️"
        }.get(category, "•")

        print(f"{BLUE}{category_emoji} {category.upper()}:{NC}")
        for r in results:
            color = RED if r.level == "BLOCK" else YELLOW
            level_text = f"{color}{r.level}{NC}"
            source_badge = f"[{r.source}]"

            print(f"{level_text} {r.file}:{r.line} {source_badge}")
            print(f"  [{r.rule_id}] {r.message}")

            # Log guardian blocks for statistics
            if guardian_active and r.level == "BLOCK" and r.source == "VIBESRAILS":
                # Create fake ScanResult for compatibility
                from .scanner import ScanResult
                scan_result = ScanResult(
                    file=r.file,
                    line=r.line,
                    pattern_id=r.rule_id,
                    message=r.message,
                    level=r.level
                )
                log_guardian_block(scan_result, agent_name)
        print()

    print("=" * 30)
    print(f"BLOCKING: {len(blocking)} | WARNINGS: {len(warnings)}")

    if blocking:
        print(f"\n{RED}Fix blocking issues or use: git commit --no-verify{NC}")
        return 1

    print(f"\n{GREEN}VibesRails: PASSED{NC}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="VibesRails - Scale up your vibe coding safely | From KIONOS™ (free tools)",
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
  vibesrails --guardian-stats  Show AI coding block statistics
        """,
    )
    parser.add_argument("--version", "-v", action="version",
                        version=f"VibesRails {__version__} - From KIONOS™ (free tools) - Developed by SM")
    parser.add_argument("--init", action="store_true", help="Initialize vibesrails.yaml")
    parser.add_argument("--hook", action="store_true", help="Install git pre-commit hook")
    parser.add_argument("--uninstall", action="store_true", help="Remove vibesrails from project")
    parser.add_argument("--setup", action="store_true", help="Smart auto-setup (analyzes project)")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing config")
    parser.add_argument("--validate", action="store_true", help="Validate YAML config")
    parser.add_argument("--show", action="store_true", help="Show all patterns")
    parser.add_argument("--all", action="store_true", help="Scan all Python files")
    parser.add_argument("--file", "-f", help="Scan specific file")
    parser.add_argument("--config", "-c", help="Path to vibesrails.yaml")
    parser.add_argument("--learn", action="store_true", help="Claude-powered pattern discovery")
    parser.add_argument("--watch", action="store_true", help="Live scanning on file save")
    parser.add_argument("--guardian-stats", action="store_true", help="Show AI coding block statistics")
    parser.add_argument("--fix", action="store_true", help="Auto-fix simple patterns")
    parser.add_argument("--dry-run", action="store_true", help="Show what --fix would change")
    parser.add_argument("--no-backup", action="store_true", help="Don't create .bak files with --fix")
    parser.add_argument("--fixable", action="store_true", help="Show auto-fixable patterns")
    args = parser.parse_args()

    # Handle guardian stats
    if args.guardian_stats:
        from .guardian import show_guardian_stats
        show_guardian_stats()
        sys.exit(0)

    # Handle fixable patterns list
    if args.fixable:
        from .autofix import show_fixable_patterns
        show_fixable_patterns()
        sys.exit(0)

    # Handle watch mode
    if args.watch:
        from .watch import run_watch_mode
        config_path = Path(args.config) if args.config else find_config()
        sys.exit(0 if run_watch_mode(config_path) else 1)

    # Handle learn mode (doesn't need config, uses Claude API)
    if args.learn:
        from .learn import run_learn_mode
        sys.exit(0 if run_learn_mode() else 1)

    # Handle smart setup (auto-detects project type)
    if args.setup:
        from .smart_setup import run_smart_setup_cli
        sys.exit(0 if run_smart_setup_cli(force=args.force, dry_run=args.dry_run) else 1)

    # Handle init (doesn't need config)
    if args.init:
        sys.exit(0 if init_config() else 1)

    # Handle hook (doesn't need config)
    if args.hook:
        sys.exit(0 if install_hook() else 1)

    # Handle uninstall
    if args.uninstall:
        sys.exit(0 if uninstall() else 1)

    # Find config
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = find_config()

    if not config_path or not config_path.exists():
        print(f"{RED}ERROR: No vibesrails.yaml found{NC}")
        print("\nRun: vibesrails --init")
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

    # Handle auto-fix
    if args.fix or args.dry_run:
        from .autofix import run_autofix
        run_autofix(config, files, dry_run=args.dry_run, backup=not args.no_backup)
        if args.dry_run:
            sys.exit(0)
        # After fix, re-scan to show remaining issues
        print()

    sys.exit(run_scan(config, files))


if __name__ == "__main__":
    main()
