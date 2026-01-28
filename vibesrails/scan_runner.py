"""Scan execution logic for VibesRails.

Orchestrates Semgrep + VibesRails scanning and result merging.
"""

import time

from .ai_guardian import (
    apply_guardian_rules,
    get_ai_agent_name,
    log_guardian_block,
    print_guardian_status,
    should_apply_guardian,
)
from .metrics import track_scan
from .result_merger import ResultMerger
from .scanner import BLUE, GREEN, NC, RED, YELLOW, ScanResult, scan_file
from .semgrep_adapter import SemgrepAdapter


def run_scan(config: dict, files: list[str]) -> int:
    """Run scan with Semgrep + VibesRails orchestration and return exit code."""
    start_time = time.time()

    print(f"{BLUE}VibesRails - Security Scan{NC}")
    print("=" * 30)

    print_guardian_status(config)

    if not files:
        print(f"{GREEN}No Python files to scan{NC}")
        return 0

    print(f"Scanning {len(files)} file(s)...\n")

    # Initialize Semgrep adapter
    semgrep_config = config.get("semgrep", {"enabled": True, "preset": "auto"})
    semgrep = SemgrepAdapter(semgrep_config)

    # Ensure Semgrep is installed (auto-install if needed)
    semgrep_available = False
    if semgrep.enabled:
        if not semgrep.is_installed():
            print("📦 Installing Semgrep (enhanced scanning)...")
            semgrep_available = semgrep.install(quiet=False)
            if semgrep_available:
                print(f"{GREEN}✅ Semgrep installed{NC}\n")
            else:
                print(f"{YELLOW}⚠️  Semgrep install failed, continuing with VibesRails only{NC}\n")
        else:
            semgrep_available = True

    # Run Semgrep scan (if available)
    semgrep_results = []
    if semgrep_available and semgrep.enabled:
        print("🔍 Running Semgrep scan...")
        semgrep_results = semgrep.scan(files)
        print(f"   Found {len(semgrep_results)} issue(s)")

    # Run VibesRails scan
    print("🔍 Running VibesRails scan...")
    vibesrails_results = []
    guardian_active = should_apply_guardian(config)
    agent_name = get_ai_agent_name() if guardian_active else None

    for filepath in files:
        results = scan_file(filepath, config)

        if guardian_active:
            results = apply_guardian_rules(results, config, filepath)

        vibesrails_results.extend(results)

    print(f"   Found {len(vibesrails_results)} issue(s)\n")

    # Merge results
    merger = ResultMerger()
    unified_results, stats = merger.merge(semgrep_results, vibesrails_results)

    # Display statistics
    if semgrep_results or vibesrails_results:
        print(f"{BLUE}📊 Scan Statistics:{NC}")
        print(f"   Semgrep:     {stats['semgrep']} issues")
        print(f"   VibesRails:  {stats['vibesrails']} issues")
        if stats['duplicates'] > 0:
            print(f"   Duplicates:  {stats['duplicates']} (merged)")
        print(f"   Total:       {stats['total']} unique issues\n")

    # Categorize and display results
    blocking = [r for r in unified_results if r.level == "BLOCK"]
    warnings = [r for r in unified_results if r.level == "WARN"]

    _display_results(merger, unified_results, guardian_active, agent_name)

    print("=" * 30)
    print(f"BLOCKING: {len(blocking)} | WARNINGS: {len(warnings)}")

    exit_code = 1 if blocking else 0

    # Track metrics
    duration_ms = int((time.time() - start_time) * 1000)
    track_scan(
        duration_ms=duration_ms,
        files_scanned=len(files),
        semgrep_enabled=semgrep.enabled and semgrep_available,
        semgrep_issues=len(semgrep_results),
        vibesrails_issues=len(vibesrails_results),
        duplicates=stats.get('duplicates', 0),
        total_issues=len(unified_results),
        blocking_issues=len(blocking),
        warnings=len(warnings),
        exit_code=exit_code,
        guardian_active=guardian_active,
    )

    if blocking:
        print(f"\n{RED}Fix blocking issues or use: git commit --no-verify{NC}")
        return 1

    print(f"\n{GREEN}VibesRails: PASSED{NC}")
    return 0


def _display_results(merger: ResultMerger, unified_results: list, guardian_active: bool, agent_name: str | None) -> None:
    """Display categorized scan results."""
    categories = merger.group_by_category(unified_results)

    for category, results in categories.items():
        category_emoji = {
            "security": "🔒",
            "architecture": "🏗️",
            "guardian": "🛡️",
            "bugs": "🐛",
            "general": "⚙️"
        }.get(category, "•")

        print(f"{BLUE}{category_emoji} {category.upper()}:{NC}")
        for r in results:
            color = RED if r.level == "BLOCK" else YELLOW
            level_text = f"{color}{r.level}{NC}"
            source_badge = f"[{r.source}]"

            print(f"{level_text} {r.file}:{r.line} {source_badge}")
            print(f"  [{r.rule_id}] {r.message}")

            if guardian_active and r.level == "BLOCK" and r.source == "VIBESRAILS":
                scan_result = ScanResult(
                    file=r.file,
                    line=r.line,
                    pattern_id=r.rule_id,
                    message=r.message,
                    level=r.level
                )
                log_guardian_block(scan_result, agent_name)
        print()
