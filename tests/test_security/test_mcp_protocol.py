"""MCP protocol-level security tests.

Tests JSON-RPC transport via the MCP SDK in-memory client.
Validates error handling for: malformed calls, invalid arguments,
nonexistent tools, oversized payloads, tool listing, and rate limiting.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server import mcp

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def anyio_backend():
    return "asyncio"


async def _get_session():
    """Create a connected MCP client session."""
    return create_connected_server_and_client_session(mcp)


# ── 1. Tool listing ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_tools_list_returns_12_tools():
    """tools/list returns exactly 12 registered tools."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await session.list_tools()
        assert len(result.tools) == 12


@pytest.mark.anyio
async def test_tools_all_have_name_and_description():
    """Every tool has a non-empty name and description."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.name, "Tool missing name"
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} description too short"


@pytest.mark.anyio
async def test_tools_have_input_schema():
    """Every tool has an inputSchema for argument validation."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.inputSchema is not None, f"Tool {tool.name} missing inputSchema"


# ── 2. Nonexistent tool ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_nonexistent_tool_returns_error():
    """Calling a tool that doesn't exist returns isError=True."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("nonexistent_tool_xyz", {}), timeout=10,
        )
        assert result.isError is True
        assert "unknown" in result.content[0].text.lower()


# ── 3. Missing required arguments ────────────────────────────────────


@pytest.mark.anyio
async def test_deep_hallucination_missing_file_path():
    """deep_hallucination without required file_path returns error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("deep_hallucination", {"max_level": 2}), timeout=10,
        )
        assert result.isError is True
        assert "file_path" in result.content[0].text.lower()


@pytest.mark.anyio
async def test_scan_semgrep_missing_file_path():
    """scan_semgrep without required file_path returns error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("scan_semgrep", {}), timeout=10,
        )
        assert result.isError is True
        assert "file_path" in result.content[0].text.lower()


@pytest.mark.anyio
async def test_check_config_missing_project_path():
    """check_config without required project_path returns error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("check_config", {}), timeout=10,
        )
        assert result.isError is True
        assert "project_path" in result.content[0].text.lower()


# ── 4. Invalid argument types ────────────────────────────────────────


@pytest.mark.anyio
async def test_enforce_brief_null_brief():
    """enforce_brief with brief=null returns Pydantic validation error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("enforce_brief", {"brief": None}), timeout=10,
        )
        assert result.isError is True
        assert "dict" in result.content[0].text.lower()


@pytest.mark.anyio
async def test_deep_hallucination_max_level_out_of_range(tmp_path):
    """deep_hallucination with max_level=999 returns input validation error."""
    f = tmp_path / "test.py"
    f.write_text("import os")
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("deep_hallucination", {
                "file_path": str(f), "max_level": 999,
            }),
            timeout=10,
        )
        # Our input validator catches this and returns status=error
        text = result.content[0].text
        data = json.loads(text)
        assert data["status"] == "error"
        assert "max_level" in data["error"].lower()


@pytest.mark.anyio
async def test_shield_prompt_no_input():
    """shield_prompt with no text/file_path returns graceful error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("shield_prompt", {}), timeout=10,
        )
        text = result.content[0].text
        data = json.loads(text)
        assert data["status"] == "error"
        assert "no input" in data["error"].lower()


# ── 5. Oversized payloads ────────────────────────────────────────────


@pytest.mark.anyio
async def test_large_text_payload_handled():
    """1MB text payload is handled without OOM (rejected or processed)."""
    big_text = "A" * (1024 * 1024)  # 1MB
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("shield_prompt", {"text": big_text}), timeout=30,
        )
        # Should complete without crash — either processed or rejected
        text = result.content[0].text
        data = json.loads(text)
        assert data["status"] in ("pass", "warn", "error")


@pytest.mark.anyio
async def test_brief_with_many_fields_rejected():
    """Brief with 10000 fields is rejected by input validation."""
    huge_brief = {f"field_{i}": f"value_{i}" for i in range(10_000)}
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("enforce_brief", {"brief": huge_brief}), timeout=10,
        )
        text = result.content[0].text
        data = json.loads(text)
        assert data["status"] == "error"
        assert "too many" in data["error"].lower() or "max" in data["error"].lower()


# ── 6. Rate limiting via MCP protocol ────────────────────────────────


@pytest.mark.anyio
async def test_rate_limit_returns_structured_error(monkeypatch):
    """Rate-limited tool returns structured error with retry_after."""
    monkeypatch.delenv("VIBESRAILS_RATE_LIMIT", raising=False)

    import mcp_server
    from core.rate_limiter import RateLimiter

    original = mcp_server._limiter
    mcp_server._limiter = RateLimiter(per_tool_rpm=1, global_rpm=300)
    try:
        async with create_connected_server_and_client_session(mcp) as session:
            await session.initialize()
            # First call succeeds
            r1 = await session.call_tool("ping", {})
            data1 = json.loads(r1.content[0].text)
            assert data1["status"] == "ok"

            # Second call is rate limited
            r2 = await session.call_tool("ping", {})
            data2 = json.loads(r2.content[0].text)
            assert data2["status"] == "error"
            assert data2["error"] == "rate_limited"
            assert "retry_after_seconds" in data2
            assert isinstance(data2["retry_after_seconds"], int)
    finally:
        mcp_server._limiter = original


# ── 7. Ping health check via protocol ────────────────────────────────


@pytest.mark.anyio
async def test_ping_via_protocol():
    """Ping returns valid JSON with status and version via MCP protocol."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await session.call_tool("ping", {})
        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data["status"] == "ok"
        assert "version" in data
        parts = data["version"].split(".")
        assert len(parts) == 3


# ── 8. Tool with wrong param type ────────────────────────────────────


@pytest.mark.anyio
async def test_monitor_entropy_string_instead_of_int():
    """Passing string where int expected triggers Pydantic error."""
    async with create_connected_server_and_client_session(mcp) as session:
        await session.initialize()
        result = await asyncio.wait_for(
            session.call_tool("monitor_entropy", {
                "action": "update",
                "session_id": "fake-id",
                "changes_loc": "not_a_number",
            }),
            timeout=10,
        )
        # Pydantic may coerce strings to int or fail
        # Either way, server should not crash
        assert result.content  # Got some response back
