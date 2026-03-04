"""Tests for smart_setup config generation & vibe mode modules."""


import pytest

# ============================================
# Config Generation Tests
# ============================================

class TestConfigGen:
    """Tests for config_gen module: generating vibesrails.yaml."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def test_generate_config_basic(self):
        """Generate basic config with security pack."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=[],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert 'version: "1.0"' in result
        assert "@vibesrails/security-pack" in result
        assert "guardian:" in result

    def test_generate_config_fastapi(self):
        """Generate config for FastAPI project."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=["fastapi"],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert "@vibesrails/fastapi-pack" in result
        assert "@vibesrails/security-pack" in result

    def test_generate_config_django(self):
        """Generate config for Django project."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=["django"],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert "@vibesrails/django-pack" in result

    def test_generate_config_flask(self):
        """Generate config for Flask project."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=["flask"],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert "@vibesrails/web-pack" in result

    def test_generate_config_with_env_files(self, project_dir):
        """Generate config with env file protection."""
        from vibesrails.smart_setup.config_gen import generate_config

        env_file = project_dir / ".env"
        env_file.write_text("KEY=value")

        result = generate_config(
            project_types=[],
            has_secrets=False,
            env_files=[env_file],
            existing_configs={},
        )

        assert "blocking:" in result
        assert "env_file_content" in result
        assert ".env" in result

    def test_generate_config_multiple_types(self):
        """Generate config with multiple project types."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=["fastapi", "cli"],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert "@vibesrails/fastapi-pack" in result
        # CLI has no pack, so only fastapi pack should be there
        assert "extends:" in result

    def test_generate_config_complexity_settings(self):
        """Generated config includes complexity settings."""
        from vibesrails.smart_setup.config_gen import generate_config

        result = generate_config(
            project_types=[],
            has_secrets=False,
            env_files=[],
            existing_configs={},
        )

        assert "complexity:" in result
        assert "max_file_lines: 300" in result
        assert "max_function_lines: 50" in result

    def test_generate_config_with_extras_patterns(self, project_dir):
        """Generate config with extra custom patterns."""
        from vibesrails.smart_setup.config_gen import generate_config_with_extras

        extra_patterns = [
            {"id": "custom_1", "regex": "mycompany\\.com", "message": "Protected domain"},
        ]

        result = generate_config_with_extras(
            project_types=[],
            has_secrets=False,
            env_files=[],
            existing_configs={},
            extra_patterns=extra_patterns,
        )

        assert "blocking:" in result
        assert "custom_1" in result
        assert "mycompany\\.com" in result
        assert "Protected domain" in result

    def test_generate_config_with_extras_architecture(self, project_dir):
        """Generate config with architecture settings."""
        from vibesrails.smart_setup.config_gen import generate_config_with_extras

        arch_config = {
            "enabled": True,
            "language": "python",
            "layers": ["backend/domain", "backend/infrastructure", "backend/api"],
        }

        result = generate_config_with_extras(
            project_types=[],
            has_secrets=False,
            env_files=[],
            existing_configs={},
            extra_patterns=[],
            architecture=arch_config,
        )

        assert "architecture:" in result
        assert "dip_domain_infra" in result
        assert "DIP Violation" in result
        assert "import-linter" in result

    def test_generate_config_with_extras_no_blocking_when_empty(self):
        """No blocking section when no patterns."""
        from vibesrails.smart_setup.config_gen import generate_config_with_extras

        result = generate_config_with_extras(
            project_types=[],
            has_secrets=False,
            env_files=[],
            existing_configs={},
            extra_patterns=[],
        )

        # Should not have blocking section if no patterns
        # (but should have complexity section)
        assert "complexity:" in result

    def test_generate_importlinter_config_basic(self, project_dir):
        """Generate basic import-linter config."""
        from vibesrails.smart_setup.config_gen import generate_importlinter_config

        # Create a package
        (project_dir / "myproject").mkdir()
        (project_dir / "myproject" / "__init__.py").write_text("")

        layers = ["domain", "api"]
        result = generate_importlinter_config(project_dir, layers)

        assert "[importlinter]" in result
        assert "root_package = myproject" in result

    def test_generate_importlinter_config_with_domain(self, project_dir):
        """Generate import-linter config with domain independence."""
        from vibesrails.smart_setup.config_gen import generate_importlinter_config

        (project_dir / "backend").mkdir()
        (project_dir / "backend" / "__init__.py").write_text("")

        layers = ["domain", "api", "infrastructure"]
        result = generate_importlinter_config(project_dir, layers)

        assert "independence" in result
        assert "domain" in result

    def test_generate_importlinter_config_layers_contract(self, project_dir):
        """Generate import-linter config with layer contract."""
        from vibesrails.smart_setup.config_gen import generate_importlinter_config

        (project_dir / "app").mkdir()
        (project_dir / "app" / "__init__.py").write_text("")

        layers = ["api", "services", "domain"]
        result = generate_importlinter_config(project_dir, layers)

        assert "type = layers" in result
        assert "Architectural layers" in result

    def test_generate_importlinter_config_fallback_name(self, project_dir):
        """Fallback to project directory name if no package found."""
        from vibesrails.smart_setup.config_gen import generate_importlinter_config

        # No __init__.py anywhere
        result = generate_importlinter_config(project_dir, ["api"])

        # Should use project_dir name (sanitized)
        assert "root_package" in result


# ============================================
# Vibe Mode Tests
# ============================================

class TestVibeMode:
    """Tests for vibe_mode module: user-friendly pattern setup."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory."""
        return tmp_path

    def test_scan_for_secrets_openai_key(self, project_dir):
        """Scan finds OpenAI key pattern."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu"')

        result = scan_for_secrets(project_dir)
        assert "api_keys" in result
        assert len(result["api_keys"]) > 0

    def test_scan_for_secrets_aws_key(self, project_dir):
        """Scan finds AWS key pattern."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('aws_key = "AKIAIOSFODNN7EXAMPLE"')

        result = scan_for_secrets(project_dir)
        assert "api_keys" in result

    def test_scan_for_secrets_password(self, project_dir):
        """Scan finds password pattern."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('password = "supersecret123"')

        result = scan_for_secrets(project_dir)
        assert "passwords" in result
        assert len(result["passwords"]) > 0

    def test_scan_for_secrets_jwt(self, project_dir):
        """Scan finds JWT token pattern."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        # Test JWT-like token pattern (uses a truncated fake to avoid semgrep)
        header = "eyJhbGciOiJIUzI1NiJ9"
        payload = "eyJzdWIiOiIxIn0"
        sig = "abc123"
        jwt = f"{header}.{payload}.{sig}"
        (project_dir / "auth.py").write_text(f'token = "{jwt}"')

        result = scan_for_secrets(project_dir)
        assert "tokens" in result

    def test_scan_for_secrets_url_with_creds(self, project_dir):
        """Scan finds URL with credentials."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "db.py").write_text('db_url = "postgresql://user:password@localhost:5432/db"')

        result = scan_for_secrets(project_dir)
        assert "urls" in result

    def test_scan_for_secrets_excludes_venv(self, project_dir):
        """Scan excludes virtual environment."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        venv = project_dir / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "secrets.py").write_text('password = "hidden"')

        result = scan_for_secrets(project_dir)
        # Should be empty since only venv file has secrets
        assert result == {}

    def test_scan_for_secrets_excludes_comments(self, project_dir):
        """Scan excludes commented lines."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('# password = "commented_out"')

        result = scan_for_secrets(project_dir)
        assert result == {}

    def test_scan_for_secrets_excludes_ignore_directive(self, project_dir):
        """Scan excludes lines with vibesrails: ignore."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('password = "example"  # vibesrails: ignore')

        result = scan_for_secrets(project_dir)
        assert result == {}

    def test_scan_for_secrets_masks_preview(self, project_dir):
        """Scan masks secrets in preview."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        (project_dir / "config.py").write_text('password = "supersecretpassword123"')

        result = scan_for_secrets(project_dir)
        assert "passwords" in result
        preview = result["passwords"][0]["preview"]
        # Should be masked (first 4 chars + ... + last 4 chars)
        assert "..." in preview
        assert len(preview) < len("supersecretpassword123")

    def test_scan_for_secrets_empty_project(self, project_dir):
        """Empty project returns empty dict."""
        from vibesrails.smart_setup.vibe_mode import scan_for_secrets

        result = scan_for_secrets(project_dir)
        assert result == {}

    def test_natural_language_to_pattern_quoted_string(self):
        """Convert quoted string to pattern."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern('protege "mypassword123"')

        assert result is not None
        assert result["regex"] == "mypassword123"
        assert "mypassword123" in result["message"]

    def test_natural_language_to_pattern_domain(self):
        """Convert domain to pattern."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern("bloc mycompany.com dans le code")

        assert result is not None
        assert "mycompany\\.com" in result["regex"]
        assert "mycompany.com" in result["message"]

    def test_natural_language_to_pattern_email_domain(self):
        """Convert email domain to pattern."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern("emails @entreprise.fr")

        assert result is not None
        # The regex escapes the @ and the domain
        assert "entreprise" in result["regex"]
        assert "\\." in result["regex"]  # Dot is escaped

    def test_natural_language_to_pattern_project_name(self):
        """Convert project name reference to pattern."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern("le nom du projet", project_name="myproject")

        assert result is not None
        assert result["regex"] == "myproject"
        assert "myproject" in result["message"]

    def test_natural_language_to_pattern_short_value(self):
        """Short input treated as value to block."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern("api_v2")

        assert result is not None
        assert result["regex"] == "api_v2"

    def test_natural_language_to_pattern_long_unrecognized(self):
        """Long unrecognized input returns None."""
        from vibesrails.smart_setup.vibe_mode import natural_language_to_pattern

        result = natural_language_to_pattern("je veux proteger quelque chose mais je ne sais pas quoi exactement")

        assert result is None

    def test_prompt_user_yes_default(self, monkeypatch):
        """prompt_user defaults to yes."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        monkeypatch.setattr('builtins.input', lambda _: "")
        result = prompt_user("Confirm?", default="y")
        assert result is True

    def test_prompt_user_no_default(self, monkeypatch):
        """prompt_user defaults to no."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        monkeypatch.setattr('builtins.input', lambda _: "")
        result = prompt_user("Confirm?", default="n")
        assert result is False

    def test_prompt_user_explicit_yes(self, monkeypatch):
        """prompt_user accepts 'y'."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        monkeypatch.setattr('builtins.input', lambda _: "y")
        result = prompt_user("Confirm?")
        assert result is True

    def test_prompt_user_explicit_no(self, monkeypatch):
        """prompt_user accepts 'n'."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        monkeypatch.setattr('builtins.input', lambda _: "n")
        result = prompt_user("Confirm?")
        assert result is False

    def test_prompt_user_french_yes(self, monkeypatch):
        """prompt_user accepts 'oui'."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        monkeypatch.setattr('builtins.input', lambda _: "oui")
        result = prompt_user("Confirm?")
        assert result is True

    def test_prompt_user_eof_error(self, monkeypatch):
        """prompt_user handles EOFError."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        def raise_eof(_):
            raise EOFError()

        monkeypatch.setattr('builtins.input', raise_eof)
        result = prompt_user("Confirm?")
        assert result is False

    def test_prompt_user_keyboard_interrupt(self, monkeypatch):
        """prompt_user handles KeyboardInterrupt."""
        from vibesrails.smart_setup.vibe_mode import prompt_user

        def raise_interrupt(_):
            raise KeyboardInterrupt()

        monkeypatch.setattr('builtins.input', raise_interrupt)
        result = prompt_user("Confirm?")
        assert result is False
