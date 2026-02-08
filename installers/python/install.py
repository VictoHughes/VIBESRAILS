#!/usr/bin/env python3
"""VibesRails - Cross-platform installer (self-contained).

Usage: python install.py /path/to/project
"""
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("vibesrails.installer")

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    """CLI entry point."""
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    logger.info("=== VibesRails Installer ===")
    logger.info(f"Target: {target}")

    # 1. Install vibesrails
    logger.info("\n[1/4] Installing vibesrails...")
    subprocess.run([sys.executable, "-m", "pip", "install", "vibesrails"], check=True)

    # 2. Copy config files
    logger.info("\n[2/4] Copying configuration files...")
    shutil.copy2(SCRIPT_DIR / "vibesrails.yaml", target / "vibesrails.yaml")
    logger.info("  -> vibesrails.yaml")

    shutil.copy2(SCRIPT_DIR / "CLAUDE.md", target / "CLAUDE.md")
    logger.info("  -> CLAUDE.md")

    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)
    shutil.copy2(SCRIPT_DIR / ".claude" / "hooks.json", claude_dir / "hooks.json")
    logger.info("  -> .claude/hooks.json")

    # 3. Git pre-commit hook
    logger.info("\n[3/4] Installing git pre-commit hook...")
    git_dir = target / ".git"
    if git_dir.is_dir():
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        hook = hooks_dir / "pre-commit"
        hook.write_text(
            '#!/usr/bin/env bash\n'
            '# vibesrails pre-commit hook\n'
            '\n'
            'if command -v vibesrails &>/dev/null; then\n'
            '    vibesrails\n'
            'elif [ -f ".venv/bin/vibesrails" ]; then\n'
            '    .venv/bin/vibesrails\n'
            'elif [ -f "venv/bin/vibesrails" ]; then\n'
            '    venv/bin/vibesrails\n'
            'else\n'
            '    python3 -m vibesrails\n'
            'fi\n'
        )
        hook.chmod(0o755)
        logger.info("  -> .git/hooks/pre-commit")
    else:
        logger.info("  (no .git directory found, skipping hook)")

    # 4. Install AI self-protection hook
    logger.info("\n[4/4] Installing AI self-protection hook...")
    claude_hooks_dir = Path.home() / ".claude" / "hooks"
    claude_hooks_dir.mkdir(parents=True, exist_ok=True)

    ptuh_source = SCRIPT_DIR / "ptuh.py"
    if ptuh_source.exists():
        shutil.copy2(ptuh_source, claude_hooks_dir / "ptuh.py")
        logger.info("  -> ~/.claude/hooks/ptuh.py")
    else:
        logger.info(f"  (ptuh.py not found at {ptuh_source}, skipping hook file copy)")

    settings_path = Path.home() / ".claude" / "settings.json"
    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())

    hook_cmd = "python3 ~/.claude/hooks/ptuh.py"
    matcher_entry = {"matcher": "Edit|Write|Bash", "hooks": [{"type": "command", "command": hook_cmd}]}
    hooks = settings.setdefault("hooks", {})
    ptu = hooks.setdefault("PreToolUse", [])
    exists = any(any(h.get("command", "") == hook_cmd for h in m.get("hooks", [])) for m in ptu)
    if not exists:
        ptu.append(matcher_entry)

    settings_path.write_text(json.dumps(settings, indent=2))
    logger.info("  -> ~/.claude/settings.json (hook registered)")

    logger.info("\n=== Done! ===")
    logger.info("Commands:")
    logger.info("  vibesrails --all    # Scan project")
    logger.info("  vibesrails --setup  # Reconfigure (interactive)")
    logger.info("  vibesrails --show   # Show patterns")


if __name__ == "__main__":
    main()
