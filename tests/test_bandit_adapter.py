"""
Tests for Bandit SAST adapter.

Tests BanditAdapter and classify_severity helper.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from vibesrails.adapters.bandit_adapter import (
    BanditAdapter,
    BanditResult,
    classify_severity,
)

# Sample Bandit JSON output used across multiple tests
SAMPLE_BANDIT_JSON = json.dumps(
    {
        "results": [
            {
                "filename": "app.py",
                "line_number": 10,
                "test_id": "B105",
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "Possible hardcoded password",
                "code": "secret = 'password123'\n",
            }
        ]
    }
)


class TestBanditResultFields:
    """Test BanditResult dataclass."""

    def test_bandit_result_fields(self):
        """Test BanditResult stores all fields correctly."""
        result = BanditResult(
            file="app.py",
            line=10,
            test_id="B105",
            severity="HIGH",
            confidence="HIGH",
            message="Possible hardcoded password",
            code_snippet="secret = 'password123'\n",
        )
        assert result.file == "app.py"
        assert result.line == 10
        assert result.test_id == "B105"
        assert result.severity == "HIGH"
        assert result.confidence == "HIGH"
        assert result.message == "Possible hardcoded password"
        assert result.code_snippet == "secret = 'password123'\n"

    def test_bandit_result_code_snippet_optional(self):
        """Test BanditResult code_snippet defaults to None."""
        result = BanditResult(
            file="app.py",
            line=5,
            test_id="B101",
            severity="LOW",
            confidence="HIGH",
            message="Use of assert detected",
        )
        assert result.code_snippet is None


class TestIsInstalled:
    """Test BanditAdapter.is_installed()."""

    def test_is_installed_true(self):
        """Test is_installed returns True when bandit binary is found."""
        adapter = BanditAdapter({})
        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            assert adapter.is_installed() is True

    def test_is_installed_false(self):
        """Test is_installed returns False when bandit binary is missing."""
        adapter = BanditAdapter({})
        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value=None):
            assert adapter.is_installed() is False


class TestScanEarlyReturn:
    """Test scan() early-return conditions."""

    def test_scan_returns_empty_when_not_installed(self):
        """Test scan returns empty list when Bandit is not installed."""
        adapter = BanditAdapter({"enabled": True})
        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value=None):
            results = adapter.scan(["app.py"])
        assert results == []

    def test_scan_returns_empty_when_disabled(self):
        """Test scan returns empty list when adapter is disabled."""
        adapter = BanditAdapter({"enabled": False})
        results = adapter.scan(["app.py"])
        assert results == []

    def test_scan_returns_empty_when_no_files(self):
        """Test scan returns empty list when files list is empty."""
        adapter = BanditAdapter({"enabled": True})
        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            results = adapter.scan([])
        assert results == []


class TestParseResults:
    """Test BanditAdapter._parse_results()."""

    def test_parse_results(self):
        """Test _parse_results correctly parses Bandit JSON output."""
        adapter = BanditAdapter({})
        results = adapter._parse_results(SAMPLE_BANDIT_JSON)

        assert len(results) == 1
        r = results[0]
        assert r.file == "app.py"
        assert r.line == 10
        assert r.test_id == "B105"
        assert r.severity == "HIGH"
        assert r.confidence == "HIGH"
        assert r.message == "Possible hardcoded password"
        assert r.code_snippet == "secret = 'password123'\n"

    def test_parse_results_empty(self):
        """Test _parse_results returns empty list for empty results array."""
        adapter = BanditAdapter({})
        results = adapter._parse_results(json.dumps({"results": []}))
        assert results == []

    def test_parse_results_invalid_json(self):
        """Test _parse_results returns empty list on invalid JSON."""
        adapter = BanditAdapter({})
        results = adapter._parse_results("not valid json {{{")
        assert results == []

    def test_parse_results_missing_key(self):
        """Test _parse_results returns empty list when required key is missing."""
        adapter = BanditAdapter({})
        # Missing 'filename' key
        broken = json.dumps({"results": [{"line_number": 5, "test_id": "B101"}]})
        results = adapter._parse_results(broken)
        assert results == []


class TestClassifySeverity:
    """Test classify_severity() function."""

    def test_classify_severity(self):
        """Test all 6 severity/confidence combinations."""
        # HIGH + HIGH → block
        assert classify_severity("HIGH", "HIGH") == "block"
        # HIGH + MEDIUM → block
        assert classify_severity("HIGH", "MEDIUM") == "block"
        # HIGH + LOW → warn
        assert classify_severity("HIGH", "LOW") == "warn"
        # MEDIUM + HIGH → warn
        assert classify_severity("MEDIUM", "HIGH") == "warn"
        # MEDIUM + MEDIUM → info
        assert classify_severity("MEDIUM", "MEDIUM") == "info"
        # LOW + LOW → info
        assert classify_severity("LOW", "LOW") == "info"

    def test_classify_severity_case_insensitive(self):
        """Test classify_severity handles lowercase input."""
        assert classify_severity("high", "high") == "block"
        assert classify_severity("high", "low") == "warn"
        assert classify_severity("low", "medium") == "info"


class TestBuildCommand:
    """Test BanditAdapter._build_command()."""

    def test_build_command(self):
        """Test _build_command returns correct command structure."""
        import sys

        adapter = BanditAdapter({})
        cmd = adapter._build_command(["app.py", "utils.py"])

        assert cmd[0] == sys.executable
        assert "-m" in cmd
        assert "bandit" in cmd
        assert "-ll" in cmd
        assert "-f" in cmd
        assert "json" in cmd
        assert "--quiet" in cmd
        assert "app.py" in cmd
        assert "utils.py" in cmd


class TestScanSuccess:
    """Test scan() with mocked subprocess."""

    def test_scan_success(self):
        """Test scan returns parsed results on successful subprocess call."""
        adapter = BanditAdapter({"enabled": True})

        mock_proc = MagicMock()
        mock_proc.returncode = 1  # 1 = findings present (not an error)
        mock_proc.stdout = SAMPLE_BANDIT_JSON

        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            with patch("vibesrails.adapters.bandit_adapter.subprocess.run", return_value=mock_proc):
                results = adapter.scan(["app.py"])

        assert len(results) == 1
        assert results[0].test_id == "B105"

    def test_scan_clean_exit_code_zero(self):
        """Test scan returns empty list when bandit reports no findings (exit 0)."""
        adapter = BanditAdapter({"enabled": True})

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"results": []})

        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            with patch("vibesrails.adapters.bandit_adapter.subprocess.run", return_value=mock_proc):
                results = adapter.scan(["app.py"])

        assert results == []

    def test_scan_error_exit_code(self):
        """Test scan returns empty list on exit code > 1 (bandit error)."""
        adapter = BanditAdapter({"enabled": True})

        mock_proc = MagicMock()
        mock_proc.returncode = 2

        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            with patch("vibesrails.adapters.bandit_adapter.subprocess.run", return_value=mock_proc):
                results = adapter.scan(["app.py"])

        assert results == []


class TestScanTimeout:
    """Test scan() graceful timeout handling."""

    def test_scan_timeout_graceful(self):
        """Test scan returns empty list on TimeoutExpired without raising."""
        adapter = BanditAdapter({"enabled": True})

        with patch("vibesrails.adapters.bandit_adapter.shutil.which", return_value="/usr/bin/bandit"):
            with patch(
                "vibesrails.adapters.bandit_adapter.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=60),
            ):
                results = adapter.scan(["app.py"])

        assert results == []
