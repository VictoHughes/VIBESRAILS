"""MCP tool: audit_mcp — security audit of MCP server configurations."""

from __future__ import annotations

import logging
from pathlib import Path

from core.input_validator import sanitize_for_output
from core.learning_bridge import record_safe

logger = logging.getLogger(__name__)

_PEDAGOGY = {
    "why": "MCP configs can contain hardcoded secrets, unpinned versions (rug pull risk), or shell injection patterns.",
    "how_to_fix": "Use environment variables for secrets, pin package versions with @version, avoid shell metacharacters.",
    "prevention": "Run vibesrails --audit-mcp before adding new MCP servers. Reference: OWASP MCP Top 10.",
}


async def audit_mcp_impl(project_path: str | None = None) -> dict:
    """Audit MCP configs for security issues."""
    from vibesrails.mcp_audit import audit_mcp_config

    root = Path(project_path) if project_path else Path.cwd()
    findings = audit_mcp_config(root)

    result_findings = [
        {
            "check_type": f.check_type,
            "severity": f.severity,
            "message": sanitize_for_output(f.message),
            "server": f.server_name,
        }
        for f in findings
    ]

    blocking = sum(1 for f in result_findings if f["severity"] == "block")

    record_safe("config_issue", {"tool": "audit_mcp", "findings": len(result_findings), "blocking": blocking})

    return {
        "status": "blocking" if blocking else ("warnings" if result_findings else "clean"),
        "findings": result_findings,
        "summary": f"{len(result_findings)} finding(s), {blocking} blocking",
        "pedagogy": _PEDAGOGY,
    }
