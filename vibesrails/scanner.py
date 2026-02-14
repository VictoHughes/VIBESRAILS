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
import sys
from pathlib import Path

import yaml

# Re-export all public names so existing imports continue to work
from .scanner_cli import (  # noqa: F401
    get_all_python_files,
    main,
    show_patterns,
    validate_config,
)
from .scanner_git import get_staged_files, is_git_repo  # noqa: F401
from .scanner_types import (  # noqa: F401
    BLUE,
    GREEN,
    NC,
    RED,
    YELLOW,
    ScanResult,
)
from .scanner_utils import (  # noqa: F401
    SUPPRESS_NEXT_LINE_REGEX,
    SUPPRESS_PATTERN_REGEX,
    SUPPRESS_PATTERNS,
    SUPPRESS_REGEX,
    is_line_suppressed,
    is_path_safe,
    is_test_file,
    matches_pattern,
    safe_regex_search,
)

logger = logging.getLogger(__name__)


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


def _collect_patterns(config: dict) -> tuple[list, list]:
    """Collect all blocking and warning patterns from config sections."""
    all_blocking = list(config.get("blocking") or [])
    all_warning = list(config.get("warning") or [])

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
        if not isinstance(pattern, dict) or "id" not in pattern or "regex" not in pattern:
            continue
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
    complexity = config.get("complexity") or {}
    try:
        max_file_lines = int(complexity.get("max_file_lines", 0))
    except (ValueError, TypeError):
        max_file_lines = 0
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


if __name__ == "__main__":
    main()
