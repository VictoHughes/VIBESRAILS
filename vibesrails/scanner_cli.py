"""CLI functions for vibesrails scanner."""

import logging
import re
import sys
from pathlib import Path

from .scanner_types import ScanResult

logger = logging.getLogger(__name__)


def _show_section_patterns(patterns: list[dict]) -> None:
    """Display patterns for a pro-coding section."""
    for p in patterns:
        level = p.get("level", "WARN")
        scope = f" [scope: {p['scope']}]" if p.get("scope") else ""
        skip = " (skip tests)" if p.get("skip_in_tests") else ""
        logger.info(f"  [{level}] [{p['id']}] {p['name']}{scope}{skip}")
        logger.info(f"    {p['message']}")


def show_patterns(config: dict) -> None:
    """Display all configured patterns."""
    logger.info("=== vibesrails patterns ===")

    logger.info("SECURITY (BLOCKING):")
    for p in config.get("blocking", []):
        logger.info(f"  [{p['id']}] {p['name']}")
        logger.info(f"    {p['message']}")

    logger.info("SECURITY (WARNINGS):")
    for p in config.get("warning", []):
        skip = " (skip tests)" if p.get("skip_in_tests") else ""
        logger.info(f"  [{p['id']}] {p['name']}{skip}")
        logger.info(f"    {p['message']}")

    for section, emoji, title in [
        ("bugs", "🐛", "BUGS SILENCIEUX"),
        ("architecture", "🏗️", "ARCHITECTURE"),
        ("maintainability", "🔧", "MAINTENABILITÉ"),
    ]:
        patterns = config.get(section, [])
        if patterns:
            logger.info(f"{emoji} {title}:")
            _show_section_patterns(patterns)

    logger.info("EXCEPTIONS:")
    for name, exc in config.get("exceptions", {}).items():
        logger.info(f"  {name}: {exc.get('reason', '')}")
        logger.info(f"    files: {exc['patterns']}")
        logger.info(f"    allowed: {exc['allowed']}")


def validate_config(config: dict) -> bool:
    """Validate vibesrails.yaml structure."""
    errors = []

    # Check required sections
    if "blocking" not in config:
        errors.append("Missing 'blocking' section")

    if "version" not in config:
        errors.append("Missing 'version' field")

    # Check each blocking pattern
    for i, p in enumerate(config.get("blocking", [])):
        if "id" not in p:
            errors.append(f"blocking[{i}]: missing 'id'")
        if "regex" not in p:
            errors.append(f"blocking[{i}]: missing 'regex'")
        if "message" not in p:
            errors.append(f"blocking[{i}]: missing 'message'")

        # Validate regex compiles
        try:
            re.compile(p.get("regex", ""))
        except re.error as e:
            errors.append(f"blocking[{i}]: invalid regex: {e}")

    if errors:
        logger.info("Validation errors:")
        for e in errors:
            logger.info(f"  - {e}")
        return False

    logger.info("vibesrails.yaml is valid")
    return True


def get_all_python_files() -> list[str]:
    """Get all Python files in project (excluding venv, archive, cache)."""
    exclude = [
        ".venv", "venv", "__pycache__", "_archive", "archive",
        "node_modules", ".git", "build", "dist", ".egg-info",
        ".mypy_cache", ".ruff_cache", ".pytest_cache",
    ]
    files = []
    for p in Path(".").rglob("*.py"):
        path_str = str(p)
        if not any(ex in path_str for ex in exclude):
            files.append(path_str)
    return files


def _determine_files(args) -> list[str]:
    """Determine which files to scan based on CLI args."""
    from .scanner_git import get_staged_files

    if args.file:
        return [args.file] if Path(args.file).exists() else []
    if args.all:
        return get_all_python_files()
    return get_staged_files()


def _report_results(all_results: list[ScanResult]) -> int:
    """Print scan results and return exit code."""
    blocking = [r for r in all_results if r.level == "BLOCK"]
    warnings = [r for r in all_results if r.level == "WARN"]

    for r in blocking:
        logger.info(f"BLOCK {r.file}:{r.line}")
        logger.info(f"  [{r.pattern_id}] {r.message}")
    for r in warnings:
        logger.info(f"WARN {r.file}:{r.line}")
        logger.info(f"  [{r.pattern_id}] {r.message}")

    logger.info("=" * 30)
    logger.info(f"BLOCKING: {len(blocking)} | WARNINGS: {len(warnings)}")

    if blocking:
        logger.info("Fix blocking issues before committing.")
        return 1
    logger.info("vibesrails: PASSED")
    return 0


def main() -> None:
    """CLI entry point."""
    import argparse

    from .scanner import load_config, scan_file

    parser = argparse.ArgumentParser(description="vibesrails - Scale up your vibe coding safely")
    parser.add_argument("--validate", action="store_true", help="Validate YAML config")
    parser.add_argument("--show", action="store_true", help="Show all patterns")
    parser.add_argument("--all", action="store_true", help="Scan all Python files")
    parser.add_argument("--file", "-f", help="Scan specific file")
    args = parser.parse_args()

    config = load_config()

    if args.validate:
        sys.exit(0 if validate_config(config) else 1)
    if args.show:
        show_patterns(config)
        sys.exit(0)

    files = _determine_files(args)
    logger.info("vibesrails - Security Scan")
    logger.info("=" * 30)

    if not files:
        logger.info("No Python files to scan")
        sys.exit(0)
    logger.info(f"Scanning {len(files)} file(s)...")

    all_results = []
    for filepath in files:
        all_results.extend(scan_file(filepath, config))

    sys.exit(_report_results(all_results))
