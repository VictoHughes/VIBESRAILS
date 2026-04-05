"""MCP config security auditor — OWASP MCP Top 10 checks.

Scans .mcp.json and claude_desktop_config.json for:
- Hardcoded secrets in env blocks
- Unpinned npx package references
- Shell injection metacharacters in command fields
- Sensitive filesystem paths in args
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Secret patterns — reuse the pre_tool_use central source of truth
# ---------------------------------------------------------------------------
try:
    from vibesrails.hooks.pre_tool_use import (
        SECRET_PATTERNS as _RAW_SECRET_PATTERNS,  # type: ignore[import]
    )

    _COMPILED_SECRETS = [
        (re.compile(pattern, re.IGNORECASE), label)
        for pattern, label in _RAW_SECRET_PATTERNS
    ]
except ImportError:
    _COMPILED_SECRETS = [
        (
            re.compile(
                r"(?:api_key|secret|token|password|passwd)\s*=\s*['\"][^'\"]{8,}['\"]",
                re.IGNORECASE,
            ),
            "Hardcoded secret detected",
        ),
        (
            re.compile(
                r"(?:AKIA|sk-|ghp_|gho_)[A-Za-z0-9_\-]{10,}",
                re.IGNORECASE,
            ),
            "API key detected",
        ),
    ]

# ---------------------------------------------------------------------------
# Compiled check patterns
# ---------------------------------------------------------------------------

# Shell injection metacharacters / dangerous commands in a command field
_SHELL_INJECTION = re.compile(r"[;&|`$]|\b(curl|wget|nc|bash|sh)\b")

# Sensitive filesystem paths in args
_SENSITIVE_PATHS = re.compile(
    r"(/root|/etc/shadow|\.ssh|\.gnupg|\.aws/credentials|\.env)",
    re.IGNORECASE,
)

# Unpinned npx package: @scope/package WITHOUT @version suffix
# Matches @scope/package but NOT @scope/package@1.2.3
_UNPINNED_NPX = re.compile(r"^@[\w-]+/[\w-]+$")


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


@dataclass
class MCPFinding:
    """A single security finding from an MCP config audit."""

    check_type: str
    severity: str  # "block" | "warn" | "info"
    message: str
    server_name: str
    field: str


# ---------------------------------------------------------------------------
# Internal check functions
# ---------------------------------------------------------------------------


def _check_secrets(name: str, cfg: dict) -> list[MCPFinding]:
    """Scan env block values for hardcoded secrets (severity: block)."""
    findings: list[MCPFinding] = []
    env = cfg.get("env", {})
    if not isinstance(env, dict):
        return findings
    for key, value in env.items():
        if not isinstance(value, str):
            continue
        for compiled, label in _COMPILED_SECRETS:
            if compiled.search(value):
                findings.append(
                    MCPFinding(
                        check_type="hardcoded_secret",
                        severity="block",
                        message=f"{label} in env key '{key}'",
                        server_name=name,
                        field="env",
                    )
                )
                break  # one finding per env key is enough
    return findings


def _check_unpinned(name: str, cfg: dict) -> list[MCPFinding]:
    """Detect unpinned npx package references (severity: warn)."""
    findings: list[MCPFinding] = []
    command = cfg.get("command", "")
    if command not in ("npx", "npx.cmd"):
        return findings
    args = cfg.get("args", [])
    if not isinstance(args, list):
        return findings
    for arg in args:
        if not isinstance(arg, str):
            continue
        if _UNPINNED_NPX.match(arg):
            findings.append(
                MCPFinding(
                    check_type="unpinned_version",
                    severity="warn",
                    message=(
                        f"npx package '{arg}' is unpinned — "
                        "pin with @version to prevent supply-chain attacks"
                    ),
                    server_name=name,
                    field="args",
                )
            )
    return findings


def _check_injection(name: str, cfg: dict) -> list[MCPFinding]:
    """Detect shell injection metacharacters in command field (severity: block)."""
    findings: list[MCPFinding] = []
    command = cfg.get("command", "")
    if not isinstance(command, str):
        return findings
    if _SHELL_INJECTION.search(command):
        findings.append(
            MCPFinding(
                check_type="shell_injection",
                severity="block",
                message=(
                    f"Shell metacharacter or dangerous command in 'command' field: "
                    f"'{command}'"
                ),
                server_name=name,
                field="command",
            )
        )
    return findings


def _check_paths(name: str, cfg: dict) -> list[MCPFinding]:
    """Detect sensitive filesystem paths in args (severity: warn)."""
    findings: list[MCPFinding] = []
    args = cfg.get("args", [])
    if not isinstance(args, list):
        return findings
    for arg in args:
        if not isinstance(arg, str):
            continue
        if _SENSITIVE_PATHS.search(arg):
            findings.append(
                MCPFinding(
                    check_type="sensitive_path",
                    severity="warn",
                    message=f"Sensitive filesystem path in args: '{arg}'",
                    server_name=name,
                    field="args",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_MCP_CONFIG_FILES = [".mcp.json", "claude_desktop_config.json"]

_ALL_CHECKS = [_check_secrets, _check_unpinned, _check_injection, _check_paths]


def audit_mcp_config(root: Path) -> list[MCPFinding]:
    """Audit all MCP config files under *root* and return a list of findings.

    Reads `.mcp.json` and `claude_desktop_config.json` (whichever exist),
    iterates over ``mcpServers``, and runs all security checks on each server
    definition.

    Parameters
    ----------
    root:
        Directory to look for config files in.

    Returns
    -------
    list[MCPFinding]
        Possibly empty list of security findings.
    """
    findings: list[MCPFinding] = []

    for filename in _MCP_CONFIG_FILES:
        config_path = root / filename
        if not config_path.exists():
            continue

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        mcp_servers = data.get("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            continue

        for server_name, server_cfg in mcp_servers.items():
            if not isinstance(server_cfg, dict):
                continue
            for check in _ALL_CHECKS:
                findings.extend(check(server_name, server_cfg))

    return findings
