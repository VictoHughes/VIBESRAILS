"""MCP tool: check_config — scan AI configuration files for malicious content.

Wraps core/config_shield.py as an MCP-callable tool.
Detects invisible Unicode, prompt injection, exfiltration attempts,
and security override instructions in AI tool config files.

Reference: "Rules File Backdoor" attack (Pillar Security, March 2025).
"""

from __future__ import annotations

import logging

from core.config_shield import AI_CONFIG_PATTERNS, ConfigFinding, ConfigShield
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path

logger = logging.getLogger(__name__)

# ── Pedagogy per check type ───────────────────────────────────────────

CHECK_PEDAGOGY: dict[str, dict[str, str]] = {
    "invisible_unicode": {
        "why": (
            "This file contains invisible Unicode characters that are readable by LLMs "
            "but invisible to humans. This is the 'Rules File Backdoor' attack documented "
            "by Pillar Security (March 2025). An attacker can hide malicious instructions "
            "in your AI configuration files."
        ),
        "how_to_fix": "Open the file in hex mode. Remove all unintended non-ASCII characters.",
        "prevention": "Always verify AI config files after git pull from external sources.",
    },
    "contradictory": {
        "why": (
            "This instruction attempts to override or contradict existing AI guidelines. "
            "Patterns like 'ignore previous instructions' or 'you are now' are classic "
            "prompt injection techniques that hijack AI behavior."
        ),
        "how_to_fix": "Remove the suspicious instruction. Check git blame to identify who added it.",
        "prevention": "Review all changes to AI config files in PRs. Treat them as security-critical.",
    },
    "exfiltration": {
        "why": (
            "This instruction tells the AI to send code, data, or context to an external "
            "endpoint. If added by a malicious actor, it could exfiltrate your source code, "
            "secrets, or proprietary information."
        ),
        "how_to_fix": "Verify that the destination URL is legitimate and expected. Remove if suspicious.",
        "prevention": "Whitelist allowed domains. Never allow AI configs to send data to unknown endpoints.",
    },
    "security_override": {
        "why": (
            "This instruction weakens security protections for your AI tool. "
            "Instructions to 'skip security', 'disable validation', or 'hardcode credentials' "
            "are potentially dangerous, especially if added by a third party."
        ),
        "how_to_fix": "Remove the override instruction. Implement proper security practices instead.",
        "prevention": "Treat AI config files as security-critical. Review all changes carefully.",
    },
}

_NO_FILES_PEDAGOGY = {
    "why": (
        "No AI configuration files were found in this project. "
        "AI config files define how AI tools (Claude, Cursor, Copilot, etc.) "
        "behave when working on your code."
    ),
    "supported_files": AI_CONFIG_PATTERNS,
    "recommendation": (
        "If you use AI coding tools, consider adding a CLAUDE.md or .cursorrules "
        "file to set project-specific guidelines."
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────

def _finding_to_dict(finding: ConfigFinding) -> dict:
    """Convert a ConfigFinding to a MCP result dict with pedagogy."""
    pedagogy = CHECK_PEDAGOGY.get(finding.check_type, CHECK_PEDAGOGY["security_override"])

    return {
        "check_type": finding.check_type,
        "severity": finding.severity,
        "message": finding.message,
        "file": finding.file,
        "line": finding.line,
        "matched_text": finding.matched_text,
        "pedagogy": {
            "why": pedagogy["why"],
            "how_to_fix": pedagogy["how_to_fix"],
            "prevention": pedagogy["prevention"],
        },
    }


def _determine_status(findings: list[dict]) -> str:
    """Determine overall status from findings."""
    if not findings:
        return "pass"
    severities = {f["severity"] for f in findings}
    if "block" in severities:
        return "block"
    if "warn" in severities:
        return "warn"
    return "info"


# ── Core logic ────────────────────────────────────────────────────────

def check_config(project_path: str) -> dict:
    """Scan AI config files in a project for malicious content.

    Args:
        project_path: Path to the project directory.

    Returns:
        Dict with status, files_scanned, files_found, findings, pedagogy.
    """
    try:
        validate_path(project_path, must_exist=True, must_be_dir=True)
    except PathValidationError as exc:
        return _error_result(str(exc))

    shield = ConfigShield()
    result = shield.scan_project(project_path)

    # No config files found
    if result["files_found"] == 0:
        return {
            "status": "info",
            "files_scanned": [],
            "files_found": 0,
            "findings": [],
            "summary": {"total": 0, "by_check_type": {}},
            "pedagogy": _NO_FILES_PEDAGOGY,
        }

    # Convert findings
    findings = [_finding_to_dict(f) for f in result["findings"]]

    # Summary
    by_check_type: dict[str, int] = {}
    for f in findings:
        ct = f["check_type"]
        by_check_type[ct] = by_check_type.get(ct, 0) + 1

    # Feed Learning Engine
    for f in findings:
        record_safe(None, "config_issue", {"check_type": f["check_type"], "severity": f["severity"]})

    return {
        "status": _determine_status(findings),
        "files_scanned": result["files_scanned"],
        "files_found": result["files_found"],
        "findings": findings,
        "summary": {
            "total": len(findings),
            "by_check_type": by_check_type,
        },
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "files_scanned": [],
        "files_found": 0,
        "findings": [],
        "summary": {"total": 0, "by_check_type": {}},
        "error": message,
    }
