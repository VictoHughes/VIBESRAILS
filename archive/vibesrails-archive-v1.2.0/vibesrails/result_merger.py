#!/usr/bin/env python3
"""
Result merger for VibesRails + Semgrep integration.

Merges and deduplicates results from both scanners, providing a unified view
with source attribution and statistics.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .scanner import ScanResult
from .semgrep_adapter import SemgrepResult

logger = logging.getLogger(__name__)


@dataclass
class UnifiedResult:
    """Unified result after merging Semgrep + VibesRails."""
    file: str
    line: int
    source: str  # "SEMGREP" | "VIBESRAILS"
    rule_id: str
    message: str
    level: str  # "BLOCK" | "WARN" | "INFO"
    category: str  # "security" | "architecture" | "guardian" | "bugs" | "general"
    code_snippet: str = ""


class ResultMerger:
    """Merges results from Semgrep and VibesRails with intelligent deduplication."""

    def _convert_semgrep(self, result: SemgrepResult) -> UnifiedResult:
        """Convert a SemgrepResult to UnifiedResult."""
        return UnifiedResult(
            file=result.file, line=result.line, source="SEMGREP",
            rule_id=result.rule_id, message=result.message,
            level=self._map_severity(result.severity),
            category=self._categorize_semgrep(result.rule_id),
            code_snippet=result.code_snippet or "",
        )

    def _convert_vibesrails(self, result: ScanResult) -> UnifiedResult:
        """Convert a ScanResult to UnifiedResult."""
        return UnifiedResult(
            file=result.file, line=result.line, source="VIBESRAILS",
            rule_id=result.pattern_id, message=result.message,
            level=result.level,
            category=self._categorize_vibesrails(result.pattern_id),
        )

    def merge(
        self,
        semgrep_results: List[SemgrepResult],
        vibesrails_results: List[ScanResult],
    ) -> Tuple[List[UnifiedResult], Dict[str, int]]:
        """Merge results from both scanners with deduplication."""
        unified = []
        seen: set[tuple] = set()
        stats = {"semgrep": 0, "vibesrails": 0, "duplicates": 0, "total": 0}

        for source_key, results, converter in [
            ("semgrep", semgrep_results, self._convert_semgrep),
            ("vibesrails", vibesrails_results, self._convert_vibesrails),
        ]:
            for result in results:
                key = (result.file, result.line)
                if key in seen:
                    stats["duplicates"] += 1
                    continue
                unified.append(converter(result))
                seen.add(key)
                stats[source_key] += 1

        unified.sort(key=lambda r: (r.file, r.line))
        stats["total"] = len(unified)
        return unified, stats

    def _map_severity(self, semgrep_severity: str) -> str:
        """
        Map Semgrep severity to VibesRails level.

        Args:
            semgrep_severity: Semgrep severity (ERROR, WARNING, INFO)

        Returns:
            VibesRails level (BLOCK, WARN, INFO)
        """
        mapping = {
            "ERROR": "BLOCK",
            "WARNING": "WARN",
            "INFO": "INFO"
        }
        return mapping.get(semgrep_severity, "WARN")

    def _categorize_semgrep(self, rule_id: str) -> str:
        """
        Categorize Semgrep rule by ID.

        Args:
            rule_id: Semgrep rule ID (e.g., "python.lang.security.dangerous-system-call")

        Returns:
            Category string
        """
        rule_lower = rule_id.lower()

        if "security" in rule_lower or "secret" in rule_lower:
            return "security"
        if "bug" in rule_lower or "correctness" in rule_lower:
            return "bugs"
        if "performance" in rule_lower or "best-practice" in rule_lower:
            return "general"

        return "general"

    def _categorize_vibesrails(self, pattern_id: str) -> str:
        """
        Categorize VibesRails pattern by ID.

        Args:
            pattern_id: VibesRails pattern ID (e.g., "dip_domain_infra")

        Returns:
            Category string
        """
        pattern_lower = pattern_id.lower()

        if "dip" in pattern_lower or "layer" in pattern_lower or "architecture" in pattern_lower:
            return "architecture"
        if "guardian" in pattern_lower or "ai" in pattern_lower:
            return "guardian"
        if "secret" in pattern_lower or "sql" in pattern_lower:
            return "security"
        if "complexity" in pattern_lower or "maintainability" in pattern_lower:
            return "general"

        return "security"  # Default to security

    def group_by_category(self, results: List[UnifiedResult]) -> Dict[str, List[UnifiedResult]]:
        """
        Group results by category for organized display.

        Args:
            results: List of unified results

        Returns:
            Dictionary mapping category -> results
        """
        groups = {}
        for result in results:
            if result.category not in groups:
                groups[result.category] = []
            groups[result.category].append(result)

        return groups

    def get_blocking_count(self, results: List[UnifiedResult]) -> int:
        """Count blocking issues."""
        return sum(1 for r in results if r.level == "BLOCK")

    def get_warning_count(self, results: List[UnifiedResult]) -> int:
        """Count warning issues."""
        return sum(1 for r in results if r.level == "WARN")
