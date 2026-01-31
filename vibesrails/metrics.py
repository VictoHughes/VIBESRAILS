#!/usr/bin/env python3
"""
Metrics collection for VibesRails.

Tracks usage, performance, and effectiveness metrics locally.
No telemetry - all data stays on user's machine.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ScanMetrics:
    """Metrics for a single scan."""
    timestamp: str
    duration_ms: int
    files_scanned: int
    semgrep_enabled: bool
    semgrep_issues: int
    vibesrails_issues: int
    duplicates: int
    total_issues: int
    blocking_issues: int
    warnings: int
    exit_code: int
    guardian_active: bool


class MetricsCollector:
    """Collects and stores metrics locally."""

    def __init__(self, metrics_dir: Path | None = None):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory to store metrics (default: .vibesrails/metrics/)
        """
        if metrics_dir is None:
            metrics_dir = Path.cwd() / ".vibesrails" / "metrics"

        self.metrics_dir = metrics_dir
        self._initialized = False
        self.metrics_file: Path | None = None

    def _ensure_initialized(self) -> bool:
        """Initialize metrics directory with symlink protection (TOCTOU-safe)."""
        if self._initialized:
            return self.metrics_file is not None

        try:
            # Symlink protection: verify directory is under cwd
            cwd = Path.cwd().resolve()
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            metrics_dir_resolved = self.metrics_dir.resolve()

            # Check for symlink attack - directory must be under cwd
            metrics_dir_resolved.relative_to(cwd)

            self.metrics_file = metrics_dir_resolved / "scans.jsonl"
            self._initialized = True
            return True
        except (ValueError, OSError):
            # Symlink attack detected or permission error
            self._initialized = True
            self.metrics_file = None
            return False

    def record_scan(self, metrics: ScanMetrics) -> None:
        """Record a scan's metrics."""
        if not self._ensure_initialized() or self.metrics_file is None:
            return  # Silently skip if symlink attack detected

        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")

    def get_all_scans(self) -> List[ScanMetrics]:
        """Load all recorded scans."""
        if not self._ensure_initialized() or self.metrics_file is None:
            return []

        if not self.metrics_file.exists():
            return []

        scans = []
        with open(self.metrics_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    scans.append(ScanMetrics(**data))
        return scans

    def get_stats(self) -> Dict:
        """Get aggregate statistics."""
        scans = self.get_all_scans()

        if not scans:
            return {"total_scans": 0}

        # Calculate averages
        total_scans = len(scans)
        avg_duration = sum(s.duration_ms for s in scans) / total_scans
        avg_issues = sum(s.total_issues for s in scans) / total_scans

        # Count Semgrep usage
        semgrep_scans = sum(1 for s in scans if s.semgrep_enabled)
        semgrep_usage_rate = (semgrep_scans / total_scans) * 100

        # Count blocks vs passes
        blocked_scans = sum(1 for s in scans if s.exit_code != 0)
        block_rate = (blocked_scans / total_scans) * 100

        # Guardian stats
        guardian_scans = sum(1 for s in scans if s.guardian_active)
        guardian_usage_rate = (guardian_scans / total_scans) * 100

        # Effectiveness (issues found per scan)
        effectiveness = {
            "semgrep_avg": sum(s.semgrep_issues for s in scans) / total_scans,
            "vibesrails_avg": sum(s.vibesrails_issues for s in scans) / total_scans,
            "duplicates_avg": sum(s.duplicates for s in scans) / total_scans,
        }

        return {
            "total_scans": total_scans,
            "avg_duration_ms": round(avg_duration, 2),
            "avg_issues_per_scan": round(avg_issues, 2),
            "semgrep_usage_rate": round(semgrep_usage_rate, 2),
            "block_rate": round(block_rate, 2),
            "guardian_usage_rate": round(guardian_usage_rate, 2),
            "effectiveness": effectiveness,
            "last_scan": scans[-1].timestamp if scans else None,
        }

    def show_stats(self) -> None:
        """Display statistics in terminal."""
        from .scanner import BLUE, NC, YELLOW

        stats = self.get_stats()

        if stats["total_scans"] == 0:
            logger.info("%sNo scans recorded yet%s", YELLOW, NC)
            return

        logger.info("\n%s📊 VibesRails Statistics%s", BLUE, NC)
        logger.info("=" * 50)
        logger.info("Total scans: %s", stats['total_scans'])
        logger.info("Average duration: %sms", stats['avg_duration_ms'])
        logger.info("Average issues per scan: %s", stats['avg_issues_per_scan'])
        logger.info("Block rate: %s%%", stats['block_rate'])
        logger.info("")
        logger.info("%sIntegration Usage:%s", BLUE, NC)
        logger.info("  Semgrep: %s%%", stats['semgrep_usage_rate'])
        logger.info("  Guardian Mode: %s%%", stats['guardian_usage_rate'])
        logger.info("")
        logger.info("%sEffectiveness:%s", BLUE, NC)
        eff = stats['effectiveness']
        logger.info("  Semgrep avg: %.1f issues/scan", eff['semgrep_avg'])
        logger.info("  VibesRails avg: %.1f issues/scan", eff['vibesrails_avg'])
        logger.info("  Duplicates avg: %.1f/scan", eff['duplicates_avg'])
        logger.info("")
        logger.info("Last scan: %s", stats['last_scan'])
        logger.info("=" * 50)


@dataclass
class ScanTrackingData:
    """Groups scan tracking parameters."""
    duration_ms: int
    files_scanned: int
    semgrep_enabled: bool
    semgrep_issues: int
    vibesrails_issues: int
    duplicates: int
    total_issues: int
    blocking_issues: int
    warnings: int
    exit_code: int
    guardian_active: bool


def track_scan(*, data: ScanTrackingData) -> None:
    """Track a scan's metrics. Call this after each scan completes."""
    d = data
    collector = MetricsCollector()
    metrics = ScanMetrics(
        timestamp=datetime.now().isoformat(),
        duration_ms=d.duration_ms,
        files_scanned=d.files_scanned,
        semgrep_enabled=d.semgrep_enabled,
        semgrep_issues=d.semgrep_issues,
        vibesrails_issues=d.vibesrails_issues,
        duplicates=d.duplicates,
        total_issues=d.total_issues,
        blocking_issues=d.blocking_issues,
        warnings=d.warnings,
        exit_code=d.exit_code,
        guardian_active=d.guardian_active,
    )
    collector.record_scan(metrics)
