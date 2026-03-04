"""Tests for vibesrails.cli — config discovery, init, hook installation."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

from vibesrails.cli import (
    find_config,
    get_default_config_path,
    init_config,
    install_hook,
)

# ============================================
# Tests for find_config()
# ============================================


class TestFindConfig:
    """Tests for find_config()."""

    def test_finds_config_in_project_root(self, tmp_path):
        """Find vibesrails.yaml in project root (highest priority)."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_file = tmp_path / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            result = find_config()

            assert result is not None
            assert result.exists()
            assert result.name == "vibesrails.yaml"
        finally:
            os.chdir(original_cwd)

    def test_finds_config_in_config_subdir(self, tmp_path):
        """Find vibesrails.yaml in config/ subdirectory."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            config_dir = tmp_path / "config"
            config_dir.mkdir()
            config_file = config_dir / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            result = find_config()

            assert result is not None
            assert result.exists()
            assert "config" in str(result)
        finally:
            os.chdir(original_cwd)

    def test_finds_config_in_user_home(self, tmp_path):
        """Find vibesrails.yaml in ~/.config/vibesrails/."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock Path.home() to return a controlled path
            mock_home = tmp_path / "mock_home"
            mock_home.mkdir()
            config_dir = mock_home / ".config" / "vibesrails"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "vibesrails.yaml"
            config_file.write_text("version: '1.0'")

            with patch.object(Path, "home", return_value=mock_home):
                result = find_config()

            assert result is not None
            assert result.exists()
        finally:
            os.chdir(original_cwd)

    def test_returns_none_when_no_config_found(self, tmp_path):
        """Return None when no config file exists anywhere."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock Path.home() to ensure no home config
            mock_home = tmp_path / "empty_home"
            mock_home.mkdir()

            with patch.object(Path, "home", return_value=mock_home):
                result = find_config()

            assert result is None
        finally:
            os.chdir(original_cwd)

    def test_project_root_takes_priority_over_config_subdir(self, tmp_path):
        """Project root vibesrails.yaml takes priority over config/ subdir."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create both configs
            root_config = tmp_path / "vibesrails.yaml"
            root_config.write_text("location: root")

            config_dir = tmp_path / "config"
            config_dir.mkdir()
            subdir_config = config_dir / "vibesrails.yaml"
            subdir_config.write_text("location: subdir")

            result = find_config()

            assert result is not None
            assert result.read_text() == "location: root"
        finally:
            os.chdir(original_cwd)

    def test_config_subdir_takes_priority_over_home(self, tmp_path):
        """config/ subdir takes priority over user home config."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create config in subdir
            config_dir = tmp_path / "config"
            config_dir.mkdir()
            subdir_config = config_dir / "vibesrails.yaml"
            subdir_config.write_text("location: subdir")

            # Create config in mock home
            mock_home = tmp_path / "mock_home"
            mock_home.mkdir()
            home_config_dir = mock_home / ".config" / "vibesrails"
            home_config_dir.mkdir(parents=True)
            home_config = home_config_dir / "vibesrails.yaml"
            home_config.write_text("location: home")

            with patch.object(Path, "home", return_value=mock_home):
                result = find_config()

            assert result is not None
            assert result.read_text() == "location: subdir"
        finally:
            os.chdir(original_cwd)


# ============================================
# Tests for get_default_config_path()
# ============================================


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path()."""

    def test_returns_path_to_default_yaml(self):
        """Return path to bundled default.yaml."""
        result = get_default_config_path()

        assert isinstance(result, Path)
        assert result.name == "default.yaml"
        assert "config" in str(result)

    def test_default_config_exists(self):
        """Bundled default.yaml actually exists."""
        result = get_default_config_path()

        assert result.exists()

    def test_default_config_is_valid_yaml(self):
        """Bundled default.yaml contains valid YAML."""
        import yaml

        result = get_default_config_path()
        content = result.read_text()
        config = yaml.safe_load(content)

        assert "version" in config
        assert "blocking" in config

    def test_path_is_inside_package(self):
        """Path is within the vibesrails package directory."""
        result = get_default_config_path()

        # Should be in vibesrails/config/default.yaml
        assert "vibesrails" in str(result)


# ============================================
# Tests for init_config()
# ============================================


class TestInitConfig:
    """Tests for init_config()."""

    def test_creates_vibesrails_yaml(self, tmp_path, capsys):
        """Create vibesrails.yaml in specified location."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            target = tmp_path / "vibesrails.yaml"
            result = init_config(target)

            assert result is True
            assert target.exists()

            captured = capsys.readouterr()
            assert "Created" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_copies_content_from_default_config(self, tmp_path):
        """Copied config contains same content as default."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            target = tmp_path / "vibesrails.yaml"
            init_config(target)

            default_content = get_default_config_path().read_text()
            target_content = target.read_text()

            assert target_content == default_content
        finally:
            os.chdir(original_cwd)

    def test_returns_false_if_config_already_exists(self, tmp_path, capsys):
        """Return False if vibesrails.yaml already exists."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            target = tmp_path / "vibesrails.yaml"
            target.write_text("existing config")

            result = init_config(target)

            assert result is False

            captured = capsys.readouterr()
            assert "already exists" in captured.out

            # Content should be unchanged
            assert target.read_text() == "existing config"
        finally:
            os.chdir(original_cwd)

    def test_uses_default_target_path(self, tmp_path, capsys):
        """Use default target path (vibesrails.yaml in cwd)."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = init_config()

            assert result is True
            assert (tmp_path / "vibesrails.yaml").exists()
        finally:
            os.chdir(original_cwd)

    def test_prints_next_steps(self, tmp_path, capsys):
        """Print helpful next steps after initialization."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            target = tmp_path / "vibesrails.yaml"
            init_config(target)

            captured = capsys.readouterr()
            assert "Next steps" in captured.out
            assert "--hook" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_returns_false_when_default_config_missing(self, tmp_path, capsys):
        """Return False when bundled default config is missing."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            target = tmp_path / "vibesrails.yaml"

            # Mock get_default_config_path to return non-existent path
            fake_path = tmp_path / "nonexistent" / "default.yaml"
            with patch("vibesrails.cli_setup.get_default_config_path", return_value=fake_path):
                result = init_config(target)

            assert result is False

            captured = capsys.readouterr()
            assert "ERROR" in captured.out
            assert "Default config not found" in captured.out
        finally:
            os.chdir(original_cwd)


# ============================================
# Tests for install_hook()
# ============================================


class TestInstallHook:
    """Tests for install_hook()."""

    def test_creates_pre_commit_hook(self, tmp_path, capsys):
        """Create pre-commit hook in .git/hooks/."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create git directory
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            result = install_hook()

            assert result is True

            hook_path = git_dir / "hooks" / "pre-commit"
            assert hook_path.exists()

            captured = capsys.readouterr()
            assert "Git hook installed" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_hook_content_contains_vibesrails_command(self, tmp_path):
        """Hook content contains vibesrails command."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            install_hook()

            hook_path = git_dir / "hooks" / "pre-commit"
            content = hook_path.read_text()

            assert "vibesrails" in content
            assert "#!/bin/bash" in content
        finally:
            os.chdir(original_cwd)

    def test_hook_is_executable(self, tmp_path):
        """Hook file has executable permissions."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            install_hook()

            hook_path = git_dir / "hooks" / "pre-commit"
            mode = hook_path.stat().st_mode

            # Check that file is executable by owner
            assert mode & stat.S_IXUSR
        finally:
            os.chdir(original_cwd)

    def test_creates_hooks_directory_if_missing(self, tmp_path):
        """Create hooks directory if it doesn't exist."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()
            # Note: hooks dir is NOT created

            install_hook()

            hooks_dir = git_dir / "hooks"
            assert hooks_dir.exists()
        finally:
            os.chdir(original_cwd)

    def test_returns_false_if_not_git_repo(self, tmp_path, capsys):
        """Return False if not in a git repository."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = install_hook()

            assert result is False

            captured = capsys.readouterr()
            assert "ERROR" in captured.out
            assert "Not a git repository" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_appends_to_existing_hook(self, tmp_path, capsys):
        """Append vibesrails to existing pre-commit hook."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\necho 'existing hook'")

            result = install_hook()

            assert result is True

            content = hook_path.read_text()
            assert "existing hook" in content
            assert "vibesrails" in content

            captured = capsys.readouterr()
            assert "Appending to existing" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_does_not_duplicate_if_already_installed(self, tmp_path, capsys):
        """Don't add vibesrails twice if already in hook."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\nvibesrails\n")

            result = install_hook()

            assert result is True

            content = hook_path.read_text()
            assert content.count("vibesrails") == 1

            captured = capsys.readouterr()
            assert "already installed" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_hook_includes_fallback_commands(self, tmp_path):
        """Hook includes fallback commands for different environments."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            install_hook()

            hook_path = git_dir / "hooks" / "pre-commit"
            content = hook_path.read_text()

            # Check for fallback options
            assert ".venv/bin/vibesrails" in content
            assert "venv/bin/vibesrails" in content
            assert "python3 -m vibesrails" in content
        finally:
            os.chdir(original_cwd)

    def test_architecture_check_added_when_enabled(self, tmp_path):
        """Add architecture check when architecture_enabled=True."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            install_hook(architecture_enabled=True)

            hook_path = git_dir / "hooks" / "pre-commit"
            content = hook_path.read_text()

            assert "lint-imports" in content
            assert "Architecture check" in content
        finally:
            os.chdir(original_cwd)

    def test_no_architecture_check_by_default(self, tmp_path):
        """No architecture check by default."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            git_dir.mkdir()

            install_hook()

            hook_path = git_dir / "hooks" / "pre-commit"
            content = hook_path.read_text()

            assert "lint-imports" not in content
        finally:
            os.chdir(original_cwd)

    def test_update_existing_hook_with_architecture_check(self, tmp_path, capsys):
        """Update existing hook to add architecture check."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_dir = tmp_path / ".git"
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(parents=True)

            hook_path = hooks_dir / "pre-commit"
            hook_path.write_text("#!/bin/bash\nvibesrails\n")

            result = install_hook(architecture_enabled=True)

            assert result is True

            content = hook_path.read_text()
            assert "lint-imports" in content

            captured = capsys.readouterr()
            assert "Updated pre-commit hook with architecture check" in captured.out
        finally:
            os.chdir(original_cwd)
