"""Utility functions for vibesrails scanner."""

import re
from pathlib import Path


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
