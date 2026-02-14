"""Tests for tools/scan_senior.py — MCP scan_senior tool."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.scan_senior import (  # noqa: E402
    AVAILABLE_GUARDS,
    GUARD_PEDAGOGY,
    _determine_status,
    _error_result,
    _issue_to_finding,
    _resolve_guards,
    scan_senior,
)
from vibesrails.senior_mode.guards import GuardIssue  # noqa: E402

# ── Fixtures ───────────────────────────────────────────────────────────

BAD_ERROR_HANDLING = """\
import os

def risky():
    try:
        os.remove("file.txt")
    except:
        pass
"""

BAD_LAZY_CODE = """\
def placeholder():
    pass

def another():
    ...

def todo_func():
    # TODO  # vibesrails: ignore
    return None
"""

BAD_BYPASS = """\
x = 1  # type: ignore
y = 2  # noqa
z = 3  # nosec
"""

BAD_RESILIENCE = """\
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()
"""

CLEAN_CODE = """\
\"\"\"A clean module.\"\"\"

import logging

logger = logging.getLogger(__name__)


def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""


def _write_file(tmp_path: Path, content: str, name: str = "example.py") -> Path:
    """Write a Python file to tmp_path and return its path."""
    f = tmp_path / name
    f.write_text(content)
    return f


# ── Guard registry ─────────────────────────────────────────────────────


class TestGuardRegistry:
    """Tests for the senior guard registry."""

    def test_five_guards_available(self):
        assert len(AVAILABLE_GUARDS) == 5

    def test_expected_guard_names(self):
        expected = {"bypass", "error_handling", "hallucination", "lazy_code", "resilience"}
        assert set(AVAILABLE_GUARDS) == expected

    def test_all_guards_have_pedagogy(self):
        for slug in AVAILABLE_GUARDS:
            assert slug in GUARD_PEDAGOGY, f"Missing pedagogy for {slug}"

    def test_pedagogy_has_required_keys(self):
        for slug, pedagogy in GUARD_PEDAGOGY.items():
            assert "why" in pedagogy, f"{slug} missing 'why'"
            assert "how_to_fix" in pedagogy, f"{slug} missing 'how_to_fix'"
            assert "prevention" in pedagogy, f"{slug} missing 'prevention'"


# ── _resolve_guards ────────────────────────────────────────────────────


class TestResolveGuards:
    """Tests for guard name resolution."""

    def test_all_returns_all_guards(self):
        result = _resolve_guards("all")
        assert len(result) == 5

    def test_specific_guard(self):
        result = _resolve_guards(["error_handling"])
        assert len(result) == 1
        assert result[0][0] == "error_handling"

    def test_multiple_guards(self):
        result = _resolve_guards(["error_handling", "bypass"])
        slugs = [slug for slug, _ in result]
        assert slugs == ["error_handling", "bypass"]

    def test_unknown_guard_raises(self):
        try:
            _resolve_guards(["nonexistent_guard"])
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "nonexistent_guard" in str(exc)
            assert "Available:" in str(exc)


# ── _determine_status ──────────────────────────────────────────────────


class TestDetermineStatus:
    """Tests for status determination from findings."""

    def test_empty_findings_pass(self):
        assert _determine_status([]) == "pass"

    def test_block_severity(self):
        assert _determine_status([{"severity": "block"}]) == "block"

    def test_warn_severity(self):
        assert _determine_status([{"severity": "warn"}]) == "warn"

    def test_info_severity(self):
        assert _determine_status([{"severity": "info"}]) == "info"

    def test_mixed_returns_worst(self):
        findings = [{"severity": "info"}, {"severity": "warn"}, {"severity": "block"}]
        assert _determine_status(findings) == "block"


# ── _issue_to_finding ──────────────────────────────────────────────────


class TestIssueToFinding:
    """Tests for GuardIssue to finding dict conversion."""

    def test_basic_conversion(self):
        issue = GuardIssue(
            guard="ErrorHandlingGuard",
            severity="warn",
            message="bare except",
            file="test.py",
            line=5,
        )
        finding = _issue_to_finding(issue, "error_handling")
        assert finding["guard"] == "ErrorHandlingGuard"
        assert finding["severity"] == "warn"
        assert finding["message"] == "bare except"
        assert finding["file"] == "test.py"
        assert finding["line"] == 5
        assert "pedagogy" in finding
        assert "why" in finding["pedagogy"]

    def test_no_file_no_line(self):
        issue = GuardIssue(
            guard="ErrorHandlingGuard",
            severity="warn",
            message="test",
        )
        finding = _issue_to_finding(issue, "error_handling")
        assert "file" not in finding
        assert "line" not in finding

    def test_unknown_slug_uses_default_pedagogy(self):
        issue = GuardIssue(guard="X", severity="warn", message="msg")
        finding = _issue_to_finding(issue, "unknown_slug")
        assert "pedagogy" in finding
        assert "why" in finding["pedagogy"]


# ── _error_result ──────────────────────────────────────────────────────


class TestErrorResult:
    """Tests for error result formatting."""

    def test_error_result_structure(self):
        result = _error_result("Something went wrong")
        assert result["status"] == "error"
        assert result["findings"] == []
        assert result["guards_run"] == []
        assert result["summary"]["total"] == 0
        assert result["error"] == "Something went wrong"


# ── scan_senior integration ───────────────────────────────────────────


class TestScanSeniorIntegration:
    """Integration tests for the scan_senior function."""

    def test_error_handling_detects_bare_except(self, tmp_path):
        f = _write_file(tmp_path, BAD_ERROR_HANDLING)
        result = scan_senior(file_path=str(f), guards=["error_handling"])
        assert result["status"] != "pass"
        messages = [fi["message"] for fi in result["findings"]]
        assert any("except" in m.lower() or "bare" in m.lower() for m in messages), (
            f"Expected bare except detection, got: {messages}"
        )

    def test_lazy_code_detects_pass(self, tmp_path):
        f = _write_file(tmp_path, BAD_LAZY_CODE)
        result = scan_senior(file_path=str(f), guards=["lazy_code"])
        assert result["status"] != "pass"
        assert result["summary"]["total"] > 0

    def test_bypass_detects_bare_noqa(self, tmp_path):
        f = _write_file(tmp_path, BAD_BYPASS)
        result = scan_senior(file_path=str(f), guards=["bypass"])
        assert result["status"] != "pass"
        messages = [fi["message"] for fi in result["findings"]]
        assert any("noqa" in m.lower() or "nosec" in m.lower() or "type" in m.lower() for m in messages), (
            f"Expected bypass detection, got: {messages}"
        )

    def test_resilience_detects_no_timeout(self, tmp_path):
        f = _write_file(tmp_path, BAD_RESILIENCE)
        result = scan_senior(file_path=str(f), guards=["resilience"])
        assert result["status"] != "pass"
        messages = [fi["message"] for fi in result["findings"]]
        assert any("timeout" in m.lower() for m in messages), (
            f"Expected timeout detection, got: {messages}"
        )

    def test_clean_code_passes(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_senior(file_path=str(f), guards="all")
        # Clean code may still have some findings (hallucination checks logging),
        # but should have no error_handling, lazy_code, bypass, or resilience issues
        severe = [fi for fi in result["findings"] if fi["guard"] in (
            "ErrorHandlingGuard", "LazyCodeGuard", "BypassGuard", "ResilienceGuard"
        )]
        assert len(severe) == 0

    def test_guards_all_runs_five(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_senior(file_path=str(f), guards="all")
        assert len(result["guards_run"]) == 5

    def test_findings_have_pedagogy(self, tmp_path):
        f = _write_file(tmp_path, BAD_ERROR_HANDLING)
        result = scan_senior(file_path=str(f), guards=["error_handling"])
        for finding in result["findings"]:
            assert "pedagogy" in finding
            p = finding["pedagogy"]
            assert "why" in p
            assert "how_to_fix" in p
            assert "prevention" in p

    def test_nonexistent_file_returns_error(self):
        result = scan_senior(file_path="/nonexistent/path/file.py")
        assert result["status"] == "error"
        assert "does not exist" in result.get("error", "")

    def test_no_path_returns_error(self):
        result = scan_senior()
        assert result["status"] == "error"
        assert "required" in result.get("error", "").lower()

    def test_invalid_guard_returns_error(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_senior(file_path=str(f), guards=["fake_guard"])
        assert result["status"] == "error"
        assert "Unknown senior guard" in result.get("error", "")

    def test_project_path_scans_directory(self, tmp_path):
        _write_file(tmp_path, BAD_ERROR_HANDLING, "bad.py")
        _write_file(tmp_path, CLEAN_CODE, "clean.py")
        result = scan_senior(project_path=str(tmp_path), guards=["error_handling"])
        assert result["guards_run"] == ["error_handling"]
        # Should find issues in bad.py
        bad_findings = [fi for fi in result["findings"] if fi.get("file", "").endswith("bad.py")]
        assert len(bad_findings) > 0

    def test_summary_counts_correct(self, tmp_path):
        f = _write_file(tmp_path, BAD_ERROR_HANDLING)
        result = scan_senior(file_path=str(f), guards=["error_handling"])
        total = sum(result["summary"]["by_severity"].values())
        assert total == result["summary"]["total"]
        assert total == len(result["findings"])

    def test_result_structure(self, tmp_path):
        f = _write_file(tmp_path, CLEAN_CODE)
        result = scan_senior(file_path=str(f), guards=["error_handling"])
        assert "status" in result
        assert "findings" in result
        assert "guards_run" in result
        assert "summary" in result
        assert "total" in result["summary"]
        assert "by_severity" in result["summary"]

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        _write_file(hidden, BAD_ERROR_HANDLING, "bad.py")
        result = scan_senior(project_path=str(tmp_path), guards=["error_handling"])
        hidden_findings = [fi for fi in result["findings"] if ".hidden" in fi.get("file", "")]
        assert len(hidden_findings) == 0

    def test_skips_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        _write_file(cache, BAD_ERROR_HANDLING, "bad.py")
        result = scan_senior(project_path=str(tmp_path), guards=["error_handling"])
        cache_findings = [fi for fi in result["findings"] if "__pycache__" in fi.get("file", "")]
        assert len(cache_findings) == 0
