#!/usr/bin/env python3
"""
vibesrails - Source installer (cross-platform)
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    print("=== VibesRails source installer ===")
    print()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version})")
        sys.exit(1)

    # Check git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: git is required")
        print("Install from: https://git-scm.com")
        sys.exit(1)

    print(f"Python: {sys.version.split()[0]}")
    print()

    # Determine install path
    home = Path.home()
    install_path = home / ".vibesrails"

    # Clone or update
    if install_path.exists():
        print(f"Updating existing installation at {install_path}...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=install_path,
            capture_output=False,
        )
        if result.returncode != 0:
            print("WARNING: git pull failed, continuing with existing code")
    else:
        print(f"Cloning to {install_path}...")
        result = subprocess.run(
            ["git", "clone", "https://github.com/VictoHughes/VIBESRAILS.git", str(install_path)],
            capture_output=False,
        )
        if result.returncode != 0:
            print()
            print("ERROR: Clone failed")
            sys.exit(1)

    print()

    # Install in development mode
    print("Installing in development mode...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(install_path)],
        capture_output=False,
    )

    if result.returncode != 0:
        print()
        print("ERROR: Installation failed")
        sys.exit(1)

    # Verify
    print()
    result = subprocess.run(
        ["vibesrails", "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"Installed: {result.stdout.strip()}")
    else:
        print("vibesrails installed (run: python -m vibesrails --version)")

    print()
    print("=== Installation complete ===")
    print()
    print("Next steps:")
    print("  cd your-project")
    print("  vibesrails --setup")
    print()


if __name__ == "__main__":
    main()
