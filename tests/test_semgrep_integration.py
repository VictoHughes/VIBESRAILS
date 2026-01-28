"""
Tests for Semgrep integration.

Tests SemgrepAdapter, ResultMerger, and CLI orchestration.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from vibesrails.result_merger import ResultMerger, UnifiedResult
from vibesrails.scanner import ScanResult
from vibesrails.semgrep_adapter import SemgrepAdapter, SemgrepResult


class TestSemgrepAdapter:
    """Test SemgrepAdapter functionality."""

    def test_is_installed_when_available(self):
        """Test is_installed returns True when semgrep is available."""
        with patch("shutil.which", return_value="/usr/bin/semgrep"):
            adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
            assert adapter.is_installed() is True

    def test_is_installed_when_not_available(self):
        """Test is_installed returns False when semgrep is not available."""
        with patch("shutil.which", return_value=None):
            adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
            assert adapter.is_installed() is False

    def test_get_config_flag_auto(self):
        """Test _get_config_flag returns 'auto' for auto preset."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
        assert adapter._get_config_flag() == "auto"

    def test_get_config_flag_strict(self):
        """Test _get_config_flag returns correct flag for strict preset."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "strict"})
        assert adapter._get_config_flag() == "p/security-audit"

    def test_get_config_flag_minimal(self):
        """Test _get_config_flag returns correct flag for minimal preset."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "minimal"})
        assert adapter._get_config_flag() == "p/secrets"

    def test_parse_results_valid_json(self):
        """Test _parse_results correctly parses Semgrep JSON output."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})

        # Example Semgrep output (test data only)  # vibesrails: ignore
        json_output = json.dumps({
            "results": [
                {
                    "path": "test.py",
                    "start": {"line": 10},
                    "check_id": "python.lang.security.dangerous-system-call",
                    "extra": {
                        "message": "Dangerous system call",
                        "severity": "ERROR",
                        "lines": "unsafe_call(user_input)"  # Test example
                    }
                }
            ]
        })

        results = adapter._parse_results(json_output)
        assert len(results) == 1
        assert results[0].file == "test.py"
        assert results[0].line == 10
        assert results[0].rule_id == "python.lang.security.dangerous-system-call"
        assert results[0].severity == "ERROR"
        assert results[0].message == "Dangerous system call"

    def test_parse_results_invalid_json(self):
        """Test _parse_results returns empty list on invalid JSON."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
        results = adapter._parse_results("invalid json")
        assert results == []

    def test_scan_when_not_installed(self):
        """Test scan returns empty list when Semgrep not installed."""
        with patch("shutil.which", return_value=None):
            adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
            results = adapter.scan(["test.py"])
            assert results == []

    def test_scan_when_disabled(self):
        """Test scan returns empty list when Semgrep disabled."""
        adapter = SemgrepAdapter({"enabled": False, "preset": "auto"})
        results = adapter.scan(["test.py"])
        assert results == []

    def test_scan_with_no_files(self):
        """Test scan returns empty list when no files provided."""
        adapter = SemgrepAdapter({"enabled": True, "preset": "auto"})
        results = adapter.scan([])
        assert results == []


class TestResultMerger:
    """Test ResultMerger functionality."""

    def test_merge_empty_results(self):
        """Test merge with no results."""
        merger = ResultMerger()
        unified, stats = merger.merge([], [])

        assert unified == []
        assert stats["semgrep"] == 0
        assert stats["vibesrails"] == 0
        assert stats["duplicates"] == 0
        assert stats["total"] == 0

    def test_merge_semgrep_only(self):
        """Test merge with only Semgrep results."""
        merger = ResultMerger()
        semgrep_results = [
            SemgrepResult(
                file="test.py",
                line=10,
                rule_id="python.lang.security.dangerous-system-call",
                message="Dangerous system call",
                severity="ERROR"
            )
        ]

        unified, stats = merger.merge(semgrep_results, [])

        assert len(unified) == 1
        assert stats["semgrep"] == 1
        assert stats["vibesrails"] == 0
        assert stats["total"] == 1
        assert unified[0].source == "SEMGREP"
        assert unified[0].level == "BLOCK"

    def test_merge_vibesrails_only(self):
        """Test merge with only VibesRails results."""
        merger = ResultMerger()
        vibesrails_results = [
            ScanResult(
                file="test.py",
                line=15,
                pattern_id="dip_domain_infra",
                message="Domain imports infrastructure",
                level="BLOCK"
            )
        ]

        unified, stats = merger.merge([], vibesrails_results)

        assert len(unified) == 1
        assert stats["semgrep"] == 0
        assert stats["vibesrails"] == 1
        assert stats["total"] == 1
        assert unified[0].source == "VIBESRAILS"
        assert unified[0].level == "BLOCK"

    def test_merge_deduplication(self):
        """Test merge deduplicates results by (file, line)."""
        merger = ResultMerger()

        semgrep_results = [
            SemgrepResult(
                file="test.py",
                line=10,
                rule_id="python.lang.security.hardcoded-secret",
                message="Hardcoded secret",
                severity="ERROR"
            )
        ]

        vibesrails_results = [
            ScanResult(
                file="test.py",
                line=10,  # Same file and line
                pattern_id="hardcoded_secret",
                message="Hardcoded secret detected",
                level="BLOCK"
            )
        ]

        unified, stats = merger.merge(semgrep_results, vibesrails_results)

        # Should keep only Semgrep result (priority)
        assert len(unified) == 1
        assert stats["semgrep"] == 1
        assert stats["vibesrails"] == 0
        assert stats["duplicates"] == 1
        assert unified[0].source == "SEMGREP"

    def test_map_severity(self):
        """Test _map_severity correctly maps Semgrep severity to VibesRails level."""
        merger = ResultMerger()

        assert merger._map_severity("ERROR") == "BLOCK"
        assert merger._map_severity("WARNING") == "WARN"
        assert merger._map_severity("INFO") == "INFO"
        assert merger._map_severity("UNKNOWN") == "WARN"  # Default

    def test_categorize_semgrep(self):
        """Test _categorize_semgrep correctly categorizes Semgrep rules."""
        merger = ResultMerger()

        assert merger._categorize_semgrep("python.lang.security.dangerous-call") == "security"
        assert merger._categorize_semgrep("python.lang.bug.null-pointer") == "bugs"
        assert merger._categorize_semgrep("python.lang.performance.slow-loop") == "general"

    def test_categorize_vibesrails(self):
        """Test _categorize_vibesrails correctly categorizes VibesRails patterns."""
        merger = ResultMerger()

        assert merger._categorize_vibesrails("dip_domain_infra") == "architecture"
        assert merger._categorize_vibesrails("guardian_ai_session") == "guardian"
        assert merger._categorize_vibesrails("hardcoded_secret") == "security"
        assert merger._categorize_vibesrails("complexity_check") == "general"

    def test_group_by_category(self):
        """Test group_by_category correctly groups results."""
        merger = ResultMerger()

        results = [
            UnifiedResult(
                file="test.py",
                line=10,
                source="SEMGREP",
                rule_id="security-rule",
                message="Security issue",
                level="BLOCK",
                category="security"
            ),
            UnifiedResult(
                file="test.py",
                line=20,
                source="VIBESRAILS",
                rule_id="arch-rule",
                message="Architecture issue",
                level="BLOCK",
                category="architecture"
            ),
            UnifiedResult(
                file="test.py",
                line=30,
                source="SEMGREP",
                rule_id="another-security-rule",
                message="Another security issue",
                level="WARN",
                category="security"
            )
        ]

        groups = merger.group_by_category(results)

        assert len(groups) == 2
        assert len(groups["security"]) == 2
        assert len(groups["architecture"]) == 1

    def test_get_blocking_count(self):
        """Test get_blocking_count correctly counts blocking issues."""
        merger = ResultMerger()

        results = [
            UnifiedResult("test.py", 10, "SEMGREP", "rule1", "msg", "BLOCK", "security"),
            UnifiedResult("test.py", 20, "VIBESRAILS", "rule2", "msg", "WARN", "security"),
            UnifiedResult("test.py", 30, "SEMGREP", "rule3", "msg", "BLOCK", "bugs"),
        ]

        assert merger.get_blocking_count(results) == 2

    def test_get_warning_count(self):
        """Test get_warning_count correctly counts warning issues."""
        merger = ResultMerger()

        results = [
            UnifiedResult("test.py", 10, "SEMGREP", "rule1", "msg", "BLOCK", "security"),
            UnifiedResult("test.py", 20, "VIBESRAILS", "rule2", "msg", "WARN", "security"),
            UnifiedResult("test.py", 30, "SEMGREP", "rule3", "msg", "WARN", "bugs"),
        ]

        assert merger.get_warning_count(results) == 2


class TestCLIOrchestration:
    """Test CLI orchestration of Semgrep + VibesRails."""

    @patch("vibesrails.guardian.should_apply_guardian", return_value=False)
    @patch("vibesrails.guardian.print_guardian_status")
    @patch("vibesrails.scan_runner.scan_file")
    @patch("vibesrails.semgrep_adapter.SemgrepAdapter")
    def test_run_scan_with_semgrep_available(
        self, mock_semgrep_class, mock_scan_file, mock_print_guardian, mock_should_guardian
    ):
        """Test run_scan orchestrates both scanners when Semgrep available."""
        from vibesrails.scan_runner import run_scan

        # Mock Semgrep adapter
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.is_installed.return_value = True
        mock_adapter.scan.return_value = []
        mock_semgrep_class.return_value = mock_adapter

        # Mock VibesRails scanner
        mock_scan_file.return_value = []

        config = {"semgrep": {"enabled": True, "preset": "auto"}}
        files = ["test.py"]

        exit_code = run_scan(config, files)

        # Verify both scanners were called
        mock_adapter.scan.assert_called_once_with(files)
        mock_scan_file.assert_called()
        assert exit_code == 0

    @patch("vibesrails.guardian.should_apply_guardian", return_value=False)
    @patch("vibesrails.guardian.print_guardian_status")
    @patch("vibesrails.scan_runner.scan_file")
    @patch("vibesrails.semgrep_adapter.SemgrepAdapter")
    def test_run_scan_graceful_degradation(
        self, mock_semgrep_class, mock_scan_file, mock_print_guardian, mock_should_guardian
    ):
        """Test run_scan works with only VibesRails when Semgrep unavailable."""
        from vibesrails.scan_runner import run_scan

        # Mock Semgrep adapter (not installed)
        mock_adapter = MagicMock()
        mock_adapter.enabled = True
        mock_adapter.is_installed.return_value = False
        mock_adapter.install.return_value = False  # Install fails
        mock_semgrep_class.return_value = mock_adapter

        # Mock VibesRails scanner
        mock_scan_file.return_value = []

        config = {"semgrep": {"enabled": True, "preset": "auto"}}
        files = ["test.py"]

        exit_code = run_scan(config, files)

        # Verify only VibesRails scanner was called
        mock_scan_file.assert_called()
        assert exit_code == 0
