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

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

# Colors for terminal output
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color

class ScanResult(NamedTuple):
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
        print(f"{RED}ERROR: No vibesrails.yaml found{NC}")
        sys.exit(1)

    # YAML bomb protection - limit config file size
    if config_path.stat().st_size > 1_000_000:  # 1MB limit
        print(f"{RED}ERROR: Config file too large (max 1MB){NC}")
        sys.exit(1)

    # Use config loader with extends support
    try:
        from .config import load_config_with_extends
        return load_config_with_extends(config_path)
    except ImportError:
        # Fallback to simple load if config module not available
        with open(config_path) as f:
            return yaml.safe_load(f)


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
    """Check if a line has suppression comments.

    Supports:
    - `# vibesrails: ignore` - ignore all patterns on this line
    - `# vibesrails: disable` - alias for ignore
    - `# noqa: vibesrails` - familiar syntax for Python devs
    - `# vibesrails: ignore [pattern_id]` - ignore specific pattern
    - `# vibesrails: ignore-next-line` - on previous line
    """
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


def scan_file(filepath: str, config: dict) -> list[ScanResult]:
    """Scan a single file for pattern violations."""
    results = []

    # Path traversal protection
    if not is_path_safe(filepath):
        print(f"{YELLOW}SKIP{NC} {filepath} (outside project directory)")
        return results

    try:
        content = Path(filepath).read_text()
        lines = content.split("\n")
    except (OSError, UnicodeDecodeError) as e:
        print(f"{YELLOW}SKIP{NC} {filepath} (read error: {e})")
        return results

    # Check file length (complexity settings)
    complexity = config.get("complexity", {})
    max_file_lines = complexity.get("max_file_lines", 0)
    if max_file_lines and len(lines) > max_file_lines and not is_test_file(filepath):
        results.append(ScanResult(
            file=filepath,
            line=len(lines),
            pattern_id="file_too_long",
            message=f"File has {len(lines)} lines (max: {max_file_lines}). Consider splitting into smaller modules.",
            level="WARN",
        ))

    # Get exceptions for this file
    exceptions = config.get("exceptions", {})
    allowed_patterns = set()

    for _, exc_config in exceptions.items():
        if matches_pattern(filepath, exc_config.get("patterns", [])):
            allowed_patterns.update(exc_config.get("allowed", []))

    # Collect all patterns from all sections
    all_blocking = config.get("blocking", [])
    all_warning = config.get("warning", [])

    # Add patterns from pro coding sections
    for section in ["bugs", "architecture", "maintainability"]:
        for pattern in config.get(section, []):
            level = pattern.get("level", "WARN")
            if level == "BLOCK":
                all_blocking.append(pattern)
            else:
                all_warning.append(pattern)

    # Check blocking patterns
    for pattern in all_blocking:
        pattern_id = pattern["id"]

        # Skip if this file has an exception for this pattern
        if pattern_id in allowed_patterns:
            continue

        # Check scope (file patterns where rule applies)
        scope = pattern.get("scope", [])
        if scope and not matches_pattern(filepath, scope):
            continue

        regex = pattern["regex"]
        flags = re.IGNORECASE if pattern.get("flags") == "i" else 0
        exclude_regex = pattern.get("exclude_regex")

        for i, line in enumerate(lines, 1):
            if safe_regex_search(regex, line, flags):
                # Check exclusion pattern
                if exclude_regex and safe_regex_search(exclude_regex, line):
                    continue

                # Check inline suppression
                prev_line = lines[i - 2] if i > 1 else None
                if is_line_suppressed(line, pattern_id, prev_line):
                    continue

                results.append(ScanResult(
                    file=filepath,
                    line=i,
                    pattern_id=pattern_id,
                    message=pattern["message"],
                    level="BLOCK",
                ))

    # Check warning patterns (skip in test files if configured)
    for pattern in all_warning:
        if pattern.get("skip_in_tests") and is_test_file(filepath):
            continue

        # Check scope
        scope = pattern.get("scope", [])
        if scope and not matches_pattern(filepath, scope):
            continue

        regex = pattern["regex"]
        flags = re.IGNORECASE if pattern.get("flags") == "i" else 0
        exclude = pattern.get("exclude_regex")

        for i, line in enumerate(lines, 1):
            if safe_regex_search(regex, line, flags):
                if exclude and safe_regex_search(exclude, line):
                    continue

                # Check inline suppression
                prev_line = lines[i - 2] if i > 1 else None
                if is_line_suppressed(line, pattern["id"], prev_line):
                    continue

                results.append(ScanResult(
                    file=filepath,
                    line=i,
                    pattern_id=pattern["id"],
                    message=pattern["message"],
                    level="WARN",
                ))

    return results


def show_patterns(config: dict) -> None:
    """Display all configured patterns."""
    print(f"\n{BLUE}=== vibesrails patterns ==={NC}\n")

    # Security patterns
    print(f"{RED}🔒 SECURITY (BLOCKING):{NC}")
    for p in config.get("blocking", []):
        print(f"  [{p['id']}] {p['name']}")
        print(f"    {p['message']}")

    print(f"\n{YELLOW}⚠️  SECURITY (WARNINGS):{NC}")
    for p in config.get("warning", []):
        skip = " (skip tests)" if p.get("skip_in_tests") else ""
        print(f"  [{p['id']}] {p['name']}{skip}")
        print(f"    {p['message']}")

    # Pro coding sections
    for section, emoji, title in [
        ("bugs", "🐛", "BUGS SILENCIEUX"),
        ("architecture", "🏗️", "ARCHITECTURE"),
        ("maintainability", "🔧", "MAINTENABILITÉ"),
    ]:
        patterns = config.get(section, [])
        if patterns:
            print(f"\n{BLUE}{emoji} {title}:{NC}")
            for p in patterns:
                level = p.get("level", "WARN")
                color = RED if level == "BLOCK" else YELLOW
                scope = f" [scope: {p['scope']}]" if p.get("scope") else ""
                skip = " (skip tests)" if p.get("skip_in_tests") else ""
                print(f"  {color}[{level}]{NC} [{p['id']}] {p['name']}{scope}{skip}")
                print(f"    {p['message']}")

    print(f"\n{GREEN}✅ EXCEPTIONS:{NC}")
    for name, exc in config.get("exceptions", {}).items():
        print(f"  {name}: {exc.get('reason', '')}")
        print(f"    files: {exc['patterns']}")
        print(f"    allowed: {exc['allowed']}")


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
        print(f"{RED}Validation errors:{NC}")
        for e in errors:
            print(f"  - {e}")
        return False

    print(f"{GREEN}vibesrails.yaml is valid{NC}")
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


def main():
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

    # Determine files to scan
    if args.file:
        files = [args.file] if Path(args.file).exists() else []
    elif args.all:
        files = get_all_python_files()
    else:
        files = get_staged_files()

    print(f"{BLUE}vibesrails - Security Scan{NC}")
    print("=" * 30)

    if not files:
        print(f"{GREEN}No Python files to scan{NC}")
        sys.exit(0)

    print(f"Scanning {len(files)} file(s)...\n")

    all_results = []
    for filepath in files:
        results = scan_file(filepath, config)
        all_results.extend(results)

    # Report results
    blocking = [r for r in all_results if r.level == "BLOCK"]
    warnings = [r for r in all_results if r.level == "WARN"]

    for r in blocking:
        print(f"{RED}BLOCK{NC} {r.file}:{r.line}")
        print(f"  [{r.pattern_id}] {r.message}")

    for r in warnings:
        print(f"{YELLOW}WARN{NC} {r.file}:{r.line}")
        print(f"  [{r.pattern_id}] {r.message}")

    print("=" * 30)
    print(f"BLOCKING: {len(blocking)} | WARNINGS: {len(warnings)}")

    if blocking:
        print(f"\n{RED}Fix blocking issues before committing.{NC}")
        sys.exit(1)

    print(f"\n{GREEN}vibesrails: PASSED{NC}")
    sys.exit(0)


if __name__ == "__main__":
    main()
