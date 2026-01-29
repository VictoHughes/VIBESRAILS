#!/usr/bin/env python3
"""
VibesRails v2.0 - Source installer (cross-platform)
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    print("+" + "=" * 48 + "+")
    print("|  VibesRails v2.0 Installer (source)             |")
    print("|  YAML-driven security + code quality scanner    |")
    print("+" + "=" * 48 + "+")
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
        # Try to checkout v2 branch
        subprocess.run(
            ["git", "checkout", "v2.0"],
            cwd=install_path,
            capture_output=True,
        )
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
        subprocess.run(
            ["git", "checkout", "v2.0"],
            cwd=install_path,
            capture_output=True,
        )

    print()

    # Install in development mode with all extras
    print("Installing vibesrails v2.0 from source with all extras...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", f"{install_path}[all]"],
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
    print("=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print(f"Installed at: {install_path}")
    print()
    print("v2.0 Features:")
    print("  - 15 security & quality guards")
    print("  - Senior Mode (AI coding safety)")
    print("  - Architecture mapping")
    print("  - Community pattern packs")
    print()
    print("Next steps:")
    print("  cd your-project")
    print("  vibesrails --setup")
    print()


if __name__ == "__main__":
    main()
