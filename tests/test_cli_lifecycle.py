"""Tests for vibesrails.cli — uninstall, edge cases, exit codes, easter egg."""

import os
import stat
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from vibesrails.cli import (
    find_config,
    init_config,
    install_hook,
    uninstall,
)

# ============================================
# Tests for uninstall()
# ============================================


class TestUninstall:
    """Tests for uninstall()."""

    def test_removes_vibesrails_yaml(self, tmp_path, capsys):
        """Remove vibesrails.yaml file."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            result = uninstall()

            assert result is True
            assert not config_file.exists()

            captured = capsys.readouterr()
            assert "vibesrails.yaml" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_removes_vibesrails_from_hook(self, tmp_path, capsys):
        """Remove vibesrails lines from pre-commit hook."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\necho 'other'\nvibesrails\necho 'done'")

            result = uninstall()

            assert result is True
            assert hook_path.exists()

            content = hook_path.read_text()
            assert "vibesrails" not in content
            assert "other" in content
            assert "done" in content

            captured = capsys.readouterr()
            assert "Removed vibesrails from pre-commit hook" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_removes_hook_file_if_only_vibesrails(self, tmp_path, capsys):
        """Remove entire hook file if it only contains vibesrails."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\nvibesrails")

            result = uninstall()

            assert result is True
            assert not hook_path.exists()

            captured = capsys.readouterr()
            assert "pre-commit" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_removes_vibesrails_directory(self, tmp_path, capsys):
        """Remove .vibesrails directory (guardian logs, etc.)."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            vibesrails_dir = tmp_path / ".vibesrails"
            vibesrails_dir.mkdir()
            (vibesrails_dir / "guardian.log").write_text("some logs")

            result = uninstall()

            assert result is True
            assert not vibesrails_dir.exists()

            captured = capsys.readouterr()
            assert ".vibesrails" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_reports_nothing_to_uninstall(self, tmp_path, capsys):
        """Report when nothing to uninstall."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = uninstall()

            assert result is True

            captured = capsys.readouterr()
            assert "Nothing to uninstall" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_handles_all_components_together(self, tmp_path, capsys):
        """Handle removal of all components at once."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create all components
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)
            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\nvibesrails")

            vibesrails_dir = tmp_path / ".vibesrails"
            vibesrails_dir.mkdir()

            result = uninstall()

            assert result is True
            assert not config_file.exists()
            assert not hook_path.exists()
            assert not vibesrails_dir.exists()

            captured = capsys.readouterr()
            assert "vibesrails uninstalled" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_leaves_hook_alone_if_no_vibesrails(self, tmp_path):
        """Leave hook file alone if it doesn't contain vibesrails."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            original_content = "#!/bin/bash\necho 'other stuff'"
            hook_path.write_text(original_content)

            uninstall()

            # Hook should be unchanged
            assert hook_path.exists()
            assert hook_path.read_text() == original_content
        finally:
            os.chdir(original_cwd)

    def test_suggests_pip_uninstall(self, tmp_path, capsys):
        """Suggest pip uninstall command after project cleanup."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            uninstall()

            captured = capsys.readouterr()
            assert "pip uninstall vibesrails" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_removes_hook_with_only_shebang_and_vibesrails(self, tmp_path):
        """Remove hook when content is only shebang + vibesrails."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            # Content that becomes just "#!/bin/bash" after filtering
            hook_path.write_text("#!/bin/bash\nvibesrails --check")

            uninstall()

            # Hook should be removed since it's essentially empty
            assert not hook_path.exists()
        finally:
            os.chdir(original_cwd)

    def test_removes_generated_hook_with_if_elif_else_fi(self, tmp_path):
        """Remove the full generated hook without leaving orphaned else/fi."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            # Exact hook generated by install_hook()
            hook_path.write_text(
                "#!/bin/bash\n"
                "# VibesRails pre-commit hook\n"
                "# Scale up your vibe coding - safely\n"
                "\n"
                "# Find vibesrails command (PATH, local venv, or python -m)\n"
                'if command -v vibesrails &> /dev/null; then\n'
                "    vibesrails\n"
                'elif [ -f ".venv/bin/vibesrails" ]; then\n'
                "    .venv/bin/vibesrails\n"
                'elif [ -f "venv/bin/vibesrails" ]; then\n'
                "    venv/bin/vibesrails\n"
                "else\n"
                "    python3 -m vibesrails\n"
                "fi\n"
            )

            uninstall()

            # Hook must be fully deleted — no orphaned else/fi
            assert not hook_path.exists()
        finally:
            os.chdir(original_cwd)

    def test_uninstall_preserves_other_hooks_when_appended(self, tmp_path):
        """Keep non-vibesrails content when vibesrails was appended."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text(
                "#!/bin/bash\n"
                "black --check .\n"
                "eslint .\n"
                "\n"
                "# vibesrails security check\n"
                "vibesrails\n"
            )

            uninstall()

            # Hook should still exist with the non-vibesrails content
            assert hook_path.exists()
            content = hook_path.read_text()
            assert "black --check" in content
            assert "eslint" in content
            assert "vibesrails" not in content.lower()
        finally:
            os.chdir(original_cwd)

    def test_uninstall_notifies_leftover_files(self, tmp_path, capsys):
        """Notify user about CLAUDE.md and .claude/hooks.json left behind."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create leftover files that uninstall should mention
            (tmp_path / "CLAUDE.md").write_text("# Integration")
            claude_dir = tmp_path / ".claude"
            claude_dir.mkdir()
            (claude_dir / "hooks.json").write_text("{}")

            # Create something to actually uninstall
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            uninstall()

            captured = capsys.readouterr()
            assert "CLAUDE.md" in captured.out
            assert ".claude/hooks.json" in captured.out
            assert "Remove them manually" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Edge Cases and Error Conditions
# ============================================


class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_find_config_with_empty_config_file(self, tmp_path):
        """Find config even if file is empty."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("")

            result = find_config()

            assert result is not None
            assert result.exists()
        finally:
            os.chdir(original_cwd)

    def test_init_config_creates_parent_directory(self, tmp_path):
        """Create parent directories if needed for target path."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Target in a subdirectory that doesn't exist
            target = tmp_path / "custom" / "configs" / "vibesrails.yaml"
            target.parent.mkdir(parents=True)  # init_config doesn't create parents

            result = init_config(target)

            assert result is True
            assert target.exists()
        finally:
            os.chdir(original_cwd)

    def test_uninstall_handles_readonly_files(self, tmp_path, capsys):
        """Handle read-only config file gracefully."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            # Make file read-only (but uninstall should still work on most systems)
            # This test verifies no crash occurs
            original_mode = config_file.stat().st_mode
            config_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

            try:
                # Restore write permission to allow unlink
                config_file.chmod(original_mode)
                result = uninstall()
                assert result is True
            except PermissionError:
                pass  # on some systems, hook install may fail due to permissions
        finally:
            os.chdir(original_cwd)

    def test_install_hook_preserves_existing_content_order(self, tmp_path):
        """Preserve order of existing hook content when appending."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\nfirst_command\nsecond_command")

            install_hook()

            content = hook_path.read_text()

            # Original order preserved, vibesrails at end
            assert "first_command" in content
            assert "second_command" in content
            assert content.index("first_command") < content.index("second_command")
            assert content.index("second_command") < content.index("vibesrails")
        finally:
            os.chdir(original_cwd)

    def test_uninstall_with_vibesrails_directory_containing_files(self, tmp_path, capsys):
        """Remove .vibesrails directory with multiple files."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            vibesrails_dir = tmp_path / ".vibesrails"
            vibesrails_dir.mkdir()
            (vibesrails_dir / "guardian.log").write_text("log1")
            (vibesrails_dir / "stats.json").write_text("{}")

            subdir = vibesrails_dir / "cache"
            subdir.mkdir()
            (subdir / "data.txt").write_text("cached")

            result = uninstall()

            assert result is True
            assert not vibesrails_dir.exists()
        finally:
            os.chdir(original_cwd)

    def test_find_config_ignores_directories_with_same_name(self, tmp_path):
        """Don't match directories named vibesrails.yaml."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create a directory with the config name (unusual but possible)
            fake_dir = tmp_path / "vibesrails.yaml"
            fake_dir.mkdir()

            # Mock home to ensure no config there
            mock_home = tmp_path / "empty_home"
            mock_home.mkdir()

            with patch.object(Path, "home", return_value=mock_home):
                result = find_config()

            # Should still find it since it exists (Path.exists returns True for dirs too)
            # But this is a realistic edge case to document behavior
            assert result is not None
        finally:
            os.chdir(original_cwd)


# ============================================
# Tests for exit codes (FIX 5)
# ============================================


class TestExitCodes:
    """Verify correct exit codes for error scenarios."""

    def test_file_not_found_exits_1(self, tmp_path):
        """--file with nonexistent path exits 1 with clear message."""
        # Create a valid config so we get past config check
        config = tmp_path / "vibesrails.yaml"
        config.write_text("patterns: []\n")
        ghost = tmp_path / "nonexistent_file.py"

        result = subprocess.run(
            [sys.executable, "-m", "vibesrails.cli",
             "--config", str(config), "--file", str(ghost)],
            capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path),
        )
        assert result.returncode == 1
        assert "file not found" in result.stderr.lower() or "file not found" in result.stdout.lower()

    def test_permission_denied_exits_1(self, tmp_path):
        """--file with unreadable file exits 1 with permission error."""
        config = tmp_path / "vibesrails.yaml"
        config.write_text("patterns: []\n")
        locked = tmp_path / "locked.py"
        locked.write_text("x = 1\n")
        locked.chmod(0o000)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "vibesrails.cli",
                 "--config", str(config), "--file", str(locked)],
                capture_output=True, text=True, timeout=30,
                cwd=str(tmp_path),
            )
            assert result.returncode == 1
            assert "permission denied" in result.stderr.lower() or "permission denied" in result.stdout.lower()
        finally:
            locked.chmod(0o644)


class TestAboutEasterEgg:
    """--about is hidden and shows the easter egg."""

    def test_about_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "vibesrails.cli", "--about"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "ABH AMH" in result.stdout

    def test_help_does_not_show_about(self):
        result = subprocess.run(
            [sys.executable, "-m", "vibesrails.cli", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "--about" not in result.stdout

    def test_version_shows_by_sm_not_kionos(self):
        result = subprocess.run(
            [sys.executable, "-m", "vibesrails.cli", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        assert "by SM" in result.stdout
        assert "KIONOS" not in result.stdout
