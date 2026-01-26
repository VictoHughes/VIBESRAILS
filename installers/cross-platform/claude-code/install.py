#!/usr/bin/env python3
"""
vibesrails - Claude Code integration installer (cross-platform)
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    print("=== VibesRails + Claude Code installer ===")
    print()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version})")
        sys.exit(1)

    # Get project path from args or use current directory
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1]).resolve()
    else:
        project_path = Path.cwd()

    if not project_path.exists():
        print(f"ERROR: Path does not exist: {project_path}")
        sys.exit(1)

    # Step 1: Install vibesrails if not present
    try:
        result = subprocess.run(
            ["vibesrails", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"vibesrails already installed: {result.stdout.strip()}")
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        print("Installing vibesrails...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "vibesrails"],
            capture_output=False,
        )
        if result.returncode != 0:
            print()
            print("ERROR: vibesrails installation failed")
            sys.exit(1)

    print()

    # Verify installation
    try:
        result = subprocess.run(
            ["vibesrails", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("ERROR: vibesrails installation verification failed")
            sys.exit(1)
        print(f"vibesrails {result.stdout.strip()}")
    except FileNotFoundError:
        print("ERROR: vibesrails command not found after installation")
        print("Try: python -m vibesrails --version")
        sys.exit(1)

    print()

    # Step 2: Change to project directory
    os.chdir(project_path)
    print(f"Setting up project: {project_path}")
    print()

    # Check if git repo
    git_dir = project_path / ".git"
    if not git_dir.exists():
        print("WARNING: Not a git repository. Initializing...")
        subprocess.run(["git", "init"], capture_output=False)

    # Step 3: Run smart setup (non-interactive for script)
    print("Running vibesrails --setup...")
    result = subprocess.run(
        ["vibesrails", "--setup", "--force"],
        capture_output=False,
    )

    if result.returncode != 0:
        print()
        print("WARNING: Setup completed with warnings")

    print()
    print("=== Installation complete ===")
    print()

    # List created files
    files_to_check = [
        "vibesrails.yaml",
        "CLAUDE.md",
        ".claude/hooks.json",
        ".git/hooks/pre-commit",
    ]

    print("Files created:")
    for f in files_to_check:
        path = project_path / f
        if path.exists():
            print(f"  {f}")

    print()
    print("Claude Code will now:")
    print("  - Scan code on every commit")
    print("  - Show active plan on session start")
    print("  - Auto-save state before compaction")
    print()
    print("Try: vibesrails --all")
    print()


if __name__ == "__main__":
    main()
