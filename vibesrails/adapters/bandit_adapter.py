#!/usr/bin/env python3
"""
Bandit SAST adapter for VibesRails.

Provides a clean interface to Bandit CLI with robust error handling.
Supports severity classification and graceful degradation.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BanditResult:
    """Normalized Bandit result."""

    file: str
    line: int
    test_id: str
    severity: str  # HIGH | MEDIUM | LOW
    confidence: str  # HIGH | MEDIUM | LOW
    message: str
    code_snippet: str | None = None


def classify_severity(severity: str, confidence: str) -> str:
    """
    Classify a Bandit finding into a VibesRails action level.

    Args:
        severity: Bandit issue_severity (HIGH | MEDIUM | LOW)
        confidence: Bandit issue_confidence (HIGH | MEDIUM | LOW)

    Returns:
        "block" | "warn" | "info"
    """
    severity = severity.upper()
    confidence = confidence.upper()

    if severity == "HIGH" and confidence in ("HIGH", "MEDIUM"):
        return "block"
    if (severity == "HIGH" and confidence == "LOW") or (
        severity == "MEDIUM" and confidence == "HIGH"
    ):
        return "warn"
    return "info"


class BanditAdapter:
    """Interface to Bandit SAST CLI."""

    def __init__(self, config: dict):
        """
        Initialize Bandit adapter.

        Args:
            config: Bandit configuration from vibesrails.yaml
                   Expected keys: enabled, severity_filter
        """
        self.enabled = config.get("enabled", True)
        self.severity_filter = config.get("severity_filter", "low")

    def is_installed(self) -> bool:
        """Check if Bandit is installed and accessible."""
        return shutil.which("bandit") is not None

    def _build_command(self, files: list[str]) -> list[str]:
        """Build the Bandit command line."""
        return [
            sys.executable,
            "-m",
            "bandit",
            "-ll",
            "-f",
            "json",
            "--quiet",
            *files,
        ]

    def scan(self, files: list[str]) -> list[BanditResult]:
        """Scan files with Bandit. Returns empty list if unavailable."""
        if not self.enabled or not self.is_installed() or not files:
            return []

        try:
            result = subprocess.run(
                self._build_command(files),
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Bandit exit codes: 0=clean, 1=findings, >1=error
            if result.returncode > 1:
                logger.warning("Bandit exited with error code %d", result.returncode)
                return []
            return self._parse_results(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning("Bandit scan timed out")
            return []
        except subprocess.CalledProcessError:
            logger.warning("Bandit scan failed")
            return []

    def _parse_results(self, json_output: str) -> list[BanditResult]:
        """
        Parse Bandit JSON output into normalized results.

        Args:
            json_output: JSON string from Bandit

        Returns:
            List of BanditResult objects
        """
        try:
            data = json.loads(json_output)
            results = []

            for finding in data.get("results", []):
                results.append(
                    BanditResult(
                        file=finding["filename"],
                        line=finding["line_number"],
                        test_id=finding["test_id"],
                        severity=finding["issue_severity"],
                        confidence=finding["issue_confidence"],
                        message=finding["issue_text"],
                        code_snippet=finding.get("code"),
                    )
                )

            return results

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fail gracefully on parse errors
            return []
