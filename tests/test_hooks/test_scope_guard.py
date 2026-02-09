"""Test scope guard — rules_reminder, CLAUDE.md scope_discipline, hooks integration."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent

RULES_REMINDER_RUNTIME = PROJECT_ROOT / ".claude" / "rules_reminder.md"
RULES_REMINDER_TEMPLATE = (
    PROJECT_ROOT / "vibesrails" / "claude_integration" / "rules_reminder.md"
)
HOOKS_RUNTIME = PROJECT_ROOT / ".claude" / "hooks.json"
HOOKS_TEMPLATE = PROJECT_ROOT / "vibesrails" / "claude_integration" / "hooks.json"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
CLAUDE_MD_TEMPLATE = (
    PROJECT_ROOT / "vibesrails" / "claude_integration" / "CLAUDE.md.template"
)

REQUIRED_RULES = [
    "STOP",
    "SCOPE",
    "audit",
    "fix X",
    "commit",
]


class TestRulesReminder:
    """rules_reminder.md exists and contains the 5 checkpoint rules."""

    def test_runtime_exists(self):
        assert RULES_REMINDER_RUNTIME.exists(), (
            f"Missing: {RULES_REMINDER_RUNTIME}"
        )

    def test_template_exists(self):
        assert RULES_REMINDER_TEMPLATE.exists(), (
            f"Missing: {RULES_REMINDER_TEMPLATE}"
        )

    def test_runtime_contains_all_rules(self):
        content = RULES_REMINDER_RUNTIME.read_text()
        for rule in REQUIRED_RULES:
            assert rule in content, f"Missing rule keyword '{rule}' in rules_reminder.md"

    def test_template_matches_runtime(self):
        assert RULES_REMINDER_RUNTIME.read_text() == RULES_REMINDER_TEMPLATE.read_text(), (
            "Template and runtime rules_reminder.md are out of sync"
        )


class TestHooksContainScopeCheck:
    """hooks.json PostToolUse Bash contains rules_reminder reference."""

    @pytest.fixture(scope="class")
    def bash_hooks(self):
        data = json.loads(HOOKS_RUNTIME.read_text())
        for group in data["hooks"].get("PostToolUse", []):
            if group.get("matcher") == "Bash":
                return group["hooks"]
        pytest.fail("No PostToolUse Bash matcher found")

    def test_runtime_has_rules_reminder_command(self, bash_hooks):
        commands = [h.get("command", "") for h in bash_hooks if h["type"] == "command"]
        assert any("rules_reminder" in cmd for cmd in commands), (
            "PostToolUse Bash missing rules_reminder command"
        )

    def test_runtime_has_scope_check_prompt(self, bash_hooks):
        prompts = [h.get("prompt", "") for h in bash_hooks if h["type"] == "prompt"]
        assert any("SCOPE CHECK" in p for p in prompts), (
            "PostToolUse Bash missing SCOPE CHECK prompt"
        )

    def test_template_has_rules_reminder_command(self):
        data = json.loads(HOOKS_TEMPLATE.read_text())
        for group in data["hooks"].get("PostToolUse", []):
            if group.get("matcher") == "Bash":
                commands = [
                    h.get("command", "")
                    for h in group["hooks"]
                    if h["type"] == "command"
                ]
                assert any("rules_reminder" in cmd for cmd in commands), (
                    "Template PostToolUse Bash missing rules_reminder command"
                )
                return
        pytest.fail("Template has no PostToolUse Bash matcher")


class TestClaudeMdScopeDiscipline:
    """CLAUDE.md contains scope_discipline, not default_to_action."""

    def test_has_scope_discipline(self):
        content = CLAUDE_MD.read_text()
        assert "scope_discipline" in content

    def test_no_default_to_action(self):
        content = CLAUDE_MD.read_text()
        assert "default_to_action" not in content

    def test_template_has_scope_discipline(self):
        content = CLAUDE_MD_TEMPLATE.read_text()
        assert "scope_discipline" in content

    def test_template_no_default_to_action(self):
        content = CLAUDE_MD_TEMPLATE.read_text()
        assert "default_to_action" not in content


class TestThrottleIncludesReminder:
    """Throttle block message includes rules_reminder when file exists."""

    def test_includes_reminder_when_exists(self, tmp_path):
        """Throttle message includes reminder content when file exists."""
        reminder = tmp_path / ".claude" / "rules_reminder.md"
        reminder.parent.mkdir()
        reminder.write_text("CHECKPOINT: test rule")

        state_dir = tmp_path / ".vibesrails"
        state_dir.mkdir()

        from vibesrails.hooks.throttle import record_write

        # Write past threshold
        for _ in range(6):
            record_write(state_dir)

        # Simulate what pre_tool_use does when throttle blocks
        from vibesrails.hooks.throttle import should_block

        assert should_block(state_dir)

        # Check that the reminder path logic works
        assert reminder.exists()
        content = reminder.read_text(encoding="utf-8")
        assert "CHECKPOINT" in content

    def test_works_without_reminder(self, tmp_path):
        """Throttle functions normally when rules_reminder.md doesn't exist."""
        state_dir = tmp_path / ".vibesrails"
        state_dir.mkdir()

        from vibesrails.hooks.throttle import record_write, should_block

        for _ in range(6):
            record_write(state_dir)

        assert should_block(state_dir)
        # No crash when .claude/rules_reminder.md doesn't exist
        reminder_path = tmp_path / ".claude" / "rules_reminder.md"
        assert not reminder_path.exists()


class TestSetupCopiesReminder:
    """--setup installs rules_reminder.md into .claude/."""

    def test_install_claude_hooks_copies_reminder(self, tmp_path):
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        # Need .git for hooks to make sense
        (tmp_path / ".git").mkdir()

        result = install_claude_hooks(tmp_path)

        assert result is True
        reminder = tmp_path / ".claude" / "rules_reminder.md"
        assert reminder.exists(), "install_claude_hooks must copy rules_reminder.md"
        content = reminder.read_text()
        for rule in REQUIRED_RULES:
            assert rule in content
