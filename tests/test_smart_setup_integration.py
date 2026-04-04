"""Tests for smart_setup claude_integration, advanced_patterns, core, and integration."""

import json
from unittest import mock

import pytest

import vibesrails.smart_setup.core as _core_mod

# ============================================
# Claude Integration Tests
# ============================================

class TestClaudeIntegration:
    """Tests for claude_integration module: CLAUDE.md and hooks."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def test_get_package_data_path_exists(self):
        """get_package_data_path returns path for existing file."""
        from vibesrails.smart_setup.claude_integration import get_package_data_path

        # Try to get a path that might exist
        result = get_package_data_path("__init__.py")
        # Either returns a path or None
        assert result is None or result.exists()

    def test_get_package_data_path_nonexistent(self):
        """get_package_data_path returns None for missing file."""
        from vibesrails.smart_setup.claude_integration import get_package_data_path

        result = get_package_data_path("definitely_does_not_exist_12345.txt")
        assert result is None

    def test_generate_claude_md_content(self):
        """generate_claude_md returns valid content."""
        from vibesrails.smart_setup.claude_integration import generate_claude_md

        result = generate_claude_md()

        assert "vibesrails" in result
        assert "CLAUDE" in result or "Claude" in result or "claude" in result
        # Should contain instructions about secrets
        assert "secret" in result.lower() or "api" in result.lower()

    def test_generate_claude_md_has_examples(self):
        """generate_claude_md includes code examples."""
        from vibesrails.smart_setup.claude_integration import generate_claude_md

        result = generate_claude_md()

        # Should have code blocks
        assert "```" in result

    def test_install_claude_hooks_creates_dir(self, project_dir):
        """install_claude_hooks creates .claude directory."""
        import vibesrails.smart_setup.claude_integration as _ci
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        # Mock get_package_data_path to return a valid hooks file
        hooks_content = {"hooks": {"PreToolUse": [{"command": "vibesrails scan"}]}}
        hooks_file = project_dir / "hooks_source.json"
        hooks_file.write_text(json.dumps(hooks_content))

        with mock.patch.object(_ci, 'get_package_data_path', return_value=hooks_file):
            result = install_claude_hooks(project_dir)

        assert result is True
        assert (project_dir / ".claude").exists()

    def test_install_claude_hooks_creates_file(self, project_dir):
        """install_claude_hooks creates hooks.json."""
        import vibesrails.smart_setup.claude_integration as _ci
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        hooks_content = {"hooks": {"PreToolUse": [{"command": "vibesrails scan"}]}}
        hooks_file = project_dir / "hooks_source.json"
        hooks_file.write_text(json.dumps(hooks_content))

        with mock.patch.object(_ci, 'get_package_data_path', return_value=hooks_file):
            result = install_claude_hooks(project_dir)

        assert result is True
        assert (project_dir / ".claude" / "hooks.json").exists()

        # Verify content
        created = json.loads((project_dir / ".claude" / "hooks.json").read_text())
        assert "hooks" in created

    def test_install_claude_hooks_merges_existing(self, project_dir):
        """install_claude_hooks merges with existing hooks."""
        import vibesrails.smart_setup.claude_integration as _ci
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        # Create existing hooks
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        existing = {"hooks": {"PostToolUse": [{"command": "echo done"}]}}
        (claude_dir / "hooks.json").write_text(json.dumps(existing))

        # Source hooks
        hooks_content = {"hooks": {"PreToolUse": [{"command": "vibesrails scan"}]}}
        hooks_file = project_dir / "hooks_source.json"
        hooks_file.write_text(json.dumps(hooks_content))

        with mock.patch.object(_ci, 'get_package_data_path', return_value=hooks_file):
            result = install_claude_hooks(project_dir)

        assert result is True

        # Verify merge
        merged = json.loads((claude_dir / "hooks.json").read_text())
        assert "PreToolUse" in merged["hooks"]
        assert "PostToolUse" in merged["hooks"]

    def test_install_claude_hooks_uses_generator(self, project_dir):
        """install_claude_hooks delegates to hook_generator (no template needed)."""
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        result = install_claude_hooks(project_dir)

        assert result is True
        hooks_path = project_dir / ".claude" / "hooks.json"
        assert hooks_path.exists()
        content = json.loads(hooks_path.read_text())
        assert "PreToolUse" in content["hooks"]

    def test_install_claude_hooks_avoids_duplicates(self, project_dir):
        """install_claude_hooks doesn't duplicate vibesrails hooks."""
        import vibesrails.smart_setup.claude_integration as _ci
        from vibesrails.smart_setup.claude_integration import install_claude_hooks

        # Create existing hooks with vibesrails already
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        existing = {"hooks": {"PreToolUse": [{"command": "vibesrails scan --staged"}]}}
        (claude_dir / "hooks.json").write_text(json.dumps(existing))

        # Source hooks also have vibesrails
        hooks_content = {"hooks": {"PreToolUse": [{"command": "vibesrails scan --all"}]}}
        hooks_file = project_dir / "hooks_source.json"
        hooks_file.write_text(json.dumps(hooks_content))

        with mock.patch.object(_ci, 'get_package_data_path', return_value=hooks_file):
            result = install_claude_hooks(project_dir)

        assert result is True

        # Verify no duplicate
        merged = json.loads((claude_dir / "hooks.json").read_text())
        vibesrails_hooks = [h for h in merged["hooks"]["PreToolUse"] if "vibesrails" in h.get("command", "")]
        assert len(vibesrails_hooks) == 1


# ============================================
# Advanced Patterns Tests
# ============================================

class TestAdvancedPatterns:
    """Tests for advanced_patterns module: regex validation and preview."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def test_validate_regex_valid(self, project_dir):
        """Valid regex passes validation."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        (project_dir / "test.py").write_text("password = 'secret123'")

        is_valid, preview = validate_and_preview_regex(r"password\s*=", project_dir)

        assert is_valid is True
        assert len(preview) > 0  # Should have matches

    def test_validate_regex_invalid(self, project_dir):
        """Invalid regex fails validation."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        is_valid, preview = validate_and_preview_regex(r"[unclosed", project_dir)

        assert is_valid is False
        assert "invalide" in preview[0].lower() or "invalid" in preview[0].lower()

    def test_validate_regex_redos_detection(self, project_dir):
        """Dangerous ReDoS patterns are detected."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        # This pattern causes catastrophic backtracking
        is_valid, preview = validate_and_preview_regex(r"(.*)+$", project_dir)

        assert is_valid is False
        assert "ReDoS" in preview[0] or "dangereuse" in preview[0]

    def test_validate_regex_preview_matches(self, project_dir):
        """Preview shows matching lines."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        (project_dir / "main.py").write_text("api_key = 'abc123'\nother_code = True")

        is_valid, preview = validate_and_preview_regex(r"api_key", project_dir)

        assert is_valid is True
        assert any("api_key" in p for p in preview)

    def test_validate_regex_no_matches(self, project_dir):
        """Preview empty when no matches."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        (project_dir / "main.py").write_text("print('hello')")

        is_valid, preview = validate_and_preview_regex(r"definitely_not_here_12345", project_dir)

        assert is_valid is True
        assert preview == []

    def test_validate_regex_limits_output(self, project_dir):
        """Preview limits number of matches."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        # Create many matching files
        for i in range(10):
            (project_dir / f"file{i}.py").write_text("match_pattern = 1\n" * 10)

        is_valid, preview = validate_and_preview_regex(r"match_pattern", project_dir)

        assert is_valid is True
        # Should be limited (max 5 files * 3 lines = 15)
        assert len(preview) <= 15

    def test_validate_regex_handles_long_lines(self, project_dir):
        """Preview skips very long lines."""
        from vibesrails.smart_setup.advanced_patterns import validate_and_preview_regex

        long_line = "x" * 600 + " password = secret"
        (project_dir / "main.py").write_text(long_line)

        is_valid, preview = validate_and_preview_regex(r"password", project_dir)

        assert is_valid is True
        # Long line should be skipped
        assert preview == []


# ============================================
# Core Module Tests
# ============================================

class TestCore:
    """Tests for core module: main smart_setup logic."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory with minimal structure."""
        (tmp_path / "main.py").write_text("print('hello')")
        return tmp_path

    def test_smart_setup_dry_run(self, project_dir, capsys, monkeypatch):
        """smart_setup in dry_run mode doesn't create files."""
        from vibesrails.smart_setup.core import smart_setup

        # Mock input to avoid prompts
        monkeypatch.setattr('builtins.input', lambda _: "3")  # Skip mode

        result = smart_setup(project_dir, dry_run=True, interactive=False)

        assert result["created"] is False
        assert "config_content" in result
        assert not (project_dir / "vibesrails.yaml").exists()

    def test_smart_setup_non_interactive(self, project_dir, capsys, monkeypatch):
        """smart_setup in non-interactive mode with force."""
        from vibesrails.smart_setup.core import smart_setup

        # Mock install_hook to avoid git operations (imported from ..cli inside function)
        with mock.patch('vibesrails.cli.install_hook'):
            with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                result = smart_setup(project_dir, dry_run=False, interactive=False, force=True)

        assert result["created"] is True
        assert (project_dir / "vibesrails.yaml").exists()

    def test_smart_setup_detects_project_types(self, project_dir, monkeypatch):
        """smart_setup detects project types correctly."""
        from vibesrails.smart_setup.core import smart_setup

        # Add FastAPI marker
        (project_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")

        result = smart_setup(project_dir, dry_run=True, interactive=False)

        assert "fastapi" in result["project_types"]

    def test_smart_setup_existing_config_no_force(self, project_dir, monkeypatch):
        """smart_setup respects existing config without force."""
        from vibesrails.smart_setup.core import smart_setup

        # Create existing config
        (project_dir / "vibesrails.yaml").write_text("version: '1.0'")

        result = smart_setup(project_dir, dry_run=False, interactive=False, force=False)

        assert result["created"] is False
        assert result["reason"] == "exists"

    def test_smart_setup_existing_config_with_force(self, project_dir, monkeypatch):
        """smart_setup overwrites existing config with force."""
        from vibesrails.smart_setup.core import smart_setup

        # Create existing config
        (project_dir / "vibesrails.yaml").write_text("version: '1.0'")

        with mock.patch('vibesrails.cli.install_hook'):
            with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                result = smart_setup(project_dir, dry_run=False, interactive=False, force=True)

        assert result["created"] is True

    def test_smart_setup_creates_claude_md(self, project_dir, monkeypatch):
        """smart_setup creates CLAUDE.md."""
        from vibesrails.smart_setup.core import smart_setup

        with mock.patch('vibesrails.cli.install_hook'):
            with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                result = smart_setup(project_dir, dry_run=False, interactive=False, force=True)

        assert (project_dir / "CLAUDE.md").exists()
        assert result.get("claude_md_created") is True

    def test_smart_setup_updates_existing_claude_md(self, project_dir, monkeypatch):
        """smart_setup appends to existing CLAUDE.md."""
        from vibesrails.smart_setup.core import smart_setup

        # Create existing CLAUDE.md without vibesrails
        (project_dir / "CLAUDE.md").write_text("# Project Docs\n\nSome content")

        with mock.patch('vibesrails.cli.install_hook'):
            with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                smart_setup(project_dir, dry_run=False, interactive=False, force=True)

        content = (project_dir / "CLAUDE.md").read_text()
        assert "Project Docs" in content  # Original content preserved
        assert "vibesrails" in content.lower()  # New content added

    def test_smart_setup_skips_claude_md_if_already_has_vibesrails(self, project_dir, monkeypatch, capsys):
        """smart_setup doesn't duplicate vibesrails in CLAUDE.md."""
        from vibesrails.smart_setup.core import smart_setup

        # Create existing CLAUDE.md with vibesrails content
        (project_dir / "CLAUDE.md").write_text("# vibesrails instructions\n\nExisting vibesrails content")

        with mock.patch('vibesrails.cli.install_hook'):
            with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                smart_setup(project_dir, dry_run=False, interactive=False, force=True)

        content = (project_dir / "CLAUDE.md").read_text()
        # Should not have duplicate vibesrails sections
        assert content.count("vibesrails") <= 3  # Just the existing mentions

    def test_smart_setup_interactive_cancelled(self, project_dir, monkeypatch, capsys):
        """smart_setup can be cancelled by user."""
        from vibesrails.smart_setup.core import smart_setup

        # Mock prompts: mode=3 (skip), then 'n' for create confirmation
        inputs = iter(["3", "n"])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        result = smart_setup(project_dir, dry_run=False, interactive=True, force=True)

        assert result["created"] is False

    def test_smart_setup_returns_all_fields(self, project_dir):
        """smart_setup returns all expected fields."""
        from vibesrails.smart_setup.core import smart_setup

        result = smart_setup(project_dir, dry_run=True, interactive=False)

        expected_fields = [
            "project_root", "project_types", "existing_configs",
            "has_secrets", "env_files", "extra_patterns", "config_content"
        ]
        for field in expected_fields:
            assert field in result

    def test_run_smart_setup_cli_success(self, project_dir, monkeypatch):
        """run_smart_setup_cli returns True on success."""
        from vibesrails.smart_setup.core import run_smart_setup_cli

        # Change to project dir
        monkeypatch.chdir(project_dir)

        # Mock isatty to return False (non-interactive)
        with mock.patch('os.isatty', return_value=False):
            with mock.patch('vibesrails.cli.install_hook'):
                with mock.patch.object(_core_mod, 'install_claude_hooks', return_value=True):
                    result = run_smart_setup_cli(force=True, dry_run=False)

        assert result is True

    def test_run_smart_setup_cli_dry_run(self, project_dir, monkeypatch):
        """run_smart_setup_cli in dry_run mode."""
        from vibesrails.smart_setup.core import run_smart_setup_cli

        monkeypatch.chdir(project_dir)

        with mock.patch('os.isatty', return_value=False):
            result = run_smart_setup_cli(force=False, dry_run=True)

        assert result is True  # dry_run always returns True

    def test_run_smart_setup_cli_error_handling(self, project_dir, monkeypatch, capsys):
        """run_smart_setup_cli handles errors gracefully."""
        from vibesrails.smart_setup.core import run_smart_setup_cli

        monkeypatch.chdir(project_dir)

        # Mock smart_setup to raise exception
        with mock.patch.object(_core_mod, 'smart_setup', side_effect=Exception("Test error")):
            result = run_smart_setup_cli(force=True, dry_run=False)

        assert result is False
        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out.lower()


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests for smart_setup package."""

    @pytest.fixture
    def realistic_project(self, tmp_path):
        """Create a realistic project structure."""
        project = tmp_path / "myproject"
        project.mkdir()

        # Create package structure
        pkg = project / "myproject"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("__version__ = '1.0.0'")

        # Domain layer
        domain = pkg / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("")
        (domain / "models.py").write_text("class User:\n    pass")

        # API layer
        api = pkg / "api"
        api.mkdir()
        (api / "__init__.py").write_text("")
        (api / "routes.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()")

        # Config files
        (project / "pyproject.toml").write_text("[build-system]\nrequires = ['setuptools']")
        (project / ".env").write_text("API_KEY=test123")

        return project

    def test_full_detection_flow(self, realistic_project):
        """Test full detection on realistic project."""
        from vibesrails.smart_setup.detection import (
            detect_architecture_complexity,
            detect_env_files,
            detect_existing_configs,
            detect_project_type,
        )

        # Detect project type
        types = detect_project_type(realistic_project)
        assert "fastapi" in types

        # Detect configs
        configs = detect_existing_configs(realistic_project)
        assert "pyproject" in configs

        # Detect env files
        env_files = detect_env_files(realistic_project)
        assert len(env_files) == 1

        # Detect architecture
        arch = detect_architecture_complexity(realistic_project)
        assert arch["needs_arch"] is True
        assert arch["language"] == "python"

    def test_full_config_generation(self, realistic_project):
        """Test full config generation on realistic project."""
        from vibesrails.smart_setup.config_gen import generate_config_with_extras
        from vibesrails.smart_setup.detection import (
            detect_env_files,
            detect_existing_configs,
            detect_project_type,
        )

        types = detect_project_type(realistic_project)
        env_files = detect_env_files(realistic_project)
        configs = detect_existing_configs(realistic_project)

        config = generate_config_with_extras(
            project_types=types,
            has_secrets=True,
            env_files=env_files,
            existing_configs=configs,
            extra_patterns=[],
            architecture={"enabled": True, "language": "python", "layers": ["backend/domain", "backend/infrastructure", "backend/api"]},
        )

        assert "@vibesrails/fastapi-pack" in config
        assert "architecture:" in config
        assert "dip_domain_infra" in config
        assert "blocking:" in config

    def test_imports_from_package(self):
        """Test all public imports work from package."""
        from vibesrails.smart_setup import (
            MESSAGES,
            # Constants
            PROJECT_SIGNATURES,
            detect_project_type,
            smart_setup,
        )

        # All imports should work
        assert callable(smart_setup)
        assert callable(detect_project_type)
        assert isinstance(PROJECT_SIGNATURES, dict)
        assert isinstance(MESSAGES, dict)
