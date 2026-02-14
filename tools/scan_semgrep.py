"""MCP tool: scan_semgrep — run Semgrep vulnerability scan on code.

Wraps the VibesRails Semgrep adapter as an MCP-callable tool.
Detects security vulnerabilities, secrets, and code quality issues
using Semgrep's static analysis engine.
"""

from __future__ import annotations

import logging

from adapters.semgrep_adapter import SemgrepAdapter, SemgrepResult
from core.input_validator import InputValidationError, validate_string
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path

logger = logging.getLogger(__name__)

# ── Pedagogy by severity / rule category ──────────────────────────────

_CATEGORY_PEDAGOGY: dict[str, dict[str, str]] = {
    "security": {
        "why": (
            "This code contains a security vulnerability that could be exploited "
            "by an attacker. AI-generated code is especially prone to security "
            "issues because models optimize for 'working code', not 'secure code'."
        ),
        "how_to_fix": "Follow the suggestion in the finding message. Use parameterized queries, escape user input, avoid eval/exec.",
        "prevention": "Run Semgrep on every PR. Never trust AI-generated code that handles user input or secrets.",
    },
    "secrets": {
        "why": (
            "A potential secret (API key, password, token) was found in the source code. "
            "AI models frequently generate placeholder secrets or copy real ones from training data."
        ),
        "how_to_fix": "Move the secret to an environment variable or a secrets manager. Rotate the exposed credential immediately.",
        "prevention": "Use .env files (gitignored) for secrets. Run secret scanning before every commit.",
    },
    "correctness": {
        "why": (
            "This code has a correctness issue that may cause unexpected behavior. "
            "AI generators sometimes produce code that looks right but has subtle logic errors."
        ),
        "how_to_fix": "Review the finding and fix the logic error. Write a test that covers this specific case.",
        "prevention": "Always write tests for AI-generated code. Don't assume it's correct because it compiles.",
    },
    "performance": {
        "why": (
            "This code has a performance issue that could cause slowness or resource exhaustion. "
            "AI-generated code often ignores performance considerations."
        ),
        "how_to_fix": "Optimize the flagged code path. Consider caching, batching, or algorithmic improvements.",
        "prevention": "Profile AI-generated code before deploying to production.",
    },
}

_DEFAULT_PEDAGOGY = {
    "why": "Semgrep detected an issue in this code. Review the rule message for details.",
    "how_to_fix": "Address the specific issue described in the finding message.",
    "prevention": "Run Semgrep regularly to catch issues before they reach production.",
}

_NOT_INSTALLED_PEDAGOGY = {
    "why": (
        "Semgrep is a fast, open-source static analysis tool that finds bugs and security "
        "vulnerabilities. It's essential for scanning AI-generated code because models "
        "frequently produce insecure patterns (SQL injection, XSS, hardcoded secrets)."
    ),
    "how_to_fix": "Install Semgrep: pip install semgrep",
    "prevention": "Add semgrep to your project's dev dependencies.",
}


# ── Helpers ───────────────────────────────────────────────────────────

def _classify_rule(rule_id: str, severity: str) -> str:
    """Classify a Semgrep rule into a pedagogy category."""
    rule_lower = rule_id.lower()
    if any(kw in rule_lower for kw in ("secret", "credential", "password", "token", "api-key")):
        return "secrets"
    if any(kw in rule_lower for kw in ("security", "injection", "xss", "csrf", "auth", "crypto", "eval")):
        return "security"
    if any(kw in rule_lower for kw in ("performance", "complexity", "timeout")):
        return "performance"
    if severity == "ERROR":
        return "security"
    return "correctness"


def _result_to_finding(result: SemgrepResult) -> dict:
    """Convert a SemgrepResult to a MCP finding dict with pedagogy."""
    category = _classify_rule(result.rule_id, result.severity)
    pedagogy = _CATEGORY_PEDAGOGY.get(category, _DEFAULT_PEDAGOGY)

    severity_map = {"ERROR": "block", "WARNING": "warn", "INFO": "info"}

    finding: dict = {
        "rule_id": result.rule_id,
        "severity": severity_map.get(result.severity, "info"),
        "message": result.message,
        "file": result.file,
        "line": result.line,
        "pedagogy": {
            "why": pedagogy["why"],
            "how_to_fix": pedagogy["how_to_fix"],
            "prevention": pedagogy["prevention"],
        },
    }
    if result.code_snippet:
        snippet = result.code_snippet
        finding["code_snippet"] = snippet[:200] + "..." if len(snippet) > 200 else snippet

    return finding


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

def scan_semgrep(
    file_path: str,
    rules: str = "auto",
) -> dict:
    """Run Semgrep vulnerability scan on a file.

    Args:
        file_path: Path to the file to scan.
        rules: "auto" for default Semgrep rules, or path to a custom .yaml rules file.

    Returns:
        Dict with keys: status, findings, semgrep_version, rules_used, summary, pedagogy.
    """
    # Validate string inputs
    try:
        validate_string(file_path, "file_path", max_length=4096)
    except InputValidationError as exc:
        return _error_result(str(exc))

    # Validate paths
    try:
        fp = validate_path(file_path, must_exist=True, must_be_file=True)
    except PathValidationError as exc:
        return _error_result(str(exc))

    # Build adapter config
    config: dict = {"preset": "auto", "enabled": True}
    rules_used = "auto"

    if rules != "auto":
        try:
            rules_path = validate_path(
                rules, must_exist=True, must_be_file=True,
                allowed_extensions={".yaml", ".yml"},
            )
        except PathValidationError as exc:
            return _error_result(str(exc))
        config["additional_rules"] = [str(rules_path)]
        rules_used = str(rules_path)

    adapter = SemgrepAdapter(config)

    # Check if Semgrep is installed
    if not adapter.is_installed():
        return {
            "status": "error",
            "findings": [],
            "semgrep_version": None,
            "rules_used": rules_used,
            "summary": {"total": 0, "by_severity": {}},
            "error": "Semgrep not installed. Run: pip install semgrep",
            "pedagogy": _NOT_INSTALLED_PEDAGOGY,
        }

    # Get version
    version = adapter.get_version()

    # Run scan
    results = adapter.scan([str(fp)])

    # Convert to findings
    findings = [_result_to_finding(r) for r in results]

    # Build summary
    by_severity: dict[str, int] = {}
    for f in findings:
        sev = f["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # Feed Learning Engine
    for f in findings:
        record_safe(None, "violation", {"guard_name": f["rule_id"], "severity": f["severity"]})

    return {
        "status": _determine_status(findings),
        "findings": findings,
        "semgrep_version": version,
        "rules_used": rules_used,
        "summary": {
            "total": len(findings),
            "by_severity": by_severity,
        },
    }


def _error_result(message: str) -> dict:
    """Return a standardized error result."""
    return {
        "status": "error",
        "findings": [],
        "semgrep_version": None,
        "rules_used": None,
        "summary": {"total": 0, "by_severity": {}},
        "error": message,
    }
