"""Tests for smart_setup detection & i18n modules."""

import os
from pathlib import Path
from unittest import mock

import pytest

# ============================================
# i18n Module Tests
# ============================================

class TestI18n:
    """Tests for i18n module: language detection and message translation."""

    def test_detect_language_english_default(self):
        """Default language is English when no env set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            # Force reimport to get fresh detection
            from vibesrails.smart_setup import i18n
            # Direct function call
            result = i18n.detect_language()
            assert result == "en"

    def test_detect_language_french_from_lang(self):
        """French detected from LANG env variable."""
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8"}, clear=True):
            from vibesrails.smart_setup import i18n
            result = i18n.detect_language()
            assert result == "fr"

    def test_detect_language_french_from_language(self):
        """French detected from LANGUAGE env variable."""
        with mock.patch.dict(os.environ, {"LANGUAGE": "fr"}, clear=True):
            from vibesrails.smart_setup import i18n
            result = i18n.detect_language()
            assert result == "fr"

    def test_detect_language_french_lowercase(self):
        """French detection is case-insensitive."""
        with mock.patch.dict(os.environ, {"LANG": "FR_CA.UTF-8"}, clear=True):
            from vibesrails.smart_setup import i18n
            result = i18n.detect_language()
            assert result == "fr"

    def test_msg_english_simple(self):
        """msg() returns English translation."""
        from vibesrails.smart_setup.i18n import MESSAGES
        # Use a known key
        assert "smart_setup" in MESSAGES["en"]
        assert MESSAGES["en"]["smart_setup"] == "VibesRails Smart Setup"

    def test_msg_french_simple(self):
        """msg() returns French translation."""
        from vibesrails.smart_setup.i18n import MESSAGES
        assert "smart_setup" in MESSAGES["fr"]
        # French message is same as English for this key
        assert MESSAGES["fr"]["smart_setup"] == "VibesRails Smart Setup"

    def test_msg_with_interpolation(self):
        """msg() supports format interpolation."""
        from vibesrails.smart_setup.i18n import MESSAGES
        # The found_secrets message has {count} placeholder
        en_msg = MESSAGES["en"]["found_secrets"]
        assert "{count}" in en_msg
        # Test interpolation manually
        result = en_msg.format(count=5)
        assert "5" in result

    def test_msg_function_basic(self):
        """msg() function returns correct translation."""
        from vibesrails.smart_setup import i18n
        # Mock LANG to ensure English
        with mock.patch.object(i18n, 'LANG', 'en'):
            result = i18n.msg("smart_setup")
            assert result == "VibesRails Smart Setup"

    def test_msg_function_with_kwargs(self):
        """msg() function interpolates kwargs."""
        from vibesrails.smart_setup import i18n
        with mock.patch.object(i18n, 'LANG', 'en'):
            result = i18n.msg("found_secrets", count=3)
            assert "3" in result

    def test_msg_fallback_to_key(self):
        """msg() returns key if translation not found."""
        from vibesrails.smart_setup import i18n
        with mock.patch.object(i18n, 'LANG', 'en'):
            result = i18n.msg("nonexistent_key_12345")
            assert result == "nonexistent_key_12345"

    def test_msg_fallback_to_english(self):
        """msg() falls back to English for unknown language."""
        from vibesrails.smart_setup import i18n
        with mock.patch.object(i18n, 'LANG', 'de'):  # German not supported
            result = i18n.msg("smart_setup")
            assert result == "VibesRails Smart Setup"


# ============================================
# Detection Module Tests
# ============================================

class TestDetection:
    """Tests for detection module: project analysis functions."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def test_detect_project_type_fastapi(self, project_dir):
        """Detect FastAPI project by file."""
        from vibesrails.smart_setup.detection import detect_project_type

        (project_dir / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
        result = detect_project_type(project_dir)
        assert "fastapi" in result

    def test_detect_project_type_django(self, project_dir):
        """Detect Django project by manage.py."""
        from vibesrails.smart_setup.detection import detect_project_type

        (project_dir / "manage.py").write_text("#!/usr/bin/env python")
        result = detect_project_type(project_dir)
        assert "django" in result

    def test_detect_project_type_flask(self, project_dir):
        """Detect Flask project by import."""
        from vibesrails.smart_setup.detection import detect_project_type

        (project_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)")
        result = detect_project_type(project_dir)
        assert "flask" in result

    def test_detect_project_type_cli(self, project_dir):
        """Detect CLI project by click import."""
        from vibesrails.smart_setup.detection import detect_project_type

        (project_dir / "cli.py").write_text("import click")
        result = detect_project_type(project_dir)
        assert "cli" in result

    def test_detect_project_type_by_import(self, project_dir):
        """Detect project type by import statement."""
        from vibesrails.smart_setup.detection import detect_project_type

        # Create a file with FastAPI import but different filename
        (project_dir / "server.py").write_text("import fastapi\nfrom fastapi import APIRouter")
        result = detect_project_type(project_dir)
        assert "fastapi" in result

    def test_detect_project_type_empty(self, project_dir):
        """Empty project returns empty list."""
        from vibesrails.smart_setup.detection import detect_project_type

        result = detect_project_type(project_dir)
        assert result == []

    def test_detect_project_type_multiple(self, project_dir):
        """Detect multiple project types."""
        from vibesrails.smart_setup.detection import detect_project_type

        (project_dir / "main.py").write_text("from fastapi import FastAPI")
        (project_dir / "cli.py").write_text("import click")
        result = detect_project_type(project_dir)
        assert "fastapi" in result
        assert "cli" in result

    def test_detect_project_type_nested(self, project_dir):
        """Detect project type in nested directory."""
        from vibesrails.smart_setup.detection import detect_project_type

        subdir = project_dir / "src" / "api"
        subdir.mkdir(parents=True)
        (subdir / "main.py").write_text("from fastapi import FastAPI")
        result = detect_project_type(project_dir)
        assert "fastapi" in result

    def test_detect_project_type_handles_read_errors(self, project_dir):
        """detect_project_type handles unreadable files gracefully."""
        from vibesrails.smart_setup.detection import detect_project_type

        # Create file, then mock read to fail
        py_file = project_dir / "test.py"
        py_file.write_text("import fastapi")

        # Mock read_text to raise exception
        with mock.patch.object(Path, 'read_text', side_effect=PermissionError("No access")):
            result = detect_project_type(project_dir)
            # Should not crash, returns empty or partial
            assert isinstance(result, list)

    def test_detect_existing_configs_pyproject(self, project_dir):
        """Detect pyproject.toml."""
        from vibesrails.smart_setup.detection import detect_existing_configs

        (project_dir / "pyproject.toml").write_text("[build-system]")
        result = detect_existing_configs(project_dir)
        assert "pyproject" in result
        assert result["pyproject"] == project_dir / "pyproject.toml"

    def test_detect_existing_configs_multiple(self, project_dir):
        """Detect multiple config files."""
        from vibesrails.smart_setup.detection import detect_existing_configs

        (project_dir / "pyproject.toml").write_text("[build-system]")
        (project_dir / ".pre-commit-config.yaml").write_text("repos: []")
        (project_dir / "ruff.toml").write_text("[lint]")

        result = detect_existing_configs(project_dir)
        assert "pyproject" in result
        assert "pre-commit" in result
        assert "ruff" in result

    def test_detect_existing_configs_empty(self, project_dir):
        """No configs returns empty dict."""
        from vibesrails.smart_setup.detection import detect_existing_configs

        result = detect_existing_configs(project_dir)
        assert result == {}

    def test_detect_secrets_risk_api_key(self, project_dir):
        """Detect API key pattern."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        (project_dir / "config.py").write_text('api_key = "sk-1234567890"')
        result = detect_secrets_risk(project_dir)
        assert result is True

    def test_detect_secrets_risk_password(self, project_dir):
        """Detect password pattern."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        (project_dir / "config.py").write_text('password = "secret123"')
        result = detect_secrets_risk(project_dir)
        assert result is True

    def test_detect_secrets_risk_aws(self, project_dir):
        """Detect AWS pattern."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        (project_dir / "config.py").write_text('AWS_ACCESS_KEY = "AKIA..."')
        result = detect_secrets_risk(project_dir)
        assert result is True

    def test_detect_secrets_risk_openai(self, project_dir):
        """Detect OpenAI pattern."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        (project_dir / "config.py").write_text('OPENAI_API_KEY = "..."')
        result = detect_secrets_risk(project_dir)
        assert result is True

    def test_detect_secrets_risk_none(self, project_dir):
        """No secrets returns False."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        (project_dir / "main.py").write_text("print('hello world')")
        result = detect_secrets_risk(project_dir)
        assert result is False

    def test_detect_secrets_risk_empty(self, project_dir):
        """Empty project returns False."""
        from vibesrails.smart_setup.detection import detect_secrets_risk

        result = detect_secrets_risk(project_dir)
        assert result is False

    def test_detect_env_files_single(self, project_dir):
        """Detect .env file."""
        from vibesrails.smart_setup.detection import detect_env_files

        (project_dir / ".env").write_text("API_KEY=xxx")
        result = detect_env_files(project_dir)
        assert len(result) == 1
        assert result[0].name == ".env"

    def test_detect_env_files_multiple(self, project_dir):
        """Detect multiple .env files."""
        from vibesrails.smart_setup.detection import detect_env_files

        (project_dir / ".env").write_text("API_KEY=xxx")
        (project_dir / ".env.local").write_text("LOCAL_KEY=xxx")
        (project_dir / ".env.prod").write_text("PROD_KEY=xxx")

        result = detect_env_files(project_dir)
        assert len(result) == 3
        names = [f.name for f in result]
        assert ".env" in names
        assert ".env.local" in names
        assert ".env.prod" in names

    def test_detect_env_files_none(self, project_dir):
        """No env files returns empty list."""
        from vibesrails.smart_setup.detection import detect_env_files

        result = detect_env_files(project_dir)
        assert result == []

    def test_detect_project_language_python(self, project_dir):
        """Detect Python as primary language."""
        from vibesrails.smart_setup.detection import detect_project_language

        (project_dir / "main.py").write_text("print('hello')")
        (project_dir / "utils.py").write_text("def foo(): pass")

        result = detect_project_language(project_dir)
        assert result == "python"

    def test_detect_project_language_javascript(self, project_dir):
        """Detect JavaScript as primary language."""
        from vibesrails.smart_setup.detection import detect_project_language

        (project_dir / "index.js").write_text("console.log('hello')")
        (project_dir / "app.js").write_text("const x = 1")
        (project_dir / "utils.js").write_text("export const y = 2")

        result = detect_project_language(project_dir)
        assert result == "javascript"

    def test_detect_project_language_typescript(self, project_dir):
        """Detect TypeScript as primary language."""
        from vibesrails.smart_setup.detection import detect_project_language

        (project_dir / "index.ts").write_text("const x: number = 1")
        (project_dir / "app.ts").write_text("interface Foo {}")
        (project_dir / "utils.tsx").write_text("export const y = 2")

        result = detect_project_language(project_dir)
        assert result == "typescript"

    def test_detect_project_language_excludes_venv(self, project_dir):
        """Python files in venv are excluded."""
        from vibesrails.smart_setup.detection import detect_project_language

        # Create venv with lots of Python files
        venv = project_dir / ".venv" / "lib" / "python3.12"
        venv.mkdir(parents=True)
        for i in range(10):
            (venv / f"module{i}.py").write_text("pass")

        # Single JS file should win
        (project_dir / "app.js").write_text("console.log('hi')")

        result = detect_project_language(project_dir)
        assert result == "javascript"

    def test_detect_project_language_excludes_node_modules(self, project_dir):
        """JS files in node_modules are excluded."""
        from vibesrails.smart_setup.detection import detect_project_language

        # Create node_modules with lots of JS files
        nm = project_dir / "node_modules" / "lodash"
        nm.mkdir(parents=True)
        for i in range(10):
            (nm / f"module{i}.js").write_text("module.exports = {}")

        # Single Python file should win
        (project_dir / "main.py").write_text("print('hi')")

        result = detect_project_language(project_dir)
        assert result == "python"

    def test_detect_architecture_complexity_simple(self, project_dir):
        """Simple project doesn't need architecture checking."""
        from vibesrails.smart_setup.detection import detect_architecture_complexity

        (project_dir / "main.py").write_text("print('hello')")

        result = detect_architecture_complexity(project_dir)
        assert result["needs_arch"] is False
        assert "Simple" in result["reason"]
        assert result["language"] == "python"

    def test_detect_architecture_complexity_layered(self, project_dir):
        """Layered project needs architecture checking."""
        from vibesrails.smart_setup.detection import detect_architecture_complexity

        # Create layered structure
        (project_dir / "domain").mkdir()
        (project_dir / "domain" / "__init__.py").write_text("")
        (project_dir / "api").mkdir()
        (project_dir / "api" / "__init__.py").write_text("")
        (project_dir / "infrastructure").mkdir()
        (project_dir / "infrastructure" / "__init__.py").write_text("")

        result = detect_architecture_complexity(project_dir)
        assert result["needs_arch"] is True
        assert "layers" in result["reason"].lower() or "layer" in result["reason"].lower()
        assert len(result["layers"]) >= 2

    def test_detect_architecture_complexity_nested_layers(self, project_dir):
        """Detect layers in nested directories."""
        from vibesrails.smart_setup.detection import detect_architecture_complexity

        # Create backend/domain, backend/api structure
        backend = project_dir / "backend"
        backend.mkdir()
        (backend / "domain").mkdir()
        (backend / "domain" / "__init__.py").write_text("")
        (backend / "api").mkdir()
        (backend / "api" / "__init__.py").write_text("")

        result = detect_architecture_complexity(project_dir)
        assert "backend/domain" in result["directories"] or "domain" in str(result["layers"])

    def test_detect_architecture_complexity_excludes_tests(self, project_dir):
        """Test directories are excluded."""
        from vibesrails.smart_setup.detection import detect_architecture_complexity

        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "__init__.py").write_text("")
        (project_dir / "main.py").write_text("")

        result = detect_architecture_complexity(project_dir)
        assert "tests" not in result["directories"]

    def test_check_architecture_tool_not_installed(self):
        """Architecture tool check returns False when not installed."""
        from vibesrails.smart_setup.detection import check_architecture_tool_installed

        with mock.patch('shutil.which', return_value=None):
            result = check_architecture_tool_installed("python")
            assert result is False

    def test_check_architecture_tool_installed(self):
        """Architecture tool check returns True when installed."""
        from vibesrails.smart_setup.detection import check_architecture_tool_installed

        with mock.patch('shutil.which', return_value="/usr/local/bin/lint-imports"):
            result = check_architecture_tool_installed("python")
            assert result is True

    def test_check_architecture_tool_unknown_language(self):
        """Unknown language returns False."""
        from vibesrails.smart_setup.detection import check_architecture_tool_installed

        result = check_architecture_tool_installed("rust")
        assert result is False
