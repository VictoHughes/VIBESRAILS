"""Tests for vibesrails.guardian module.

Tests AI session detection, guardian configuration, and rule application.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vibesrails.guardian import (
    AI_ENV_MARKERS,
    is_ai_session,
    get_ai_agent_name,
    get_guardian_config,
    should_apply_guardian,
    get_stricter_patterns,
    apply_guardian_rules,
    log_guardian_block,
    get_guardian_stats,
    show_guardian_stats,
    print_guardian_status,
)
from vibesrails.scanner import ScanResult


# ============================================
# Tests for is_ai_session()
# ============================================

class TestIsAiSession:
    """Tests for is_ai_session()."""

    def test_returns_true_when_claude_code_env_set(self):
        """Detect Claude Code session via CLAUDE_CODE env var."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_cursor_env_set(self):
        """Detect Cursor session via CURSOR_SESSION env var."""
        with patch.dict(os.environ, {"CURSOR_SESSION": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_copilot_env_set(self):
        """Detect GitHub Copilot session via COPILOT_AGENT env var."""
        with patch.dict(os.environ, {"COPILOT_AGENT": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_aider_env_set(self):
        """Detect Aider session via AIDER_SESSION env var."""
        with patch.dict(os.environ, {"AIDER_SESSION": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_continue_env_set(self):
        """Detect Continue.dev session via CONTINUE_SESSION env var."""
        with patch.dict(os.environ, {"CONTINUE_SESSION": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_cody_env_set(self):
        """Detect Cody session via CODY_SESSION env var."""
        with patch.dict(os.environ, {"CODY_SESSION": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_manual_override_set(self):
        """Detect manual AI mode via VIBESRAILS_AGENT_MODE env var."""
        with patch.dict(os.environ, {"VIBESRAILS_AGENT_MODE": "1"}, clear=True):
            assert is_ai_session() is True

    def test_returns_true_when_term_program_is_claude_code(self):
        """Detect Claude Code via TERM_PROGRAM env var."""
        with patch.dict(os.environ, {"TERM_PROGRAM": "claude-code"}, clear=True):
            assert is_ai_session() is True

    def test_returns_false_when_no_ai_env(self):
        """No AI session detected when no markers set."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_ai_session() is False

    def test_returns_false_with_unrelated_env_vars(self):
        """No AI session detected with unrelated environment variables."""
        with patch.dict(os.environ, {"PATH": "/usr/bin", "HOME": "/home/user"}, clear=True):
            assert is_ai_session() is False

    def test_all_env_markers_are_checked(self):
        """Verify all documented AI_ENV_MARKERS are valid."""
        # Ensure each marker in the list triggers detection
        for marker in AI_ENV_MARKERS:
            with patch.dict(os.environ, {marker: "1"}, clear=True):
                assert is_ai_session() is True, f"Marker {marker} should be detected"


# ============================================
# Tests for get_ai_agent_name()
# ============================================

class TestGetAiAgentName:
    """Tests for get_ai_agent_name()."""

    def test_returns_claude_code_when_claude_code_set(self):
        """Return 'Claude Code' for Claude Code sessions."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert get_ai_agent_name() == "Claude Code"

    def test_returns_cursor_when_cursor_set(self):
        """Return 'Cursor' for Cursor IDE sessions."""
        with patch.dict(os.environ, {"CURSOR_SESSION": "1"}, clear=True):
            assert get_ai_agent_name() == "Cursor"

    def test_returns_github_copilot_when_copilot_set(self):
        """Return 'GitHub Copilot' for Copilot sessions."""
        with patch.dict(os.environ, {"COPILOT_AGENT": "1"}, clear=True):
            assert get_ai_agent_name() == "GitHub Copilot"

    def test_returns_aider_when_aider_set(self):
        """Return 'Aider' for Aider sessions."""
        with patch.dict(os.environ, {"AIDER_SESSION": "1"}, clear=True):
            assert get_ai_agent_name() == "Aider"

    def test_returns_continue_when_continue_set(self):
        """Return 'Continue' for Continue.dev sessions."""
        with patch.dict(os.environ, {"CONTINUE_SESSION": "1"}, clear=True):
            assert get_ai_agent_name() == "Continue"

    def test_returns_cody_when_cody_set(self):
        """Return 'Cody' for Cody sessions."""
        with patch.dict(os.environ, {"CODY_SESSION": "1"}, clear=True):
            assert get_ai_agent_name() == "Cody"

    def test_returns_manual_when_agent_mode_set(self):
        """Return 'AI Agent (manual)' for manual override."""
        with patch.dict(os.environ, {"VIBESRAILS_AGENT_MODE": "1"}, clear=True):
            assert get_ai_agent_name() == "AI Agent (manual)"

    def test_returns_none_when_no_ai(self):
        """Return None when no AI agent detected."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_ai_agent_name() is None

    def test_priority_claude_over_cursor(self):
        """Claude Code takes priority when multiple agents detected."""
        with patch.dict(os.environ, {"CLAUDE_CODE": "1", "CURSOR_SESSION": "1"}, clear=True):
            # First match wins based on function implementation order
            assert get_ai_agent_name() == "Claude Code"


# ============================================
# Tests for get_guardian_config()
# ============================================

class TestGetGuardianConfig:
    """Tests for get_guardian_config()."""

    def test_returns_guardian_section(self):
        """Extract guardian config from main config."""
        config = {"guardian": {"enabled": True, "auto_detect": True}}
        result = get_guardian_config(config)
        assert result == {"enabled": True, "auto_detect": True}

    def test_returns_empty_dict_when_missing(self):
        """Return empty dict when no guardian section."""
        config = {"blocking": [], "version": "1.0"}
        result = get_guardian_config(config)
        assert result == {}

    def test_returns_empty_dict_for_empty_config(self):
        """Return empty dict for empty config."""
        result = get_guardian_config({})
        assert result == {}

    def test_returns_nested_guardian_config(self):
        """Return complex nested guardian config."""
        config = {
            "guardian": {
                "enabled": True,
                "stricter_patterns": [
                    {"id": "test", "regex": "TODO", "message": "No TODOs"}
                ],
                "warnings_as_blocking": True,
            }
        }
        result = get_guardian_config(config)
        assert result["enabled"] is True
        assert len(result["stricter_patterns"]) == 1
        assert result["warnings_as_blocking"] is True


# ============================================
# Tests for should_apply_guardian()
# ============================================

class TestShouldApplyGuardian:
    """Tests for should_apply_guardian()."""

    def test_true_when_enabled_and_ai_session(self):
        """Apply guardian when enabled and AI detected."""
        config = {"guardian": {"enabled": True, "auto_detect": True}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert should_apply_guardian(config) is True

    def test_false_when_disabled(self):
        """Don't apply when guardian is disabled."""
        config = {"guardian": {"enabled": False}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert should_apply_guardian(config) is False

    def test_false_when_no_guardian_config(self):
        """Don't apply when no guardian config exists."""
        config = {"blocking": []}
        assert should_apply_guardian(config) is False

    def test_false_when_no_ai_and_auto_detect(self):
        """Don't apply when auto_detect is true but no AI session."""
        config = {"guardian": {"enabled": True, "auto_detect": True}}
        with patch.dict(os.environ, {}, clear=True):
            assert should_apply_guardian(config) is False

    def test_true_when_force_enabled(self):
        """Apply when force is enabled regardless of AI detection."""
        config = {"guardian": {"enabled": True, "force": True}}
        with patch.dict(os.environ, {}, clear=True):
            assert should_apply_guardian(config) is True

    def test_auto_detect_defaults_to_true(self):
        """auto_detect defaults to True when not specified."""
        config = {"guardian": {"enabled": True}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert should_apply_guardian(config) is True

    def test_enabled_defaults_to_false(self):
        """enabled defaults to False when not specified."""
        config = {"guardian": {"auto_detect": True}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            assert should_apply_guardian(config) is False


# ============================================
# Tests for get_stricter_patterns()
# ============================================

class TestGetStricterPatterns:
    """Tests for get_stricter_patterns()."""

    def test_returns_stricter_patterns(self):
        """Return stricter_patterns from guardian config."""
        config = {
            "guardian": {
                "enabled": True,
                "stricter_patterns": [
                    {"id": "test1", "regex": "TODO", "message": "No TODOs"},
                    {"id": "test2", "regex": "FIXME", "message": "No FIXMEs"},
                ]
            }
        }
        result = get_stricter_patterns(config)
        assert len(result) == 2
        assert result[0]["id"] == "test1"
        assert result[1]["id"] == "test2"

    def test_returns_empty_list_when_no_patterns(self):
        """Return empty list when no stricter_patterns defined."""
        config = {"guardian": {"enabled": True}}
        result = get_stricter_patterns(config)
        assert result == []

    def test_returns_empty_list_when_no_guardian(self):
        """Return empty list when no guardian config."""
        config = {"blocking": []}
        result = get_stricter_patterns(config)
        assert result == []


# ============================================
# Tests for apply_guardian_rules()
# ============================================

class TestApplyGuardianRules:
    """Tests for apply_guardian_rules()."""

    def test_returns_unchanged_when_guardian_disabled(self):
        """Return unchanged results when guardian is disabled."""
        config = {"guardian": {"enabled": False}}
        results = [
            ScanResult(file="test.py", line=1, pattern_id="test", message="Test", level="WARN")
        ]
        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules(results, config, "test.py")
        assert new_results == results

    def test_escalates_warnings_to_blocking(self):
        """Escalate warnings to blocking when warnings_as_blocking is True."""
        config = {
            "guardian": {
                "enabled": True,
                "force": True,
                "warnings_as_blocking": True,
            }
        }
        results = [
            ScanResult(file="test.py", line=1, pattern_id="warn1", message="Warning", level="WARN")
        ]
        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules(results, config, "test.py")

        assert len(new_results) == 1
        assert new_results[0].level == "BLOCK"
        assert "[GUARDIAN]" in new_results[0].message

    def test_keeps_blocking_as_blocking(self):
        """Keep BLOCK level unchanged when escalating."""
        config = {
            "guardian": {
                "enabled": True,
                "force": True,
                "warnings_as_blocking": True,
            }
        }
        results = [
            ScanResult(file="test.py", line=1, pattern_id="block1", message="Blocking", level="BLOCK")
        ]
        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules(results, config, "test.py")

        assert len(new_results) == 1
        assert new_results[0].level == "BLOCK"

    def test_no_escalation_without_flag(self):
        """Don't escalate warnings without warnings_as_blocking flag."""
        config = {
            "guardian": {
                "enabled": True,
                "force": True,
                "warnings_as_blocking": False,
            }
        }
        results = [
            ScanResult(file="test.py", line=1, pattern_id="warn1", message="Warning", level="WARN")
        ]
        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules(results, config, "test.py")

        assert len(new_results) == 1
        assert new_results[0].level == "WARN"

    def test_empty_results_unchanged(self):
        """Return empty list for empty input."""
        config = {"guardian": {"enabled": True, "force": True}}
        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules([], config, "test.py")
        assert new_results == []


# ============================================
# Tests for log_guardian_block()
# ============================================

class TestLogGuardianBlock:
    """Tests for log_guardian_block()."""

    def test_creates_log_file_and_writes_entry(self, tmp_path):
        """Create log file and write JSON entry."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = ScanResult(
                file="test.py",
                line=10,
                pattern_id="unsafe_yaml",
                message="Unsafe YAML load",
                level="BLOCK"
            )
            log_guardian_block(result, agent_name="Claude Code")

            log_file = tmp_path / ".vibesrails" / "guardian.log"
            assert log_file.exists()

            content = log_file.read_text()
            entry = json.loads(content.strip())

            assert entry["agent"] == "Claude Code"
            assert entry["file"] == "test.py"
            assert entry["line"] == 10
            assert entry["pattern_id"] == "unsafe_yaml"
            assert entry["level"] == "BLOCK"
            assert "timestamp" in entry
        finally:
            os.chdir(original_cwd)

    def test_appends_to_existing_log(self, tmp_path):
        """Append to existing log file."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result1 = ScanResult("test.py", 1, "p1", "M1", "BLOCK")
            result2 = ScanResult("test.py", 2, "p2", "M2", "BLOCK")

            log_guardian_block(result1, "Agent1")
            log_guardian_block(result2, "Agent2")

            log_file = tmp_path / ".vibesrails" / "guardian.log"
            lines = log_file.read_text().strip().split("\n")

            assert len(lines) == 2
        finally:
            os.chdir(original_cwd)

    def test_uses_unknown_when_no_agent_name(self, tmp_path):
        """Use 'unknown' when agent_name is None."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = ScanResult("test.py", 1, "p1", "M1", "BLOCK")
            log_guardian_block(result, agent_name=None)

            log_file = tmp_path / ".vibesrails" / "guardian.log"
            entry = json.loads(log_file.read_text().strip())

            assert entry["agent"] == "unknown"
        finally:
            os.chdir(original_cwd)


# ============================================
# Tests for get_guardian_stats()
# ============================================

class TestGetGuardianStats:
    """Tests for get_guardian_stats()."""

    def test_returns_zero_stats_when_no_log(self, tmp_path):
        """Return zero stats when no log file exists."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            stats = get_guardian_stats()
            assert stats["total_blocks"] == 0
            assert stats["by_pattern"] == {}
            assert stats["by_agent"] == {}
        finally:
            os.chdir(original_cwd)

    def test_counts_blocks_by_pattern(self, tmp_path):
        """Count blocks grouped by pattern_id."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create log entries
            log_guardian_block(ScanResult("a.py", 1, "pattern_a", "M", "BLOCK"), "Agent")
            log_guardian_block(ScanResult("b.py", 2, "pattern_a", "M", "BLOCK"), "Agent")
            log_guardian_block(ScanResult("c.py", 3, "pattern_b", "M", "BLOCK"), "Agent")

            stats = get_guardian_stats()

            assert stats["total_blocks"] == 3
            assert stats["by_pattern"]["pattern_a"] == 2
            assert stats["by_pattern"]["pattern_b"] == 1
        finally:
            os.chdir(original_cwd)

    def test_counts_blocks_by_agent(self, tmp_path):
        """Count blocks grouped by agent."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            log_guardian_block(ScanResult("a.py", 1, "p1", "M", "BLOCK"), "Claude Code")
            log_guardian_block(ScanResult("b.py", 2, "p2", "M", "BLOCK"), "Claude Code")
            log_guardian_block(ScanResult("c.py", 3, "p3", "M", "BLOCK"), "Cursor")

            stats = get_guardian_stats()

            assert stats["by_agent"]["Claude Code"] == 2
            assert stats["by_agent"]["Cursor"] == 1
        finally:
            os.chdir(original_cwd)

    def test_handles_malformed_json_gracefully(self, tmp_path):
        """Skip malformed JSON lines without crashing."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            log_dir = tmp_path / ".vibesrails"
            log_dir.mkdir()
            log_file = log_dir / "guardian.log"

            # Write valid and invalid lines
            log_file.write_text(
                '{"pattern_id": "p1", "agent": "A"}\n'
                'not valid json\n'
                '{"pattern_id": "p2", "agent": "B"}\n'
            )

            stats = get_guardian_stats()

            # Should count only valid entries
            assert stats["total_blocks"] == 2
        finally:
            os.chdir(original_cwd)


# ============================================
# Edge Cases and Error Conditions
# ============================================

class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_is_ai_session_with_empty_string_env_var(self):
        """Empty string env var should not trigger AI detection."""
        with patch.dict(os.environ, {"CLAUDE_CODE": ""}, clear=True):
            # Empty string is falsy, so should not detect
            assert is_ai_session() is False

    def test_get_ai_agent_name_with_empty_string_env_var(self):
        """Empty string env var returns None for agent name."""
        with patch.dict(os.environ, {"CLAUDE_CODE": ""}, clear=True):
            assert get_ai_agent_name() is None

    def test_apply_guardian_rules_with_multiple_results(self):
        """Process multiple scan results correctly."""
        config = {
            "guardian": {
                "enabled": True,
                "force": True,
                "warnings_as_blocking": True,
            }
        }
        results = [
            ScanResult("a.py", 1, "p1", "M1", "WARN"),
            ScanResult("b.py", 2, "p2", "M2", "BLOCK"),
            ScanResult("c.py", 3, "p3", "M3", "WARN"),
        ]

        with patch.dict(os.environ, {}, clear=True):
            new_results = apply_guardian_rules(results, config, "test.py")

        assert len(new_results) == 3
        # All should be BLOCK now
        assert all(r.level == "BLOCK" for r in new_results)
        # WARN results should have [GUARDIAN] prefix
        assert "[GUARDIAN]" in new_results[0].message
        assert "[GUARDIAN]" in new_results[2].message

    def test_guardian_config_preserves_other_keys(self):
        """get_guardian_config only returns guardian section, not other keys."""
        config = {
            "guardian": {"enabled": True},
            "blocking": [{"id": "test"}],
            "version": "1.0"
        }
        result = get_guardian_config(config)
        assert "blocking" not in result
        assert "version" not in result
        assert result == {"enabled": True}


# ============================================
# Tests for show_guardian_stats()
# ============================================

class TestShowGuardianStats:
    """Tests for show_guardian_stats()."""

    def test_shows_no_blocks_message_when_empty(self, tmp_path, capsys):
        """Display 'no blocks' message when log is empty."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            show_guardian_stats()
            captured = capsys.readouterr()
            assert "No AI code blocks recorded yet" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_shows_block_counts(self, tmp_path, capsys):
        """Display block counts by pattern and agent."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create some log entries
            log_guardian_block(ScanResult("a.py", 1, "pattern_a", "M", "BLOCK"), "Claude Code")
            log_guardian_block(ScanResult("b.py", 2, "pattern_b", "M", "BLOCK"), "Cursor")

            show_guardian_stats()
            captured = capsys.readouterr()

            assert "Guardian Statistics" in captured.out
            assert "Total blocks: 2" in captured.out
            assert "pattern_a" in captured.out
            assert "pattern_b" in captured.out
            assert "Claude Code" in captured.out
            assert "Cursor" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Tests for print_guardian_status()
# ============================================

class TestPrintGuardianStatus:
    """Tests for print_guardian_status()."""

    def test_prints_active_status_with_agent(self, capsys):
        """Print guardian active status with agent name."""
        config = {"guardian": {"enabled": True, "force": True}}
        with patch.dict(os.environ, {"CLAUDE_CODE": "1"}, clear=True):
            print_guardian_status(config)
            captured = capsys.readouterr()
            assert "GUARDIAN MODE ACTIVE" in captured.out
            assert "Claude Code" in captured.out

    def test_prints_active_status_without_agent(self, capsys):
        """Print guardian active status without agent name."""
        config = {"guardian": {"enabled": True, "force": True}}
        with patch.dict(os.environ, {}, clear=True):
            print_guardian_status(config)
            captured = capsys.readouterr()
            assert "GUARDIAN MODE ACTIVE" in captured.out

    def test_prints_warnings_elevated_note(self, capsys):
        """Print note when warnings are elevated."""
        config = {
            "guardian": {
                "enabled": True,
                "force": True,
                "warnings_as_blocking": True,
            }
        }
        with patch.dict(os.environ, {}, clear=True):
            print_guardian_status(config)
            captured = capsys.readouterr()
            assert "Warnings elevated to blocking" in captured.out

    def test_prints_nothing_when_guardian_disabled(self, capsys):
        """Print nothing when guardian is not active."""
        config = {"guardian": {"enabled": False}}
        with patch.dict(os.environ, {}, clear=True):
            print_guardian_status(config)
            captured = capsys.readouterr()
            assert "GUARDIAN MODE ACTIVE" not in captured.out


# ============================================
# Symlink Protection Tests
# ============================================

class TestSymlinkProtection:
    """Tests for symlink attack protection."""

    def test_log_guardian_block_detects_symlink_attack(self, tmp_path, capsys):
        """log_guardian_block detects symlink pointing outside project."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create a symlink pointing outside
            outside_dir = tmp_path.parent / "outside_guardian_test"
            outside_dir.mkdir(exist_ok=True)

            vibesrails_link = tmp_path / ".vibesrails"
            vibesrails_link.symlink_to(outside_dir)

            result = ScanResult("test.py", 1, "p1", "M", "BLOCK")
            log_guardian_block(result, "Agent")

            captured = capsys.readouterr()
            assert "symlink outside project" in captured.out

            # Cleanup
            vibesrails_link.unlink()
            outside_dir.rmdir()
        finally:
            os.chdir(original_cwd)

    def test_get_guardian_stats_detects_symlink_attack(self, tmp_path):
        """get_guardian_stats detects symlink pointing outside project."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create outside directory with a fake log
            outside_dir = tmp_path.parent / "outside_stats_test"
            outside_dir.mkdir(exist_ok=True)
            fake_log = outside_dir / "guardian.log"
            fake_log.write_text('{"pattern_id": "fake", "agent": "Evil"}\n')

            # Create symlink
            vibesrails_link = tmp_path / ".vibesrails"
            vibesrails_link.symlink_to(outside_dir)

            stats = get_guardian_stats()

            # Should return error indicator, not read the fake log
            assert stats.get("error") == "symlink_detected"
            assert stats["total_blocks"] == 0

            # Cleanup
            vibesrails_link.unlink()
            fake_log.unlink()
            outside_dir.rmdir()
        finally:
            os.chdir(original_cwd)
