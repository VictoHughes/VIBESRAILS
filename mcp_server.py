"""VibesRails MCP Server — security scanner for AI-assisted coding.

Entry point for the Model Context Protocol server.
Transport: stdio (default).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from core.logger import (
    log_rate_limit,
    log_server_start,
    log_tool_call,
    tool_timer,
)
from core.rate_limiter import RateLimiter
from storage.migrations import migrate
from tools.check_config import check_config as _check_config_impl
from tools.check_drift import check_drift as _check_drift_impl
from tools.check_session import check_session as _check_session_impl
from tools.deep_hallucination import deep_hallucination as _deep_hallucination_impl
from tools.enforce_brief import enforce_brief as _enforce_brief_impl
from tools.get_learning import get_learning as _get_learning_impl
from tools.monitor_entropy import monitor_entropy as _monitor_entropy_impl
from tools.scan_code import scan_code as _scan_code_impl
from tools.scan_semgrep import scan_semgrep as _scan_semgrep_impl
from tools.scan_senior import scan_senior as _scan_senior_impl
from tools.shield_prompt import shield_prompt as _shield_prompt_impl

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
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> dict:
    """Health check — returns server status and version."""
    if limited := _check_rate_limit("ping"):
        return limited
    with tool_timer() as t:
        result = {"status": "ok", "version": VERSION}
    log_tool_call("ping", {}, result["status"], t.ms)
    return result


@mcp.tool()
def scan_code(
    file_path: str | None = None,
    project_path: str | None = None,
    guards: list[str] | str = "all",
) -> dict:
    """Run AST security guards on code. Returns findings with pedagogical explanations.

    Args:
        file_path: Path to a single file to scan.
        project_path: Path to a project directory (overrides file_path).
        guards: "all" or a list of guard names (e.g. ["dead_code", "complexity"]).

    Available guards: dependency_audit, performance, complexity, env_safety,
    git_workflow, dead_code, observability, type_safety, docstring,
    pr_checklist, database_safety, api_design, pre_deploy, test_integrity,
    mutation, architecture_drift.
    """
    if limited := _check_rate_limit("scan_code"):
        return limited
    args = {"file_path": file_path, "project_path": project_path, "guards": guards}
    with tool_timer() as t:
        result = _scan_code_impl(
            file_path=file_path, project_path=project_path, guards=guards
        )
    log_tool_call("scan_code", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def scan_senior(
    file_path: str | None = None,
    project_path: str | None = None,
    guards: list[str] | str = "all",
) -> dict:
    """Run Senior Mode guards on code. Detects AI-specific issues.

    Senior guards catch: hallucinated imports, lazy placeholders,
    unjustified bypasses, poor error handling, missing resilience patterns.

    Args:
        file_path: Path to a single file to scan.
        project_path: Path to a project directory (scans all .py files).
        guards: "all" or a list of guard slugs.

    Available guards: error_handling, hallucination, lazy_code, bypass, resilience.
    """
    if limited := _check_rate_limit("scan_senior"):
        return limited
    args = {"file_path": file_path, "project_path": project_path, "guards": guards}
    with tool_timer() as t:
        result = _scan_senior_impl(
            file_path=file_path, project_path=project_path, guards=guards
        )
    log_tool_call("scan_senior", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def check_session() -> dict:
    """Detect if current session is AI-assisted and report guardian status.

    Checks environment variables for known AI coding tools
    (Claude Code, Cursor, Copilot, Aider, Continue, Cody).
    Returns detection result, agent name, and guardian block statistics.
    """
    if limited := _check_rate_limit("check_session"):
        return limited
    with tool_timer() as t:
        result = _check_session_impl()
    log_tool_call("check_session", {}, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def scan_semgrep(
    file_path: str,
    rules: str = "auto",
) -> dict:
    """Run Semgrep vulnerability scan on a file.

    Detects security vulnerabilities, secrets, and code quality issues
    using Semgrep static analysis. Returns findings with pedagogical explanations.

    Args:
        file_path: Path to the file to scan.
        rules: "auto" for default rules, or path to a custom .yaml rules file.
    """
    if limited := _check_rate_limit("scan_semgrep"):
        return limited
    args = {"file_path": file_path, "rules": rules}
    with tool_timer() as t:
        result = _scan_semgrep_impl(file_path=file_path, rules=rules)
    log_tool_call("scan_semgrep", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def monitor_entropy(
    action: str,
    project_path: str | None = None,
    session_id: str | None = None,
    files_modified: list[str] | None = None,
    changes_loc: int | None = None,
    violations: int | None = None,
) -> dict:
    """Monitor AI coding session entropy — tracks session health over time.

    Higher entropy = higher risk of AI hallucinations and code quality issues.
    Levels: safe (0-0.3), warning (0.3-0.6), elevated (0.6-0.8), critical (0.8-1.0).

    Args:
        action: "start", "update", "status", or "end".
        project_path: Project path (required for "start").
        session_id: Session UUID (required for "update", "status", "end").
        files_modified: List of modified file paths (for "update").
        changes_loc: Lines of code changed (for "update").
        violations: Number of violations detected (for "update").
    """
    if limited := _check_rate_limit("monitor_entropy"):
        return limited
    args = {
        "action": action, "project_path": project_path,
        "session_id": session_id, "changes_loc": changes_loc,
    }
    with tool_timer() as t:
        result = _monitor_entropy_impl(
            action=action,
            project_path=project_path,
            session_id=session_id,
            files_modified=files_modified,
            changes_loc=changes_loc,
            violations=violations,
        )
    log_tool_call("monitor_entropy", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def deep_hallucination(
    file_path: str,
    max_level: int = 2,
    ecosystem: str = "pypi",
) -> dict:
    """Multi-level verification of AI-generated imports (hallucination detection).

    Goes beyond basic import checks with 4 verification levels:
      Level 1: Is the module importable locally?
      Level 2: Does the package exist on PyPI? (+ slopsquatting detection)
      Level 3: Does the specific symbol exist in the package?
      Level 4: Is the symbol available in the installed version?

    Args:
        file_path: Path to the Python file to analyze.
        max_level: Maximum verification level (1-4, default 2).
        ecosystem: Package ecosystem ("pypi").
    """
    if limited := _check_rate_limit("deep_hallucination"):
        return limited
    args = {"file_path": file_path, "max_level": max_level, "ecosystem": ecosystem}
    with tool_timer() as t:
        result = _deep_hallucination_impl(
            file_path=file_path, max_level=max_level, ecosystem=ecosystem,
        )
    log_tool_call("deep_hallucination", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def check_drift(
    project_path: str,
    session_id: str | None = None,
) -> dict:
    """Measure architectural drift velocity between coding sessions.

    Takes a project metrics snapshot and compares it with previous snapshots
    to detect how fast the architecture is changing. High velocity indicates
    the AI may be reshaping the codebase beyond the original design.

    Velocity levels: normal (0-5%), warning (5-15%), critical (15%+).
    Flags review_required after 3+ consecutive sessions with >10% drift.

    Args:
        project_path: Path to the project directory.
        session_id: Optional session ID to associate with this snapshot.
    """
    if limited := _check_rate_limit("check_drift"):
        return limited
    args = {"project_path": project_path, "session_id": session_id}
    with tool_timer() as t:
        result = _check_drift_impl(
            project_path=project_path, session_id=session_id,
        )
    log_tool_call("check_drift", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def enforce_brief(
    brief: dict,
    session_id: str | None = None,
    strict: bool = False,
) -> dict:
    """Validate a pre-generation brief before AI code generation.

    Enforces structured briefs to reduce hallucinations and iteration cycles.
    Scores briefs on required fields (intent, constraints, affects) and
    optional fields (tradeoffs, rollback, dependencies).

    Score levels: insufficient (0-39), minimal (40-59), adequate (60-79), strong (80-100).

    Args:
        brief: Dict with fields: intent (str), constraints (list), affects (list),
            and optionally: tradeoffs (str), rollback (str), dependencies (list).
        session_id: Optional session ID for tracking brief quality over time.
        strict: If True, block if score < 60. Default False (block only if < 20).
    """
    if limited := _check_rate_limit("enforce_brief"):
        return limited
    args = {"brief": brief, "session_id": session_id, "strict": strict}
    with tool_timer() as t:
        result = _enforce_brief_impl(
            brief=brief, session_id=session_id, strict=strict,
        )
    log_tool_call("enforce_brief", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def shield_prompt(
    text: str | None = None,
    file_path: str | None = None,
    tool_name: str | None = None,
    arguments: dict | None = None,
) -> dict:
    """Scan for prompt injection in text, code files, or MCP tool inputs.

    Detects 5 injection categories: system_override (ignore/bypass instructions),
    role_hijack (reassign AI identity), exfiltration (send data externally),
    encoding_evasion (base64/Unicode hidden instructions),
    delimiter_escape (LLM tokenizer delimiter injection).

    Args:
        text: Arbitrary text to scan.
        file_path: Path to a file to scan.
        tool_name: MCP tool name (requires arguments).
        arguments: MCP tool arguments dict (requires tool_name).
    """
    if limited := _check_rate_limit("shield_prompt"):
        return limited
    args = {"text": text, "file_path": file_path, "tool_name": tool_name}
    with tool_timer() as t:
        result = _shield_prompt_impl(
            text=text, file_path=file_path,
            tool_name=tool_name, arguments=arguments,
        )
    log_tool_call("shield_prompt", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def check_config(project_path: str) -> dict:
    """Scan AI config files for malicious content (Rules File Backdoor defense).

    Checks .cursorrules, CLAUDE.md, .github/copilot-instructions.md, mcp.json,
    and other AI tool configs for: hidden Unicode, prompt injection,
    exfiltration attempts, and security override instructions.

    Args:
        project_path: Path to the project directory to scan.
    """
    if limited := _check_rate_limit("check_config"):
        return limited
    args = {"project_path": project_path}
    with tool_timer() as t:
        result = _check_config_impl(project_path=project_path)
    log_tool_call("check_config", args, result.get("status", "unknown"), t.ms)
    return result


@mcp.tool()
def get_learning(
    action: str,
    session_id: str | None = None,
    event_type: str | None = None,
    event_data: dict | None = None,
) -> dict:
    """Cross-session developer profiling — tracks patterns across sessions.

    Aggregates events from all VibesRails tools into a developer profile
    with actionable insights on recurring violations, brief quality,
    drift trends, and hallucination rates.

    Args:
        action: "profile" (view profile), "insights" (get recommendations),
            "session_summary" (single session stats), or "record" (log event).
        session_id: Required for "session_summary" and "record".
        event_type: Required for "record". One of: violation, brief_score,
            drift, hallucination, config_issue, injection.
        event_data: Required for "record". Event payload dict.
    """
    if limited := _check_rate_limit("get_learning"):
        return limited
    args = {"action": action, "session_id": session_id, "event_type": event_type}
    with tool_timer() as t:
        result = _get_learning_impl(
            action=action, session_id=session_id,
            event_type=event_type, event_data=event_data,
        )
    log_tool_call("get_learning", args, result.get("status", "unknown"), t.ms)
    return result


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
