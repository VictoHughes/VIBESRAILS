"""Tests for PreToolUse hook — runs as subprocess like ptuh.py tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_CMD = [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"]
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(autouse=True)
def _reset_throttle():
    """Reset throttle before each test to prevent cross-test blocking."""
    from vibesrails.hooks.throttle import reset_state
    state_dir = Path(PROJECT_ROOT) / ".vibesrails"
    state_dir.mkdir(exist_ok=True)
    reset_state(state_dir)


def _run_hook(payload: dict, cwd: str = PROJECT_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        HOOK_CMD,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=cwd,
    )


def test_allows_safe_write():
    """Safe Python code exits 0."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "app.py",
            "content": "import os\n\ndef hello():\n    return 'world'\n",
        },
    })
    assert result.returncode == 0


def test_blocks_hardcoded_secret():
    """Hardcoded API key exits 1."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "config.py",
            "content": 'API_KEY = "sk-abc123456789abcdef"\n',
        },
    })
    assert result.returncode == 1
    assert "BLOCKED" in result.stdout


def test_blocks_sql_injection():
    """SQL injection via f-string exits 1."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "db.py",
            "content": 'query = f"SELECT * FROM users WHERE id = {user_id}"\n',
        },
    })
    assert result.returncode == 1
    assert "SQL injection" in result.stdout


def test_ignores_unscannable_files():
    """Non-scannable files (e.g. .md) exit 0 even with secrets."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "README.md",
            "content": 'API_KEY = "sk-abc123456789abcdef"\n',
        },
    })
    assert result.returncode == 0


def test_ignores_non_write_tools():
    """Non-Write/Edit tools exit 0."""
    result = _run_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo hello",
        },
    })
    assert result.returncode == 0


def test_handles_edit_tool():
    """Edit tool with secret exits 1."""
    result = _run_hook({
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "settings.py",
            "new_string": 'password = "hunter2hunter2"\n',
        },
    })
    assert result.returncode == 1
    assert "BLOCKED" in result.stdout


def test_handles_empty_content():
    """Empty content exits 0."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "empty.py",
            "content": "",
        },
    })
    assert result.returncode == 0


def test_skips_comment_lines():
    """Comment lines with secrets are ignored."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "app.py",
            "content": '# API_KEY = "sk-abc123456789abcdef"\n',
        },
    })
    assert result.returncode == 0


def test_skips_vibesrails_ignore():
    """Lines with vibesrails: ignore are skipped."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "app.py",
            "content": 'API_KEY = "sk-abc123456789abcdef"  # vibesrails: ignore\n',
        },
    })
    assert result.returncode == 0


def test_blocks_sql_injection_format():
    """SQL injection via .format() exits 1."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "db.py",
            "content": 'query = "SELECT * FROM users WHERE id = {}".format(user_id)\n',
        },
    })
    assert result.returncode == 1
    assert "SQL injection" in result.stdout


def test_blocks_sk_proj_key():
    """OpenAI sk-proj- keys are blocked."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "config.py",
            "content": 'key = "sk-proj-abcdefghij1234567890"\n',
        },
    })
    assert result.returncode == 1


def test_bash_blocks_leaked_api_key():
    """Bash command with API key is blocked."""
    result = _run_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": 'curl -H "Authorization: Bearer sk-proj-abcdefghij1234567890"',
        },
    })
    assert result.returncode == 1
    assert "BLOCKED" in result.stdout
    assert "sk-proj" not in result.stdout  # key should be redacted


def test_bash_blocks_leaked_password():
    """Bash command with password is blocked."""
    result = _run_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": "mysql -u root password=SuperSecret123",
        },
    })
    assert result.returncode == 1


def test_bash_allows_safe_command():
    """Safe bash command exits 0."""
    result = _run_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo hello && git status",
        },
    })
    assert result.returncode == 0


def test_bash_blocks_inline_ghp_token():
    """GitHub token in bash is blocked."""
    result = _run_hook({
        "tool_name": "Bash",
        "tool_input": {
            "command": "git clone https://ghp_abc1234567890abcdefghijklmnopqr@github.com/repo.git",
        },
    })
    assert result.returncode == 1


def test_handles_malformed_json():
    """Malformed input exits 0 gracefully."""
    result = subprocess.run(
        HOOK_CMD,
        input="not json at all",
        capture_output=True,
        text=True,
        timeout=10,
        cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0


# --- FIX 2: Secret detection beyond .py ---


class TestSecretDetectionMultiFormat:
    """Secrets in non-.py files must now be blocked."""

    def test_blocks_secret_in_env(self):
        """Secret in .env file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env",
                "content": 'API_KEY = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout

    def test_blocks_secret_in_env_local(self):
        """Secret in .env.local file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env.local",
                "content": 'SECRET = "AKIAFAKE1234567890AB1234"\n',
            },
        })
        assert result.returncode == 1

    def test_blocks_secret_in_env_production(self):
        """Secret in .env.production file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env.production",
                "content": 'token = "ghp_abcdefghij1234567890klmnopqrst"\n',
            },
        })
        assert result.returncode == 1

    def test_blocks_secret_in_yaml(self):
        """Secret in .yaml file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "config.yaml",
                "content": 'api_key = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout

    def test_blocks_secret_in_yml(self):
        """Secret in .yml file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "docker-compose.yml",
                "content": 'password = "SuperSecretPassword123"\n',
            },
        })
        assert result.returncode == 1

    def test_blocks_secret_in_json(self):
        """Secret in .json file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "config.json",
                "content": 'api_key = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout

    def test_blocks_secret_in_sh(self):
        """Secret in .sh file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "deploy.sh",
                "content": 'api_key = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout

    def test_blocks_secret_in_toml(self):
        """Secret in .toml file is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "settings.toml",
                "content": 'password = "SuperSecretPassword123"\n',
            },
        })
        assert result.returncode == 1

    def test_ignores_binary_whl(self):
        """Binary .whl files are NOT scanned."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "dist/package-1.0.0-py3-none-any.whl",
                "content": 'api_key = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 0

    def test_ignores_binary_png(self):
        """Binary .png files are NOT scanned."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "logo.png",
                "content": 'api_key = "sk-abc123456789abcdef"\n',
            },
        })
        assert result.returncode == 0

    def test_no_code_patterns_in_yaml(self):
        """SQL injection patterns should NOT trigger in .yaml files."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "rules.yaml",
                "content": 'pattern: f"SELECT * FROM users WHERE id = {user_id}"\n',
            },
        })
        assert result.returncode == 0

    def test_safe_env_file_passes(self):
        """A .env file without secrets passes."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env",
                "content": "DEBUG=true\nLOG_LEVEL=info\nPORT=8080\n",
            },
        })
        assert result.returncode == 0


# --- Local path leak detection ---


class TestLocalPathLeak:
    """FIX 4: detect hardcoded local paths (/Users/*, /home/*, C:\\Users\\*)."""

    def test_blocks_users_path(self):
        """Writing /Users/john/secret is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "config.py",
                "content": 'DATA_DIR = "/Users/john/secret/data"\n',
            },
        })
        assert result.returncode == 1
        assert "Local path leak" in result.stdout

    def test_blocks_home_path(self):
        """Writing /home/dev/project is BLOCKED."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "settings.py",
                "content": 'PROJECT = "/home/dev/project/src"\n',
            },
        })
        assert result.returncode == 1
        assert "Local path leak" in result.stdout

    def test_allows_relative_path(self):
        """Relative path is NOT blocked."""
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "config.py",
                "content": 'DATA_DIR = "relative/path/ok"\n',
            },
        })
        assert result.returncode == 0


# --- File size guard ---


class TestFileSizeGuard:
    """File size guard blocks writes exceeding max_file_lines."""

    def test_write_200_lines_passes(self):
        """Write with 200 lines passes (under 300 limit)."""
        content = "\n".join(f"x = {i}" for i in range(200)) + "\n"
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "big_module.py",
                "content": content,
            },
        })
        assert result.returncode == 0

    def test_write_301_lines_blocked(self):
        """Write with 301 lines is BLOCKED."""
        content = "\n".join(f"x = {i}" for i in range(301)) + "\n"
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "big_module.py",
                "content": content,
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout
        assert "301 lines" in result.stdout

    def test_write_500_lines_blocked(self):
        """Write with 500 lines is BLOCKED."""
        content = "\n".join(f"x = {i}" for i in range(500)) + "\n"
        result = _run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "big_module.py",
                "content": content,
            },
        })
        assert result.returncode == 1
        assert "BLOCKED" in result.stdout
        assert "500 lines" in result.stdout

    def test_custom_max_file_lines_passes(self, tmp_path):
        """Custom max_file_lines: 500 allows 400-line files."""
        config = tmp_path / "vibesrails.yaml"
        config.write_text("guardian:\n  max_file_lines: 500\n")
        content = "\n".join(f"x = {i}" for i in range(400)) + "\n"
        result = _run_hook(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "big_module.py",
                    "content": content,
                },
            },
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
