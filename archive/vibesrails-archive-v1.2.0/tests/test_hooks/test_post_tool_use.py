"""Tests for PostToolUse hook -- runs as subprocess."""

import json
import subprocess
import sys

HOOK_CMD = [sys.executable, "-m", "vibesrails.hooks.post_tool_use"]


def _run_hook(payload: dict, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        HOOK_CMD,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=cwd or "~/Dev/vibesrails",
    )


def test_passes_clean_file(tmp_path):
    """Clean Python file exits 0 with green indicator."""
    f = tmp_path / "clean.py"
    f.write_text("def hello() -> str:\n    return 'world'\n")
    result = _run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
    assert "scanned clean" in result.stdout


def test_warns_on_issues(tmp_path):
    """File with secrets exits 0 but prints warning."""
    f = tmp_path / "bad.py"
    f.write_text('API_KEY = "sk-abc123456789abcdef"\n')
    result = _run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
    assert "issue" in result.stdout.lower() or "VibesRails" in result.stdout


def test_ignores_non_write():
    """Bash tool exits 0."""
    result = _run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
    assert result.returncode == 0
    assert result.stdout == ""


def test_ignores_missing_file():
    """Nonexistent file exits 0."""
    result = _run_hook({
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/does_not_exist_12345.py"},
    })
    assert result.returncode == 0
    assert result.stdout == ""
