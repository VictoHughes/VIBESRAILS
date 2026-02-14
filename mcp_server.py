"""VibesRails MCP Server — security scanner for AI-assisted coding.

Entry point for the Model Context Protocol server.
Transport: stdio (default).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from core.logger import log_rate_limit, log_server_start
from core.rate_limiter import RateLimiter
from storage.migrations import migrate

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Rate limiter (in-memory, resets on restart)
# Disable with VIBESRAILS_RATE_LIMIT=0
# ---------------------------------------------------------------------------
_limiter = RateLimiter()


def _check_rate_limit(tool_name: str) -> dict | None:
    """Return rate limit error dict, or None if allowed."""
    if not _limiter.check(tool_name):
        retry = _limiter.retry_after(tool_name)
        log_rate_limit(tool_name, retry)
        return {
            "status": "error",
            "error": "rate_limited",
            "message": "Too many requests. Max 60 calls/minute per tool.",
            "retry_after_seconds": retry,
        }
    return None


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Run database migrations at startup."""
    migrate()
    log_server_start(VERSION, tools_count=12)
    yield


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="vibesrails",
    instructions=(
        "VibesRails MCP Server — security scanner for AI-assisted coding. "
        "Scans code for security issues, architecture drift, and AI hallucinations. "
        "Provides pedagogical explanations for every finding."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Tool registration — importing these modules registers @mcp.tool() decorators
# ---------------------------------------------------------------------------
import mcp_tools  # noqa: E402, F401
import mcp_tools_ext  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TOOLS = [
    "ping", "scan_code", "scan_senior", "check_session",
    "scan_semgrep", "monitor_entropy", "check_config",
    "deep_hallucination", "check_drift", "enforce_brief",
    "shield_prompt", "get_learning",
]


def main():
    """Entry point for vibesrails-mcp CLI."""
    import sys

    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"VibesRails MCP Server v{VERSION}")
        print("Security scanner for AI-assisted coding (Model Context Protocol)")
        print()
        print("Usage: vibesrails-mcp          Start MCP server (stdio transport)")
        print("       vibesrails-mcp --help    Show this help")
        print("       vibesrails-mcp --version Show version")
        print()
        print(f"Available tools ({len(TOOLS)}):")
        for tool in TOOLS:
            print(f"  - {tool}")
        sys.exit(0)

    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"vibesrails-mcp {VERSION}")
        sys.exit(0)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
