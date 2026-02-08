"""
CLI setup/config functions — extracted from cli.py.

Handles: find_config, init_config, install_hook, uninstall, run_senior_mode.
"""

import logging
import shutil
from pathlib import Path

from .scanner import BLUE, GREEN, NC, RED, YELLOW

logger = logging.getLogger(__name__)


def find_config() -> Path | None:
    """Find vibesrails.yaml in project or user home."""
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
        logger.info(f"{YELLOW}vibesrails.yaml already exists{NC}")
        return False

    default_config = get_default_config_path()
    if not default_config.exists():
        logger.error(f"{RED}ERROR: Default config not found at {default_config}{NC}")
        return False

    shutil.copy(default_config, target)
    logger.info(f"{GREEN}Created {target}{NC}")
    logger.info("Next steps:")
    logger.info(f"  1. Edit {target} to customize patterns")
    logger.info("  2. Run: vibesrails --hook  (install git pre-commit)")
    logger.info("  3. Code freely - vibesrails runs on every commit")
    return True


def uninstall() -> bool:
    """Uninstall vibesrails from current project."""
    removed = []
    config_file = Path("vibesrails.yaml")
    if config_file.exists():
        config_file.unlink()
        removed.append(str(config_file))
    hook_path = Path(".git/hooks/pre-commit")
    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            lines = content.split("\n")
            new_lines = []
            in_vibesrails_block = False

            for line in lines:
                stripped = line.strip()

                # Inside vibesrails if-block: skip until closing fi
                if in_vibesrails_block:
                    if stripped == "fi":
                        in_vibesrails_block = False
                    continue

                # Detect start of if/elif block that references vibesrails
                if "vibesrails" in line.lower() and (
                    stripped.startswith("if ") or stripped.startswith("elif ")
                ):
                    in_vibesrails_block = True
                    continue

                # Skip individual vibesrails lines (comments, commands)
                if "vibesrails" in line.lower():
                    continue

                new_lines.append(line)

            new_content = "\n".join(new_lines).strip()

            # Check if only shebang/comments/whitespace remain
            meaningful = [
                l
                for l in new_content.split("\n")
                if l.strip() and not l.strip().startswith("#")
            ]

            if not meaningful:
                hook_path.unlink()
                removed.append(str(hook_path))
            else:
                hook_path.write_text(new_content + "\n")
                logger.info(f"{YELLOW}Removed vibesrails from pre-commit hook{NC}")
    vibesrails_dir = Path(".vibesrails")
    if vibesrails_dir.exists():
        shutil.rmtree(vibesrails_dir)
        removed.append(str(vibesrails_dir))

    if removed:
        logger.info(f"{GREEN}Removed:{NC}")
        for f in removed:
            logger.info(f"  - {f}")
        logger.info(f"{GREEN}vibesrails uninstalled from this project{NC}")
        logger.info("To uninstall the package: pip uninstall vibesrails")
    else:
        logger.info(f"{YELLOW}Nothing to uninstall{NC}")

    return True


def _get_cached_diff(*extra_args: str) -> str:
    """Get git staged diff output."""
    import subprocess
    cmd = ["git", "diff", "--cached"] + list(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def _read_file_contents(files: list[str]) -> list[tuple[str, str]]:
    """Read file contents, skipping unreadable files."""
    contents = []
    for f in files:
        try:
            contents.append((f, Path(f).read_text()))
        except Exception:
            logger.debug("Failed to read file for senior mode: %s", f)
    return contents


def run_senior_mode(files: list[str]) -> int:
    """Run Senior Mode checks."""
    from .senior_mode import ArchitectureMapper, ClaudeReviewer, SeniorGuards
    from .senior_mode.report import SeniorReport

    logger.info(f"{BLUE}Updating ARCHITECTURE.md...{NC}")
    ArchitectureMapper(Path.cwd()).save()

    code_diff = _get_cached_diff()
    test_diff = _get_cached_diff("--", "tests/")
    file_contents = _read_file_contents(files)

    issues = SeniorGuards().check_all(
        code_diff=code_diff, test_diff=test_diff, files=file_contents,
    )

    reviewer = ClaudeReviewer()
    review_result = None
    for filepath, content in file_contents:
        if reviewer.should_review(filepath, code_diff):
            logger.info(f"{BLUE}Running Claude review on {filepath}...{NC}")
            review_result = reviewer.review(content, filepath)
            break

    report = SeniorReport(
        guard_issues=issues, review_result=review_result, architecture_updated=True,
    )
    logger.info(report.generate())
    return 1 if report.has_blocking_issues() else 0


_ARCH_CHECK = """
# Architecture check (optional - fails silently if not installed)
if command -v lint-imports &> /dev/null; then
    echo "Checking architecture..."
    lint-imports || echo "Architecture check failed (non-blocking)"
fi
"""


def _update_existing_hook(hook_path: Path, architecture_enabled: bool) -> bool:
    """Update an existing pre-commit hook. Returns True if handled."""
    content = hook_path.read_text()
    if "vibesrails" not in content:
        return False
    if architecture_enabled and "lint-imports" not in content:
        hook_path.write_text(content.rstrip() + "\n" + _ARCH_CHECK)
        logger.info(f"{YELLOW}Updated pre-commit hook with architecture check{NC}")
    else:
        logger.info(f"{YELLOW}VibesRails hook already installed{NC}")
    return True


def install_hook(architecture_enabled: bool = False) -> bool:
    """Install git pre-commit hook."""
    git_dir = Path(".git")
    if not git_dir.exists():
        logger.error(f"{RED}ERROR: Not a git repository{NC}")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    arch_check = _ARCH_CHECK if architecture_enabled else ""

    if hook_path.exists():
        if _update_existing_hook(hook_path, architecture_enabled):
            return True
        logger.info(f"{YELLOW}Appending to existing pre-commit hook{NC}")
        with open(hook_path, "a") as f:
            f.write("\n\n# vibesrails security check\nvibesrails\n")
            if architecture_enabled:
                f.write(arch_check)
    else:
        hook_path.write_text(
            "#!/bin/bash\n# VibesRails pre-commit hook\n"
            "# Scale up your vibe coding - safely\n\n"
            "# Find vibesrails command (PATH, local venv, or python -m)\n"
            'if command -v vibesrails &> /dev/null; then\n    vibesrails\n'
            'elif [ -f ".venv/bin/vibesrails" ]; then\n    .venv/bin/vibesrails\n'
            'elif [ -f "venv/bin/vibesrails" ]; then\n    venv/bin/vibesrails\n'
            "else\n    python3 -m vibesrails\nfi\n" + arch_check
        )
        hook_path.chmod(0o755)

    logger.info(f"{GREEN}Git hook installed at {hook_path}{NC}")
    return True
