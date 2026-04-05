"""MCP tool: scan_bandit — run Bandit SAST scan on a file."""

from __future__ import annotations

import logging

from core.input_validator import sanitize_for_output, validate_string
from core.learning_bridge import record_safe
from core.path_validator import validate_path
from vibesrails.adapters.bandit_adapter import BanditAdapter, classify_severity

logger = logging.getLogger(__name__)

_PEDAGOGY = {
    "why": "Bandit detects security issues in Python code via AST analysis (hardcoded secrets, eval/exec, insecure deserialization).",
    "how_to_fix": "Follow the suggestion in the finding. Use environment variables for secrets, parameterized queries for SQL.",
    "prevention": "Run vibesrails --bandit before every commit. Add bandit to dev dependencies.",
}


def _result_to_finding(result) -> dict:
    sev = classify_severity(result.severity, result.confidence)
    return {
        "file": result.file,
        "line": result.line,
        "test_id": result.test_id,
        "severity": sev,
        "message": sanitize_for_output(result.message),
        "code_snippet": sanitize_for_output((result.code_snippet or "")[:200]),
    }


async def scan_bandit_impl(file_path: str) -> dict:
    """Run Bandit on a file and return findings."""
    try:
        validate_string(file_path, "file_path", max_length=500)
        safe_path = validate_path(file_path)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    adapter = BanditAdapter({})
    if not adapter.is_installed():
        return {"status": "not_installed", "message": "Bandit not installed. Run: pip install bandit", "pedagogy": _PEDAGOGY}

    results = adapter.scan([str(safe_path)])
    findings = [_result_to_finding(r) for r in results]
    blocking = sum(1 for f in findings if f["severity"] == "block")

    record_safe("violation", {"tool": "scan_bandit", "file": str(safe_path), "findings": len(findings), "blocking": blocking})

    return {
        "status": "blocking" if blocking else ("warnings" if findings else "clean"),
        "findings": findings,
        "summary": f"{len(findings)} finding(s), {blocking} blocking",
        "pedagogy": _PEDAGOGY,
    }
