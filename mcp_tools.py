"""VibesRails MCP Tools — core scanning tools.

Tool wrappers for: scan_code, scan_senior, scan_semgrep,
monitor_entropy, deep_hallucination, check_drift.
"""

from __future__ import annotations

from core.logger import log_tool_call, tool_timer
from mcp_server import _check_rate_limit, mcp
from tools.check_drift import check_drift as _check_drift_impl
from tools.deep_hallucination import deep_hallucination as _deep_hallucination_impl
from tools.monitor_entropy import monitor_entropy as _monitor_entropy_impl
from tools.scan_code import scan_code as _scan_code_impl
from tools.scan_semgrep import scan_semgrep as _scan_semgrep_impl
from tools.scan_senior import scan_senior as _scan_senior_impl


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
    """Monitor AI coding session entropy --- tracks session health over time.

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
