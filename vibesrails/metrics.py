#!/usr/bin/env python3
"""
Metrics collection for VibesRails.

Tracks usage, performance, and effectiveness metrics locally.
No telemetry - all data stays on user's machine.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


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
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "scans.jsonl"

    def record_scan(self, metrics: ScanMetrics) -> None:
        """Record a scan's metrics."""
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")

    def get_all_scans(self) -> List[ScanMetrics]:
        """Load all recorded scans."""
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
        from .scanner import BLUE, GREEN, YELLOW, NC

        stats = self.get_stats()

        if stats["total_scans"] == 0:
            print(f"{YELLOW}No scans recorded yet{NC}")
            return

        print(f"\n{BLUE}📊 VibesRails Statistics{NC}")
        print("=" * 50)
        print(f"Total scans: {stats['total_scans']}")
        print(f"Average duration: {stats['avg_duration_ms']}ms")
        print(f"Average issues per scan: {stats['avg_issues_per_scan']}")
        print(f"Block rate: {stats['block_rate']}%")
        print()
        print(f"{BLUE}Integration Usage:{NC}")
        print(f"  Semgrep: {stats['semgrep_usage_rate']}%")
        print(f"  Guardian Mode: {stats['guardian_usage_rate']}%")
        print()
        print(f"{BLUE}Effectiveness:{NC}")
        eff = stats['effectiveness']
        print(f"  Semgrep avg: {eff['semgrep_avg']:.1f} issues/scan")
        print(f"  VibesRails avg: {eff['vibesrails_avg']:.1f} issues/scan")
        print(f"  Duplicates avg: {eff['duplicates_avg']:.1f}/scan")
        print()
        print(f"Last scan: {stats['last_scan']}")
        print("=" * 50)


def track_scan(
    duration_ms: int,
    files_scanned: int,
    semgrep_enabled: bool,
    semgrep_issues: int,
    vibesrails_issues: int,
    duplicates: int,
    total_issues: int,
    blocking_issues: int,
    warnings: int,
    exit_code: int,
    guardian_active: bool,
) -> None:
    """
    Track a scan's metrics.

    Call this after each scan completes.
    """
    collector = MetricsCollector()

    metrics = ScanMetrics(
        timestamp=datetime.now().isoformat(),
        duration_ms=duration_ms,
        files_scanned=files_scanned,
        semgrep_enabled=semgrep_enabled,
        semgrep_issues=semgrep_issues,
        vibesrails_issues=vibesrails_issues,
        duplicates=duplicates,
        total_issues=total_issues,
        blocking_issues=blocking_issues,
        warnings=warnings,
        exit_code=exit_code,
        guardian_active=guardian_active,
    )

    collector.record_scan(metrics)
