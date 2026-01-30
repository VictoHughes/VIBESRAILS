#!/usr/bin/env python3
"""VibesRails - Cross-platform installer (self-contained).

Usage: python install.py /path/to/project
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    """CLI entry point."""
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    print(f"=== VibesRails Installer ===")
    print(f"Target: {target}")

    # 1. Install vibesrails
    print("\n[1/4] Installing vibesrails...")
    subprocess.run([sys.executable, "-m", "pip", "install", "vibesrails"], check=True)

    # 2. Copy config files
    print("\n[2/4] Copying configuration files...")
    shutil.copy2(SCRIPT_DIR / "vibesrails.yaml", target / "vibesrails.yaml")
    print("  -> vibesrails.yaml")

    shutil.copy2(SCRIPT_DIR / "CLAUDE.md", target / "CLAUDE.md")
    print("  -> CLAUDE.md")

    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)
    shutil.copy2(SCRIPT_DIR / ".claude" / "hooks.json", claude_dir / "hooks.json")
    print("  -> .claude/hooks.json")

    # 3. Git pre-commit hook
    print("\n[3/4] Installing git pre-commit hook...")
    git_dir = target / ".git"
    if git_dir.is_dir():
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook = hooks_dir / "pre-commit"
        hook.write_text(
            '#!/usr/bin/env bash\n'
            '# vibesrails pre-commit hook\n'
            'if command -v vibesrails &>/dev/null; then\n'
            '    vibesrails\n'
            '    if [ $? -ne 0 ]; then\n'
            '        echo "vibesrails: issues found. Fix before committing."\n'
            '        exit 1\n'
            '    fi\n'
            'fi\n'
        )
        hook.chmod(0o755)
        print("  -> .git/hooks/pre-commit")
    else:
        print("  (no .git directory found, skipping hook)")

    # 4. Install AI self-protection hook
    print("\n[4/4] Installing AI self-protection hook...")
    claude_hooks_dir = Path.home() / ".claude" / "hooks"
    claude_hooks_dir.mkdir(parents=True, exist_ok=True)

    ptuh_source = SCRIPT_DIR / "ptuh.py"
    if ptuh_source.exists():
        shutil.copy2(ptuh_source, claude_hooks_dir / "ptuh.py")
        print("  -> ~/.claude/hooks/ptuh.py")
    else:
        print(f"  (ptuh.py not found at {ptuh_source}, skipping hook file copy)")

    settings_path = Path.home() / ".claude" / "settings.json"
    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())

    hook_entry = {"type": "command", "command": "python3 ~/.claude/hooks/ptuh.py"}
    hooks = settings.setdefault("hooks", {})
    ptu = hooks.setdefault("PreToolUse", [])
    if not any(h.get("command", "") == hook_entry["command"] for h in ptu):
        ptu.append(hook_entry)

    settings_path.write_text(json.dumps(settings, indent=2))
    print("  -> ~/.claude/settings.json (hook registered)")

    print("\n=== Done! ===")
    print("Commands:")
    print("  vibesrails --all    # Scan project")
    print("  vibesrails --setup  # Reconfigure (interactive)")
    print("  vibesrails --show   # Show patterns")


if __name__ == "__main__":
    main()
