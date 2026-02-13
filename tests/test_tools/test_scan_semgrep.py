"""Tests for tools/scan_semgrep.py — MCP scan_semgrep tool."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from adapters.semgrep_adapter import SemgrepResult  # noqa: E402
from tools.scan_semgrep import (  # noqa: E402
    _NOT_INSTALLED_PEDAGOGY,
    _classify_rule,
    _determine_status,
    _error_result,
    _result_to_finding,
    scan_semgrep,
)

# ── Fixtures ───────────────────────────────────────────────────────────

VULN_CODE = """\
import subprocess

def run_command(user_input):
    # Vulnerable: shell injection
    subprocess.call(user_input, shell=True)
"""

CLEAN_CODE = """\
\"\"\"A safe module.\"\"\"

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""


def _write_file(tmp_path: Path, content: str, name: str = "example.py") -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


# ── _classify_rule ─────────────────────────────────────────────────────


class TestClassifyRule:
    """Tests for rule classification into pedagogy categories."""

    def test_security_rule(self):
        assert _classify_rule("python.lang.security.audit.injection", "WARNING") == "security"

    def test_secrets_rule(self):
        assert _classify_rule("generic.secrets.api-key-detected", "WARNING") == "secrets"

    def test_performance_rule(self):
        assert _classify_rule("python.lang.performance.slow-loop", "WARNING") == "performance"

    def test_error_severity_defaults_security(self):
        assert _classify_rule("python.unknown.rule", "ERROR") == "security"

    def test_unknown_defaults_correctness(self):
        assert _classify_rule("python.unknown.rule", "WARNING") == "correctness"


# ── _result_to_finding ─────────────────────────────────────────────────


class TestResultToFinding:
    """Tests for SemgrepResult to finding dict conversion."""

    def test_basic_conversion(self):
        result = SemgrepResult(
            file="test.py", line=5, rule_id="python.lang.security.injection",
            message="injection risk", severity="ERROR",
        )
        finding = _result_to_finding(result)
        assert finding["rule_id"] == "python.lang.security.injection"
        assert finding["severity"] == "block"
        assert finding["file"] == "test.py"
        assert finding["line"] == 5
        assert "pedagogy" in finding
        assert "why" in finding["pedagogy"]
        assert "how_to_fix" in finding["pedagogy"]
        assert "prevention" in finding["pedagogy"]

    def test_severity_mapping(self):
        for semgrep_sev, mcp_sev in [("ERROR", "block"), ("WARNING", "warn"), ("INFO", "info")]:
            result = SemgrepResult(
                file="t.py", line=1, rule_id="r", message="m", severity=semgrep_sev,
            )
            assert _result_to_finding(result)["severity"] == mcp_sev

    def test_code_snippet_included(self):
        result = SemgrepResult(
            file="t.py", line=1, rule_id="r", message="m",
            severity="WARNING", code_snippet="dangerous(x)",
        )
        finding = _result_to_finding(result)
        assert finding["code_snippet"] == "dangerous(x)"

    def test_no_code_snippet(self):
        result = SemgrepResult(
            file="t.py", line=1, rule_id="r", message="m", severity="WARNING",
        )
        finding = _result_to_finding(result)
        assert "code_snippet" not in finding


# ── _determine_status ──────────────────────────────────────────────────


class TestDetermineStatus:
    """Tests for status determination."""

    def test_empty_pass(self):
        assert _determine_status([]) == "pass"

    def test_block(self):
        assert _determine_status([{"severity": "block"}]) == "block"

    def test_warn(self):
        assert _determine_status([{"severity": "warn"}]) == "warn"

    def test_mixed(self):
        assert _determine_status([{"severity": "info"}, {"severity": "block"}]) == "block"


# ── _error_result ──────────────────────────────────────────────────────


class TestErrorResult:
    """Tests for error result formatting."""

    def test_structure(self):
        result = _error_result("Something broke")
        assert result["status"] == "error"
        assert result["findings"] == []
        assert result["semgrep_version"] is None
        assert result["rules_used"] is None
        assert result["error"] == "Something broke"


# ── scan_semgrep — not installed ───────────────────────────────────────


class TestScanSemgrepNotInstalled:
    """Tests for when Semgrep is not installed."""

    def test_returns_error_with_pedagogy(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        with patch("adapters.semgrep_adapter.shutil.which", return_value=None):
            result = scan_semgrep(file_path=str(f))
        assert result["status"] == "error"
        assert "not installed" in result["error"].lower()
        assert result["semgrep_version"] is None
        assert "pedagogy" in result
        assert result["pedagogy"]["why"] == _NOT_INSTALLED_PEDAGOGY["why"]

    def test_no_crash_on_missing_semgrep(self, tmp_path):
        f = _write_file(tmp_path, VULN_CODE)
        with patch("adapters.semgrep_adapter.shutil.which", return_value=None):
            result = scan_semgrep(file_path=str(f))
        assert result["status"] == "error"
        assert result["findings"] == []
