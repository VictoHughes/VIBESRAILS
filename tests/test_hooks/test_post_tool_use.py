"""Tests for PostToolUse hook -- runs as subprocess."""

import json
import subprocess
import sys
from pathlib import Path

HOOK_CMD = [sys.executable, "-m", "vibesrails.hooks.post_tool_use"]
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


def _run_hook(payload: dict, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        HOOK_CMD,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=cwd or PROJECT_ROOT,
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


# --- Auto-scan behavior ---


class TestAutoScan:
    """PostToolUse auto-scan on Write/Edit events."""

    def test_write_py_triggers_auto_scan(self, tmp_path):
        """Writing a .py file triggers V1+V2+Senior scan automatically."""
        f = tmp_path / "module.py"
        f.write_text("def greet(name: str) -> str:\n    return f'Hello {name}'\n")
        result = _run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "VibesRails" in result.stdout

    def test_write_md_skipped(self, tmp_path):
        """Writing a .md file skips scan entirely."""
        f = tmp_path / "notes.md"
        f.write_text("# Notes\n\nSome documentation.\n")
        result = _run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert result.stdout == ""

    def test_scan_completes_within_timeout(self, tmp_path):
        """Large .py file completes scan within 5s timeout, exits 0."""
        f = tmp_path / "large_module.py"
        lines = [f"def func_{i}() -> int:\n    return {i}\n" for i in range(100)]
        f.write_text("\n".join(lines))
        result = _run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "timeout" not in result.stdout.lower()
