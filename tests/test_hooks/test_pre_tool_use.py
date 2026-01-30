"""Tests for PreToolUse hook — runs as subprocess like ptuh.py tests."""

import json
import subprocess
import sys

HOOK_CMD = [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"]


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        HOOK_CMD,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        cwd="~/Dev/vibesrails",
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


def test_ignores_non_python():
    """Non-Python files exit 0 even with secrets."""
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
        cwd="~/Dev/vibesrails",
    )
    assert result.returncode == 0
