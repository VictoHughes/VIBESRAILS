#!/usr/bin/env python3
"""
vibesrails - pip installer (cross-platform)
"""
import subprocess
import sys


def main():
    print("=== VibesRails pip installer ===")
    print()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version})")
        sys.exit(1)

    print(f"Python: {sys.version.split()[0]}")
    print()

    # Install vibesrails
    print("Installing vibesrails...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "vibesrails"],
        capture_output=False,
    )

    if result.returncode != 0:
        print()
        print("ERROR: Installation failed")
        print("Try: pip install --user vibesrails")
        sys.exit(1)

    print()
    print("=== Installation complete ===")
    print()
    print("Next steps:")
    print("  cd your-project")
    print("  vibesrails --setup")
    print()


if __name__ == "__main__":
    main()
