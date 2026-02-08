"""Test that hooks.json commands stay in sync with CLI flags and modules.

Parses both the project hooks.json and the template hooks.json,
extracts every command hook, and verifies:
1. All referenced vibesrails modules import cleanly
2. All CLI flags used in hooks exist in vibesrails --help
3. Template and project hooks.json are identical

This prevents future refactors from breaking hooks silently.
"""

import importlib
import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Both hooks.json files that must stay in sync
PROJECT_HOOKS = PROJECT_ROOT / ".claude" / "hooks.json"
TEMPLATE_HOOKS = PROJECT_ROOT / "vibesrails" / "claude_integration" / "hooks.json"


def _load_hooks(path: Path) -> dict:
    """Load and parse a hooks.json file."""
    return json.loads(path.read_text())


def _extract_commands(hooks_data: dict) -> list[str]:
    """Extract all command-type hook commands from hooks data."""
    commands = []
    for _event, hook_list in hooks_data.get("hooks", {}).items():
        for entry in hook_list:
            if isinstance(entry, dict):
                for h in entry.get("hooks", []):
                    if h.get("type") == "command":
                        commands.append(h["command"])
    return commands


def _extract_modules(commands: list[str]) -> list[str]:
    """Extract vibesrails module names from hook commands."""
    modules = []
    for cmd in commands:
        if "python3 -m vibesrails." in cmd:
            # Extract: python3 -m vibesrails.hooks.xxx
            parts = cmd.split("python3 -m ")
            for part in parts[1:]:
                mod = part.split()[0].strip('"').strip("'")
                if mod.startswith("vibesrails."):
                    modules.append(mod)
        if "from vibesrails." in cmd:
            # Extract: from vibesrails.hooks.xxx import yyy
            import re

            for match in re.finditer(r"from (vibesrails\.\S+) import", cmd):
                modules.append(match.group(1))
    return list(set(modules))


def _get_cli_flags() -> set[str]:
    """Get all valid CLI flags from vibesrails --help."""
    import re

    # Try entry point first, then python -m vibesrails.cli
    for cmd in [["vibesrails", "--help"], ["python3", "-c", "from vibesrails.cli import main; main()", "--help"]]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout + result.stderr
            flags = set(re.findall(r"--[a-z][a-z_-]*", output))
            if flags:
                return flags
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return set()


class TestHooksModulesExist:
    """Every vibesrails module referenced in hooks must be importable."""

    @pytest.fixture(scope="class")
    def hook_modules(self):
        if not PROJECT_HOOKS.exists():
            pytest.skip("No .claude/hooks.json in project")
        data = _load_hooks(PROJECT_HOOKS)
        commands = _extract_commands(data)
        return _extract_modules(commands)

    def test_all_modules_importable(self, hook_modules):
        """Every referenced module must import without error."""
        errors = []
        for mod in hook_modules:
            try:
                importlib.import_module(mod)
            except ImportError as e:
                errors.append(f"{mod}: {e}")
        assert not errors, "Hook modules failed to import:\n" + "\n".join(errors)

    def test_at_least_three_modules(self, hook_modules):
        """Sanity check: hooks should reference at least 3 modules."""
        assert len(hook_modules) >= 3, f"Only {len(hook_modules)} modules found"


class TestHooksCLIFlagsExist:
    """Every vibesrails CLI flag used in hooks must exist in --help."""

    @pytest.fixture(scope="class")
    def hook_cli_flags(self):
        if not PROJECT_HOOKS.exists():
            pytest.skip("No .claude/hooks.json in project")
        data = _load_hooks(PROJECT_HOOKS)
        commands = _extract_commands(data)
        import re

        flags = set()
        for cmd in commands:
            if "vibesrails" in cmd:
                for flag in re.findall(r"vibesrails\s+(--[a-z_-]+)", cmd):
                    flags.add(flag)
        return flags

    @pytest.fixture(scope="class")
    def valid_flags(self):
        return _get_cli_flags()

    def test_all_flags_valid(self, hook_cli_flags, valid_flags):
        """Every CLI flag in hooks must exist in vibesrails --help."""
        invalid = hook_cli_flags - valid_flags
        assert not invalid, (
            f"Hook commands use invalid CLI flags: {invalid}\n"
            f"Valid flags: {sorted(valid_flags)}"
        )


class TestTemplateSync:
    """Template hooks.json must match project hooks.json."""

    def test_template_exists(self):
        assert TEMPLATE_HOOKS.exists(), (
            f"Template hooks.json missing: {TEMPLATE_HOOKS}"
        )

    def test_template_matches_project(self):
        if not PROJECT_HOOKS.exists():
            pytest.skip("No .claude/hooks.json in project")
        project = _load_hooks(PROJECT_HOOKS)
        template = _load_hooks(TEMPLATE_HOOKS)
        assert project == template, (
            "Template hooks.json and project hooks.json are out of sync. "
            "Update vibesrails/claude_integration/hooks.json to match .claude/hooks.json"
        )
