"""Tests for mcp_server.py — MCP server scaffold."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import VERSION, mcp, ping  # noqa: E402


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
