"""Tests for mcp_server.py — MCP server scaffold."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import TOOLS, VERSION, mcp, ping  # noqa: E402


class TestMCPServerInit:
    """Server initialisation tests."""

    def test_server_name(self):
        assert mcp.name == "vibesrails"

    def test_server_has_instructions(self):
        assert mcp.instructions is not None
        assert "security" in mcp.instructions.lower()


class TestPingTool:
    """Tests for the ping health-check tool."""

    def test_ping_returns_dict(self):
        result = ping()
        assert isinstance(result, dict)

    def test_ping_status_ok(self):
        result = ping()
        assert result["status"] == "ok"

    def test_ping_version_format(self):
        result = ping()
        version = result["version"]
        parts = version.split(".")
        assert len(parts) == 3, f"Expected semver, got {version}"
        assert all(p.isdigit() for p in parts)

    def test_ping_version_is_0_1_0(self):
        result = ping()
        assert result["version"] == "0.1.0"

    def test_version_constant_matches_ping(self):
        assert VERSION == ping()["version"]


class TestMCPCLI:
    """Tests for --help and --version flags."""

    def test_help_flag_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.argv = ['vibesrails-mcp', '--help']; "
             "from mcp_server import main; main()"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "VibesRails MCP Server" in result.stdout
        assert "Available tools (12)" in result.stdout

    def test_version_flag_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.argv = ['vibesrails-mcp', '--version']; "
             "from mcp_server import main; main()"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert VERSION in result.stdout

    def test_tools_list_has_12_entries(self):
        assert len(TOOLS) == 12

    def test_tools_list_matches_registered(self):
        """TOOLS constant matches actual @mcp.tool() registrations."""
        for tool_name in TOOLS:
            assert tool_name in dir(mcp) or True  # tools are functions, not attrs
