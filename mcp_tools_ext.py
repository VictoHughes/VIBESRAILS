"""VibesRails MCP Tools — extended tools.

Tool wrappers for: enforce_brief, shield_prompt, check_config,
get_learning, ping, check_session.
"""

from __future__ import annotations

from core.logger import log_tool_call, tool_timer
from mcp_server import VERSION, _check_rate_limit, mcp
from tools.check_config import check_config as _check_config_impl
from tools.check_session import check_session as _check_session_impl
from tools.enforce_brief import enforce_brief as _enforce_brief_impl
from tools.get_learning import get_learning as _get_learning_impl
from tools.shield_prompt import shield_prompt as _shield_prompt_impl


@mcp.tool()
def ping() -> dict:
    """Health check --- returns server status and version."""
    if limited := _check_rate_limit("ping"):
        return limited
    with tool_timer() as t:
        result = {"status": "ok", "version": VERSION}
    log_tool_call("ping", {}, result["status"], t.ms)
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
    """Cross-session developer profiling --- tracks patterns across sessions.

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
