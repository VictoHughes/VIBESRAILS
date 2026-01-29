"""
CLI setup/config functions — extracted from cli.py.

Handles: find_config, init_config, install_hook, uninstall, run_senior_mode.
"""

import shutil
from pathlib import Path

from .scanner import BLUE, GREEN, NC, RED, YELLOW


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
    config_file = Path("vibesrails.yaml")
    if config_file.exists():
        config_file.unlink()
        removed.append(str(config_file))
    hook_path = Path(".git/hooks/pre-commit")
    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            lines = content.split("\n")
            new_lines = [line for line in lines if "vibesrails" not in line.lower()]
            new_content = "\n".join(new_lines).strip()

            if new_content and new_content != "#!/bin/bash":
                hook_path.write_text(new_content)
                print(f"{YELLOW}Removed vibesrails from pre-commit hook{NC}")
            else:
                hook_path.unlink()
                removed.append(str(hook_path))
    vibesrails_dir = Path(".vibesrails")
    if vibesrails_dir.exists():
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


def run_senior_mode(files: list[str]) -> int:
    """Run Senior Mode checks."""
    import subprocess

    from .senior_mode import ArchitectureMapper, ClaudeReviewer, SeniorGuards
    from .senior_mode.report import SeniorReport

    project_root = Path.cwd()

    print(f"{BLUE}Updating ARCHITECTURE.md...{NC}")
    mapper = ArchitectureMapper(project_root)
    mapper.save()

    diff_result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True
    )
    code_diff = diff_result.stdout

    test_diff_result = subprocess.run(
        ["git", "diff", "--cached", "--", "tests/"],
        capture_output=True, text=True
    )
    test_diff = test_diff_result.stdout

    guards = SeniorGuards()

    file_contents = []
    for f in files:
        try:
            content = Path(f).read_text()
            file_contents.append((f, content))
        except Exception:
            pass

    issues = guards.check_all(
        code_diff=code_diff,
        test_diff=test_diff,
        files=file_contents,
    )

    reviewer = ClaudeReviewer()
    review_result = None

    for filepath, content in file_contents:
        if reviewer.should_review(filepath, code_diff):
            print(f"{BLUE}Running Claude review on {filepath}...{NC}")
            review_result = reviewer.review(content, filepath)
            break

    report = SeniorReport(
        guard_issues=issues,
        review_result=review_result,
        architecture_updated=True,
    )

    print(report.generate())

    return 1 if report.has_blocking_issues() else 0


def install_hook(architecture_enabled: bool = False) -> bool:
    """Install git pre-commit hook."""
    git_dir = Path(".git")
    if not git_dir.exists():
        print(f"{RED}ERROR: Not a git repository{NC}")
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    arch_check = ""
    if architecture_enabled:
        arch_check = """
# Architecture check (optional - fails silently if not installed)
if command -v lint-imports &> /dev/null; then
    echo "Checking architecture..."
    lint-imports || echo "Architecture check failed (non-blocking)"
fi
"""

    if hook_path.exists():
        content = hook_path.read_text()
        if "vibesrails" in content:
            if architecture_enabled and "lint-imports" not in content:
                content = content.rstrip() + "\n" + arch_check
                hook_path.write_text(content)
                print(f"{YELLOW}Updated pre-commit hook with architecture check{NC}")
            else:
                print(f"{YELLOW}VibesRails hook already installed{NC}")
            return True

        print(f"{YELLOW}Appending to existing pre-commit hook{NC}")
        with open(hook_path, "a") as f:
            f.write("\n\n# vibesrails security check\nvibesrails\n")
            if architecture_enabled:
                f.write(arch_check)
    else:
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
