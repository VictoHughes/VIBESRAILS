#!/usr/bin/env python3
"""
VibesRails v2.0 - pip installer (cross-platform)
"""
import subprocess
import sys


def main():
    print("+" + "=" * 48 + "+")
    print("|  VibesRails v2.0 Installer (pip)               |")
    print("|  YAML-driven security + code quality scanner   |")
    print("+" + "=" * 48 + "+")
    print()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"ERROR: Python 3.10+ required (you have {sys.version})")
        sys.exit(1)

    print(f"Python: {sys.version.split()[0]}")
    print()

    # Install vibesrails v2 with all extras
    print("Installing vibesrails v2.0 with all extras...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "vibesrails[all]>=2.0.0"],
        capture_output=False,
    )

    if result.returncode != 0:
        print()
        print("ERROR: Installation failed")
        print('Try: pip install --user "vibesrails[all]>=2.0.0"')
        sys.exit(1)

    print()
    print("=" * 50)
    print("  Installation complete!")
    print("=" * 50)
    print()
    print("v2.0 Features:")
    print("  - 15 security & quality guards")
    print("  - Senior Mode (AI coding safety)")
    print("  - Architecture mapping")
    print("  - Performance, complexity & dependency audits")
    print("  - Type safety & API design guards")
    print("  - Community pattern packs")
    print()
    print("CLI Commands:")
    print("  vibesrails --all          Scan entire project")
    print("  vibesrails --setup        Setup new project")
    print("  vibesrails --senior       Run Senior Mode analysis")
    print("  vibesrails --show         Show configured patterns")
    print("  vibesrails --watch        Live scanning mode")
    print("  vibesrails --learn        AI pattern discovery")
    print("  vibesrails --fix          Auto-fix issues")
    print("  vibesrails --audit        Dependency audit")
    print("  vibesrails --upgrade      Upgrade advisor")
    print()
    print("Next steps:")
    print("  cd your-project")
    print("  vibesrails --setup")
    print()


if __name__ == "__main__":
    main()
