#!/usr/bin/env python3
"""
vibesrails - Claude Code integration installer (cross-platform)

Installs vibesrails AND sets up Claude Code integration:
  - vibesrails.yaml   (security patterns)
  - CLAUDE.md         (Claude Code instructions)
  - .claude/hooks.json (session automation)
  - .git/hooks/pre-commit (security scanning)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path


def banner():
    print("+" + "=" * 48 + "+")
    print("|  VibesRails + Claude Code Installer             |")
    print("+" + "=" * 48 + "+")
    print()


def find_templates_dir() -> Path:
    """Locate the templates/claude-code directory relative to this script."""
    script_dir = Path(__file__).resolve().parent
    # cross-platform/claude-code/install.py -> ../../templates/claude-code
    templates = script_dir.parent.parent / "templates" / "claude-code"
    if templates.exists():
        return templates
    # Fallback: complete-package
    complete = script_dir.parent.parent / "complete-package" / "claude-code"
    if complete.exists():
        return complete
    return templates  # Will fail with clear error later


def copy_if_missing(src: Path, dst: Path, label: str) -> str:
    """Copy src to dst if dst doesn't exist. Returns status string."""
    if dst.exists():
        return f"  ~ {label} (already exists, skipped)"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"  + {label}"


def main():
    banner()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version})")
        sys.exit(1)

    # Get project path
    project_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not project_path.exists():
        print(f"ERROR: Path does not exist: {project_path}")
        sys.exit(1)

    templates_dir = find_templates_dir()
    if not templates_dir.exists():
        print(f"ERROR: Templates not found at: {templates_dir}")
        print("Make sure the installers/ directory structure is intact.")
        sys.exit(1)

    # Step 1: Install vibesrails
    print("[1/4] Checking vibesrails...")
    try:
        result = subprocess.run(
            ["vibesrails", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"      Already installed: {result.stdout.strip()}")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print("      Installing vibesrails...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "vibesrails"],
            capture_output=False,
        )
        if result.returncode != 0:
            print("ERROR: vibesrails installation failed")
            sys.exit(1)
    print()

    # Step 2: Setup project directory
    os.chdir(project_path)
    print(f"[2/4] Project: {project_path}")

    git_dir = project_path / ".git"
    if not git_dir.exists():
        print("      Initializing git repository...")
        subprocess.run(["git", "init"], capture_output=True)
    print()

    # Step 3: Copy Claude Code templates
    print("[3/4] Installing Claude Code integration...")

    files_to_copy = [
        ("vibesrails.yaml", "vibesrails.yaml", "vibesrails.yaml (security patterns)"),
        ("CLAUDE.md", "CLAUDE.md", "CLAUDE.md (Claude Code instructions)"),
        (
            ".claude/hooks.json",
            ".claude/hooks.json",
            ".claude/hooks.json (session automation)",
        ),
    ]

    for src_rel, dst_rel, label in files_to_copy:
        src = templates_dir / src_rel
        dst = project_path / dst_rel
        if not src.exists():
            print(f"  ! {label} (template missing, skipped)")
            continue
        print(copy_if_missing(src, dst, label))
    print()

    # Step 4: Install git pre-commit hook
    print("[4/4] Installing git pre-commit hook...")
    try:
        subprocess.run(
            ["vibesrails", "--hook", "--force"],
            capture_output=True,
            text=True,
        )
        print("      Pre-commit hook installed")
    except Exception:
        print("      (skipped - run 'vibesrails --hook' manually)")
    print()

    # Summary
    print("=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print("  Files installed:")
    for check in ["vibesrails.yaml", "CLAUDE.md", ".claude/hooks.json", ".git/hooks/pre-commit"]:
        p = project_path / check
        if p.exists():
            print(f"    {check}")
    print()
    print("  Claude Code will now:")
    print("    - Scan code on every commit")
    print("    - Show active plan on session start")
    print("    - Auto-save state before compaction")
    print("    - Remind about scanning on first edit")
    print()
    print("  Next: vibesrails --all")
    print()


if __name__ == "__main__":
    main()
