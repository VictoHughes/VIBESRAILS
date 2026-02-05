"""Tests for EnvSafetyGuard — real files, real filesystem, no mocking."""

import subprocess
import textwrap
from pathlib import Path

import pytest

from vibesrails.guards_v2.env_safety import EnvSafetyGuard


@pytest.fixture
def guard() -> EnvSafetyGuard:
    return EnvSafetyGuard()


def _init_git(tmp_path: Path) -> None:
    """Initialize a real git repo so _check_tracked_secret_files works."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True,
    )


# ── .gitignore checks ────────────────────────────────────────


def test_gitignore_missing_blocks(guard: EnvSafetyGuard, tmp_path: Path):
    """Block if .gitignore does not exist."""
    issues = guard._check_gitignore(tmp_path)
    assert len(issues) == 1
    assert "missing" in issues[0].message
    assert issues[0].severity == "block"


def test_gitignore_without_env_blocks(guard: EnvSafetyGuard, tmp_path: Path):
    """Block if .env not listed in .gitignore."""
    (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")
    issues = guard._check_gitignore(tmp_path)
    assert any(i.severity == "block" and ".env" in i.message for i in issues)


def test_gitignore_with_env_no_block(guard: EnvSafetyGuard, tmp_path: Path):
    """No block for .env if .gitignore contains .env."""
    (tmp_path / ".gitignore").write_text(".env\n*.pem\n*.key\n*.p12\n")
    issues = guard._check_gitignore(tmp_path)
    assert not any(i.severity == "block" for i in issues)


def test_gitignore_missing_pem_pattern(guard: EnvSafetyGuard, tmp_path: Path):
    """Warn if *.pem not in .gitignore."""
    (tmp_path / ".gitignore").write_text(".env\n")
    issues = guard._check_gitignore(tmp_path)
    assert any("*.pem" in i.message for i in issues)


def test_gitignore_missing_key_pattern(guard: EnvSafetyGuard, tmp_path: Path):
    """Warn if *.key not in .gitignore."""
    (tmp_path / ".gitignore").write_text(".env\n")
    issues = guard._check_gitignore(tmp_path)
    assert any("*.key" in i.message for i in issues)


def test_gitignore_missing_p12_pattern(guard: EnvSafetyGuard, tmp_path: Path):
    """Warn if *.p12 not in .gitignore."""
    (tmp_path / ".gitignore").write_text(".env\n")
    issues = guard._check_gitignore(tmp_path)
    assert any("*.p12" in i.message for i in issues)


def test_gitignore_complete_no_warnings(guard: EnvSafetyGuard, tmp_path: Path):
    """No issues if .gitignore has .env + all secret patterns."""
    (tmp_path / ".gitignore").write_text(".env\n*.pem\n*.key\n*.p12\n")
    issues = guard._check_gitignore(tmp_path)
    assert issues == []


# ── .env.example check ───────────────────────────────────────


def test_env_example_missing_warns(guard: EnvSafetyGuard, tmp_path: Path):
    """Warn if .env.example does not exist."""
    issues = guard._check_env_example(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "warn"


def test_env_example_present_ok(guard: EnvSafetyGuard, tmp_path: Path):
    """No issue if .env.example exists."""
    (tmp_path / ".env.example").write_text("DB_URL=\nSECRET_KEY=\n")
    issues = guard._check_env_example(tmp_path)
    assert issues == []


# ── scan_file: os.environ ────────────────────────────────────


def test_unsafe_environ_bracket_detected(guard: EnvSafetyGuard, tmp_path: Path):
    """Warn on os.environ['KEY'] in a real file."""
    f = tmp_path / "app.py"
    f.write_text('import os\ndb = os.environ["DATABASE_URL"]\n')
    issues = guard.scan_file(f, f.read_text())
    assert len(issues) == 1
    assert "os.environ.get" in issues[0].message
    assert issues[0].severity == "warn"


def test_safe_environ_get_no_issue(guard: EnvSafetyGuard, tmp_path: Path):
    """No issue for os.environ.get() in a real file."""
    f = tmp_path / "app.py"
    f.write_text('import os\ndb = os.environ.get("DATABASE_URL", "")\n')
    issues = guard.scan_file(f, f.read_text())
    assert issues == []


def test_multiple_unsafe_environ(guard: EnvSafetyGuard, tmp_path: Path):
    """Detect multiple unsafe environ usages."""
    f = tmp_path / "config.py"
    f.write_text(textwrap.dedent("""\
        import os
        db = os.environ["DB_URL"]
        secret = os.environ["SECRET"]
        safe = os.environ.get("SAFE", "default")
    """))
    issues = guard.scan_file(f, f.read_text())
    environ_issues = [i for i in issues if "os.environ.get" in i.message]
    assert len(environ_issues) == 2


# ── scan_file: hardcoded secrets ─────────────────────────────


def test_aws_key_detected(guard: EnvSafetyGuard, tmp_path: Path):
    """Block on real AWS access key pattern in a real file."""
    f = tmp_path / "config.py"
    f.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    issues = guard.scan_file(f, f.read_text())
    assert any(i.severity == "block" for i in issues)


def test_hardcoded_password_detected(guard: EnvSafetyGuard, tmp_path: Path):
    """Block on password = '...' pattern."""
    f = tmp_path / "db.py"
    f.write_text("password = 'super_secret_123'\n")
    issues = guard.scan_file(f, f.read_text())
    assert any(i.severity == "block" and "password" in i.message.lower() for i in issues)


def test_token_sk_detected(guard: EnvSafetyGuard, tmp_path: Path):
    """Block on token = 'sk-...' pattern."""
    f = tmp_path / "llm.py"
    f.write_text('api_key = "sk-abc123def456ghi789"\n')
    issues = guard.scan_file(f, f.read_text())
    assert any(i.severity == "block" for i in issues)


def test_ghp_token_detected(guard: EnvSafetyGuard, tmp_path: Path):
    """Block on GitHub personal token pattern."""
    f = tmp_path / "deploy.py"
    f.write_text('token = "ghp_1234567890abcdef"\n')
    issues = guard.scan_file(f, f.read_text())
    assert any(i.severity == "block" for i in issues)


def test_clean_code_no_secrets(guard: EnvSafetyGuard, tmp_path: Path):
    """Clean code should not trigger secret detection."""
    f = tmp_path / "clean.py"
    f.write_text(textwrap.dedent("""\
        import os
        db_url = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
        debug = True
        name = "my-app"
    """))
    issues = guard.scan_file(f, f.read_text())
    assert issues == []


# ── Tracked secret files (real git repo) ─────────────────────


def test_tracked_pem_detected_real_git(guard: EnvSafetyGuard, tmp_path: Path):
    """Block if .pem file is tracked in a real git repo."""
    _init_git(tmp_path)
    pem_file = tmp_path / "server.pem"
    pem_file.write_text("-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n")
    subprocess.run(["git", "add", "server.pem"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add cert"],
        cwd=tmp_path, capture_output=True,
    )
    issues = guard._check_tracked_secret_files(tmp_path)
    assert any("server.pem" in i.message for i in issues)
    assert all(i.severity == "block" for i in issues)


def test_tracked_key_detected_real_git(guard: EnvSafetyGuard, tmp_path: Path):
    """Block if .key file is tracked in a real git repo."""
    _init_git(tmp_path)
    key_file = tmp_path / "private.key"
    key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nfake\n")
    subprocess.run(["git", "add", "private.key"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add key"],
        cwd=tmp_path, capture_output=True,
    )
    issues = guard._check_tracked_secret_files(tmp_path)
    assert any("private.key" in i.message for i in issues)


def test_no_tracked_secrets_clean_repo(guard: EnvSafetyGuard, tmp_path: Path):
    """No issues when repo has no secret files tracked."""
    _init_git(tmp_path)
    (tmp_path / "app.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, capture_output=True,
    )
    issues = guard._check_tracked_secret_files(tmp_path)
    assert issues == []


# ── Full scan integration (real filesystem + real git) ────────


def test_full_scan_real_project(guard: EnvSafetyGuard, tmp_path: Path):
    """Full scan on a real project structure catches multiple issue types."""
    _init_git(tmp_path)

    # Missing .env in .gitignore
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    # No .env.example

    # Source file with unsafe environ
    src = tmp_path / "app.py"
    src.write_text('key = os.environ["SECRET"]\n')
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, capture_output=True,
    )

    issues = guard.scan(tmp_path)

    # Should find: .env not in gitignore, missing .env.example,
    # missing secret patterns, unsafe environ
    assert len(issues) >= 3
    severities = {i.severity for i in issues}
    assert "block" in severities
    assert "warn" in severities


# ── Secret leak in __repr__ detection ─────────────────────────


def test_settings_class_without_repr_blocks(guard: EnvSafetyGuard, tmp_path: Path):
    """Block Settings class with secret fields but no __repr__."""
    f = tmp_path / "config.py"
    f.write_text(textwrap.dedent("""\
        class Settings:
            openai_api_key: str = ""
            database_url: str = ""
            debug: bool = False
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any(
        "__repr__" in i.message and "Settings" in i.message
        for i in issues
    )
    # Settings class should block
    assert any(i.severity == "block" for i in issues)


def test_config_class_without_repr_blocks(guard: EnvSafetyGuard, tmp_path: Path):
    """Block Config class with secret fields but no __repr__."""
    f = tmp_path / "app_config.py"
    f.write_text(textwrap.dedent("""\
        class AppConfig:
            api_key: str
            secret_key: str
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("__repr__" in i.message for i in issues)


def test_class_with_repr_no_issue(guard: EnvSafetyGuard, tmp_path: Path):
    """No issue if Settings class has __repr__."""
    f = tmp_path / "config.py"
    f.write_text(textwrap.dedent("""\
        class Settings:
            openai_api_key: str = ""

            def __repr__(self):
                return "Settings(openai_api_key='***')"
    """))
    issues = guard.scan_file(f, f.read_text())
    assert not any("__repr__" in i.message for i in issues)


def test_class_with_str_no_issue(guard: EnvSafetyGuard, tmp_path: Path):
    """No issue if class has __str__ (also prevents leak)."""
    f = tmp_path / "config.py"
    f.write_text(textwrap.dedent("""\
        class Settings:
            password: str = ""

            def __str__(self):
                return "Settings(password='***')"
    """))
    issues = guard.scan_file(f, f.read_text())
    assert not any("__repr__" in i.message for i in issues)


def test_class_with_init_secret_fields(guard: EnvSafetyGuard, tmp_path: Path):
    """Detect secret fields set in __init__ (self.api_key = ...)."""
    f = tmp_path / "service.py"
    f.write_text(textwrap.dedent("""\
        class ServiceConfig:
            def __init__(self, api_key: str):
                self.api_key = api_key
                self.secret_token = "default"
    """))
    issues = guard.scan_file(f, f.read_text())
    assert any("__repr__" in i.message for i in issues)


def test_non_config_class_warns_not_blocks(guard: EnvSafetyGuard, tmp_path: Path):
    """Non-settings class with secrets warns instead of blocks."""
    f = tmp_path / "handler.py"
    f.write_text(textwrap.dedent("""\
        class APIHandler:
            api_key: str = ""
    """))
    issues = guard.scan_file(f, f.read_text())
    repr_issues = [i for i in issues if "__repr__" in i.message]
    assert len(repr_issues) == 1
    assert repr_issues[0].severity == "warn"


def test_class_without_secrets_no_issue(guard: EnvSafetyGuard, tmp_path: Path):
    """Class without secret fields should not trigger."""
    f = tmp_path / "model.py"
    f.write_text(textwrap.dedent("""\
        class User:
            name: str
            email: str
            age: int
    """))
    issues = guard.scan_file(f, f.read_text())
    assert not any("__repr__" in i.message for i in issues)
