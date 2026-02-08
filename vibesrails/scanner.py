#!/usr/bin/env python3
"""
vibesrails - Security scanner driven by config/vibesrails.yaml

Single source of truth for security patterns. This script:
1. Reads patterns from vibesrails.yaml
2. Scans staged Python files
3. Reports blocking/warning issues
4. Respects file-based exceptions

Usage:
    ./scripts/vibesrails.py              # Scan staged files
    ./scripts/vibesrails.py --validate   # Validate YAML config
    ./scripts/vibesrails.py --show       # Show all patterns
"""

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

logger = logging.getLogger(__name__)

# Colors for terminal output
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color

class ScanResult(NamedTuple):
    """Result from scanning a file for pattern violations."""

    file: str
    line: int
    pattern_id: str
    message: str
    level: str  # "BLOCK" or "WARN"


def load_config(config_path: Path | str | None = None) -> dict:
    """Load vibesrails.yaml configuration with extends support.

    Args:
        config_path: Path to config file. If None, searches default locations.
    """
    if config_path is None:
        # Default search paths
        candidates = [
            Path("vibesrails.yaml"),
            Path("config/vibesrails.yaml"),
            Path(__file__).parent / "config" / "default.yaml",
        ]
        for path in candidates:
            if path.exists():
                config_path = path
                break

    config_path = Path(config_path) if config_path else None

    if not config_path or not config_path.exists():
        logger.error("No vibesrails.yaml found")
        sys.exit(1)

    # YAML bomb protection - limit config file size
    if config_path.stat().st_size > 1_000_000:  # 1MB limit
        logger.error("Config file too large (max 1MB)")
        sys.exit(1)

    # Use config loader with extends support
    try:
        from .config import load_config_with_extends
        return load_config_with_extends(config_path)
    except ImportError:
        # Fallback to simple load if config module not available
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            if mark:
                logger.error(
                    "%sError: %s is malformed (line %d, column %d). "
                    "Run 'vibesrails --init' to generate a valid config.%s",
                    RED, config_path, mark.line + 1, mark.column + 1, NC,
                )
            else:
                logger.error(
                    "%sError: %s is malformed. "
                    "Run 'vibesrails --init' to generate a valid config.%s",
                    RED, config_path, NC,
                )
            sys.exit(1)


def is_git_repo() -> bool:
    """Check if current directory is a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_staged_files() -> list[str]:
    """Get list of staged Python files."""
    # Validate git repository first
    if not is_git_repo():
        return []

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
    return [f for f in files if f and Path(f).exists()]


def matches_pattern(filepath: str, patterns: list[str]) -> bool:
    """Check if filepath matches any glob pattern (supports **)."""
    from fnmatch import fnmatch
    path = Path(filepath)
    for p in patterns:
        # Use Path.match for ** patterns, fnmatch for simple patterns
        if "**" in p:
            if path.match(p):
                return True
        elif fnmatch(filepath, p) or fnmatch(path.name, p):
            return True
    return False


def is_test_file(filepath: str) -> bool:
    """Check if file is a test file."""
    name = Path(filepath).name
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in filepath


# Suppression comment patterns
SUPPRESS_PATTERNS = [
    r"#\s*vibesrails:\s*ignore\b",           # vibesrails: ignore
    r"#\s*vibesrails:\s*disable\b",          # vibesrails: disable (alias)
    r"#\s*noqa:\s*vibesrails\b",             # noqa: vibesrails (familiar syntax)
]
SUPPRESS_REGEX = re.compile("|".join(SUPPRESS_PATTERNS), re.IGNORECASE)
SUPPRESS_NEXT_LINE_REGEX = re.compile(
    r"#\s*vibesrails:\s*ignore[_-]?next[_-]?line\b", re.IGNORECASE
)
SUPPRESS_PATTERN_REGEX = re.compile(
    r"#\s*vibesrails:\s*ignore\s*\[([^\]]+)\]", re.IGNORECASE
)


def is_line_suppressed(line: str, pattern_id: str, prev_line: str | None = None) -> bool:
    """Check if a line has inline or previous-line suppression comments."""
    # Check same-line suppression
    if SUPPRESS_REGEX.search(line):
        # Check if it's pattern-specific
        match = SUPPRESS_PATTERN_REGEX.search(line)
        if match:
            # Only suppress if pattern_id matches
            suppressed_ids = [p.strip() for p in match.group(1).split(",")]
            return pattern_id in suppressed_ids
        return True  # Suppress all patterns

    # Check previous line for ignore-next-line
    if prev_line and SUPPRESS_NEXT_LINE_REGEX.search(prev_line):
        return True

    return False


def safe_regex_search(pattern: str, text: str, flags: int = 0) -> bool:
    """Safely execute regex search with error handling for ReDoS protection."""
    try:
        # Limit search to first 10000 chars per line to prevent ReDoS
        return bool(re.search(pattern, text[:10000], flags))
    except (re.error, RecursionError, MemoryError):
        return False


def is_path_safe(filepath: str) -> bool:
    """Check if filepath is within current working directory (path traversal protection)."""
    try:
        file_path = Path(filepath).resolve()
        cwd = Path.cwd().resolve()
        file_path.relative_to(cwd)
        return True
    except (ValueError, RuntimeError):
        return False


def _collect_patterns(config: dict) -> tuple[list, list]:
    """Collect all blocking and warning patterns from config sections."""
    all_blocking = list(config.get("blocking", []))
    all_warning = list(config.get("warning", []))

    for section in ["bugs", "architecture", "maintainability"]:
        for pattern in config.get(section, []):
            level = pattern.get("level", "WARN")
            if level == "BLOCK":
                all_blocking.append(pattern)
            else:
                all_warning.append(pattern)

    return all_blocking, all_warning


def _should_skip_pattern(
    pattern: dict, level: str, is_test: bool, allowed_patterns: set, filepath: str,
) -> bool:
    """Check if a pattern should be skipped for the given file."""
    if level == "WARN" and pattern.get("skip_in_tests") and is_test:
        return True
    if pattern["id"] in allowed_patterns:
        return True
    scope = pattern.get("scope", [])
    return bool(scope and not matches_pattern(filepath, scope))


def _is_comment_line(line: str) -> bool:
    """Check if a line is a Python comment (not executable code)."""
    return line.lstrip().startswith("#")


# Patterns that only matter in executable code, not comments
_CODE_ONLY_PATTERNS = {
    "hardcoded_secret", "sql_injection", "command_injection",
    "shell_injection", "unsafe_yaml", "unsafe_numpy", "debug_mode_prod",
    "mutable_default",
}


def _match_line(
    line: str, prev_line: str | None, pattern: dict, flags: int,
) -> bool:
    """Check if a line matches a pattern (with exclusion and suppression)."""
    # Skip commented lines for code-only patterns (secrets, injections, etc.)
    if pattern["id"] in _CODE_ONLY_PATTERNS and _is_comment_line(line):
        return False
    if not safe_regex_search(pattern["regex"], line, flags):
        return False
    exclude_regex = pattern.get("exclude_regex")
    if exclude_regex and safe_regex_search(exclude_regex, line):
        return False
    return not is_line_suppressed(line, pattern["id"], prev_line)


def _find_non_code_lines(lines: list[str]) -> set[int]:
    """Find line numbers that are inside markdown code blocks or docstrings.

    These lines contain examples/documentation, not executable code.
    Returns a set of 1-based line numbers to skip for code-only patterns.
    """
    skip = set()
    in_docstring = False
    in_markdown_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track triple-quote docstrings containing markdown code blocks
        if '"""' in stripped or "'''" in stripped:
            # Count quotes to detect open/close
            for quote in ('"""', "'''"):
                count = stripped.count(quote)
                if count == 1:
                    in_docstring = not in_docstring
                # count >= 2 means open+close on same line, no state change

        # Track markdown code blocks inside docstrings/strings
        if in_docstring and stripped.startswith("```"):
            in_markdown_block = not in_markdown_block
            continue

        if in_docstring and in_markdown_block:
            skip.add(i)

    return skip


def _scan_patterns(
    lines: list[str],
    filepath: str,
    patterns: list[dict],
    level: str,
    allowed_patterns: set,
) -> list[ScanResult]:
    """Scan lines against a list of patterns and return results."""
    results = []
    is_test = is_test_file(filepath)
    non_code_lines = _find_non_code_lines(lines)

    for pattern in patterns:
        if _should_skip_pattern(pattern, level, is_test, allowed_patterns, filepath):
            continue

        flags = re.IGNORECASE if pattern.get("flags") == "i" else 0

        for i, line in enumerate(lines, 1):
            # Skip example code inside markdown blocks for code-only patterns
            if pattern["id"] in _CODE_ONLY_PATTERNS and i in non_code_lines:
                continue
            prev_line = lines[i - 2] if i > 1 else None
            if _match_line(line, prev_line, pattern, flags):
                results.append(ScanResult(
                    file=filepath,
                    line=i,
                    pattern_id=pattern["id"],
                    message=pattern["message"],
                    level=level,
                ))

    return results


def scan_file(filepath: str, config: dict) -> list[ScanResult]:
    """Scan a single file for pattern violations."""
    results = []

    if not is_path_safe(filepath):
        logger.warning("SKIP %s (outside project directory)", filepath)
        return results

    try:
        content = Path(filepath).read_text()
        lines = content.split("\n")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("SKIP %s (read error: %s)", filepath, e)
        return results

    # Check file length
    complexity = config.get("complexity", {})
    max_file_lines = complexity.get("max_file_lines", 0)
    if max_file_lines and len(lines) > max_file_lines and not is_test_file(filepath):
        results.append(ScanResult(
            file=filepath, line=len(lines), pattern_id="file_too_long",
            message=f"File has {len(lines)} lines (max: {max_file_lines}). Consider splitting into smaller modules.",
            level="WARN",
        ))

    # Get exceptions for this file
    allowed_patterns = set()
    for _, exc_config in config.get("exceptions", {}).items():
        if matches_pattern(filepath, exc_config.get("patterns", [])):
            allowed_patterns.update(exc_config.get("allowed", []))

    all_blocking, all_warning = _collect_patterns(config)

    results.extend(_scan_patterns(lines, filepath, all_blocking, "BLOCK", allowed_patterns))
    results.extend(_scan_patterns(lines, filepath, all_warning, "WARN", allowed_patterns))

    return results


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
    exclude = [".venv", "venv", "__pycache__", "_archive", "archive", "node_modules", ".git"]
    files = []
    for p in Path(".").rglob("*.py"):
        path_str = str(p)
        if not any(ex in path_str for ex in exclude):
            files.append(path_str)
    return files


def _determine_files(args) -> list[str]:
    """Determine which files to scan based on CLI args."""
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


if __name__ == "__main__":
    main()
