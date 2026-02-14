"""Integration tests for the VibesRails MCP Server.

Verifies that all tools are registered, return consistent formats,
and can run together on the same file without crashing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import mcp_server  # noqa: E402
from mcp_tools_ext import ping as mcp_ping  # noqa: E402
from tools.check_session import check_session  # noqa: E402
from tools.monitor_entropy import monitor_entropy  # noqa: E402
from tools.scan_code import scan_code  # noqa: E402
from tools.scan_semgrep import scan_semgrep  # noqa: E402
from tools.scan_senior import scan_senior  # noqa: E402

# ── Fixtures ───────────────────────────────────────────────────────────

SAMPLE_CODE = """\
\"\"\"Sample module for integration testing.\"\"\"

import os
import logging

logger = logging.getLogger(__name__)


def greet(name: str) -> str:
    \"\"\"Greet someone.\"\"\"
    return f"Hello, {name}!"
"""


def _write_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


# ── Tool registration ─────────────────────────────────────────────────


class TestMCPToolRegistration:
    """Tests for MCP server tool registration."""

    def test_expected_tool_count(self):
        tools = asyncio.run(mcp_server.mcp.list_tools())
        assert len(tools) == 12, f"Expected 12 tools, got {len(tools)}: {[t.name for t in tools]}"

    def test_expected_tool_names(self):
        tools = asyncio.run(mcp_server.mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "ping", "scan_code", "scan_senior", "check_session",
            "scan_semgrep", "monitor_entropy", "check_config",
            "deep_hallucination", "check_drift", "enforce_brief",
            "shield_prompt", "get_learning",
        }
        assert names == expected, f"Tool names mismatch: {names} vs {expected}"

    def test_all_tools_have_descriptions(self):
        tools = asyncio.run(mcp_server.mcp.list_tools())
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"
            assert len(tool.description) > 10, f"Tool {tool.name} description too short"


# ── Consistent format ─────────────────────────────────────────────────


class TestConsistentFormat:
    """Tests that all scan tools return consistent format."""

    def test_scan_code_has_status(self, tmp_path):
        f = _write_file(tmp_path, SAMPLE_CODE)
        result = scan_code(file_path=str(f), guards=["dead_code"])
        assert "status" in result
        assert result["status"] in ("pass", "info", "warn", "block", "error")

    def test_scan_senior_has_status(self, tmp_path):
        f = _write_file(tmp_path, SAMPLE_CODE)
        result = scan_senior(file_path=str(f), guards=["error_handling"])
        assert "status" in result
        assert result["status"] in ("pass", "info", "warn", "block", "error")

    def test_scan_semgrep_has_status(self, tmp_path):
        f = _write_file(tmp_path, SAMPLE_CODE)
        result = scan_semgrep(file_path=str(f))
        assert "status" in result
        assert result["status"] in ("pass", "info", "warn", "block", "error")

    def test_check_session_has_pedagogy(self):
        result = check_session()
        assert "pedagogy" in result
        assert "why" in result["pedagogy"]

    def test_all_scan_tools_have_findings_list(self, tmp_path):
        f = _write_file(tmp_path, SAMPLE_CODE)
        for tool_fn, kwargs in [
            (scan_code, {"file_path": str(f), "guards": ["dead_code"]}),
            (scan_senior, {"file_path": str(f), "guards": ["error_handling"]}),
            (scan_semgrep, {"file_path": str(f)}),
        ]:
            result = tool_fn(**kwargs)
            assert "findings" in result, f"{tool_fn.__name__} missing 'findings'"
            assert isinstance(result["findings"], list), f"{tool_fn.__name__} findings not a list"


# ── Combined scan ─────────────────────────────────────────────────────


class TestCombinedScan:
    """Test all 3 scan tools on the same file without crashing."""

    def test_all_three_scans_on_same_file(self, tmp_path):
        f = _write_file(tmp_path, SAMPLE_CODE)
        fp = str(f)

        # All three scans should complete without exception
        r1 = scan_code(file_path=fp, guards=["dead_code"])
        r2 = scan_senior(file_path=fp, guards="all")
        r3 = scan_semgrep(file_path=fp)

        # All should return valid status
        for result, name in [(r1, "scan_code"), (r2, "scan_senior"), (r3, "scan_semgrep")]:
            assert result["status"] in ("pass", "info", "warn", "block", "error"), (
                f"{name} returned invalid status: {result['status']}"
            )

    def test_ping_returns_version(self):
        result = mcp_ping()
        assert result["status"] == "ok"
        assert result["version"] == mcp_server.VERSION

    def test_monitor_entropy_lifecycle(self, tmp_path):
        db = tmp_path / "integ.db"
        start = monitor_entropy(action="start", project_path=str(tmp_path), db_path=str(db))
        assert start["status"] == "ok"
        sid = start["session_id"]

        update = monitor_entropy(
            action="update", session_id=sid,
            files_modified=["a.py"], changes_loc=50,
            db_path=str(db),
        )
        assert update["status"] == "ok"
        assert "pedagogy" in update

        end = monitor_entropy(action="end", session_id=sid, db_path=str(db))
        assert end["status"] == "ok"
        assert "session_summary" in end
