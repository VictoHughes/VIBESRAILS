#!/usr/bin/env python3
"""
Semgrep adapter for VibesRails.

Provides a clean interface to Semgrep CLI with robust error handling.
Supports auto-install, preset configurations, and graceful degradation.
"""

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SemgrepResult:
    """Normalized Semgrep result."""
    file: str
    line: int
    rule_id: str
    message: str
    severity: str  # ERROR | WARNING | INFO
    code_snippet: Optional[str] = None


class SemgrepAdapter:
    """Interface to Semgrep CLI."""

    def __init__(self, config: dict):
        """
        Initialize Semgrep adapter.

        Args:
            config: Semgrep configuration from vibesrails.yaml
                   Expected keys: preset, additional_rules, exclude_rules
        """
        self.enabled = config.get("enabled", True)
        self.preset = config.get("preset", "auto")
        self.additional_rules = config.get("additional_rules", [])
        self.exclude_rules = config.get("exclude_rules", [])

    def is_installed(self) -> bool:
        """Check if Semgrep is installed and accessible."""
        return shutil.which("semgrep") is not None

    def install(self, quiet: bool = True) -> bool:
        """
        Install Semgrep via pip.

        Args:
            quiet: If True, suppress pip output

        Returns:
            True if installation successful, False otherwise
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install", "semgrep"]
            if quiet:
                cmd.append("-q")

            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=300  # 5 min timeout
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def ensure_installed(self) -> bool:
        """
        Ensure Semgrep is installed, install if needed.

        Returns:
            True if Semgrep is available, False otherwise
        """
        if self.is_installed():
            return True

        logger.info("Installing Semgrep (first time setup)...")
        success = self.install()

        if success:
            logger.info("Semgrep installed successfully")
            return True
        else:
            logger.warning("Failed to install Semgrep, continuing with VibesRails only")
            return False

    def _build_command(self, files: List[str]) -> List[str]:
        """Build the Semgrep command line."""
        cmd = ["semgrep", "--config", self._get_config_flag(), "--json", "--quiet", "--no-git-ignore"]
        for rule in self.additional_rules:
            cmd.extend(["--config", rule])
        for rule in self.exclude_rules:
            cmd.extend(["--exclude-rule", rule])
        cmd.extend(files)
        return cmd

    def scan(self, files: List[str]) -> List[SemgrepResult]:
        """Scan files with Semgrep. Returns empty list if unavailable."""
        if not self.enabled or not self.is_installed() or not files:
            return []

        try:
            result = subprocess.run(
                self._build_command(files),
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode > 1:
                return []
            return self._parse_results(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            logger.warning("Semgrep scan failed or timed out")
            return []

    def _get_config_flag(self) -> str:
        """
        Get Semgrep --config flag based on preset.

        Returns:
            Config string for Semgrep CLI
        """
        presets = {
            "auto": "auto",
            "strict": "p/security-audit",
            "minimal": "p/secrets",
        }
        return presets.get(self.preset, "auto")

    def _parse_results(self, json_output: str) -> List[SemgrepResult]:
        """
        Parse Semgrep JSON output into normalized results.

        Args:
            json_output: JSON string from Semgrep

        Returns:
            List of SemgrepResult objects
        """
        try:
            data = json.loads(json_output)
            results = []

            for finding in data.get("results", []):
                # Extract code snippet if available
                code_snippet = None
                if "extra" in finding and "lines" in finding["extra"]:
                    code_snippet = finding["extra"]["lines"]

                results.append(SemgrepResult(
                    file=finding["path"],
                    line=finding["start"]["line"],
                    rule_id=finding["check_id"],
                    message=finding["extra"]["message"],
                    severity=finding["extra"]["severity"].upper(),
                    code_snippet=code_snippet
                ))

            return results

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fail gracefully on parse errors
            return []

    def get_version(self) -> Optional[str]:
        """
        Get installed Semgrep version.

        Returns:
            Version string or None if not installed
        """
        if not self.is_installed():
            return None

        try:
            result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
