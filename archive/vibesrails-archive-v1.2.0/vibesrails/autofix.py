"""
vibesrails auto-fix - Automatic fixes for common patterns.

Only fixes patterns with clear, safe transformations.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .scanner import BLUE, GREEN, NC, YELLOW

logger = logging.getLogger(__name__)


@dataclass
class Fix:
    """Represents an auto-fix transformation."""
    pattern_id: str
    search: str      # Regex to find
    replace: str     # Replacement (can use \1, \2 for groups)
    description: str


# Safe, deterministic fixes
FIXES = [
    # None comparison
    Fix(  # vibesrails: ignore
        pattern_id="none_comparison",
        search=r"(\w+)\s*==\s*None",  # vibesrails: ignore
        replace=r"\1 is None",
        description="Use 'is None' instead of '== None'",  # vibesrails: ignore
    ),
    Fix(
        pattern_id="none_comparison_not",
        search=r"(\w+)\s*!=\s*None",
        replace=r"\1 is not None",
        description="Use 'is not None' instead of '!= None'",
    ),

    # Unsafe YAML
    Fix(
        pattern_id="unsafe_yaml",
        search=r"yaml\.load\(([^,)]+)\)",
        replace=r"yaml.safe_load(\1)",
        description="Use safe_load instead of load for YAML",  # vibesrails: ignore
    ),

    # Boolean comparison
    Fix(
        pattern_id="bool_comparison_true",
        search=r"(\w+)\s*==\s*True\b",
        replace=r"\1",
        description="Remove '== True' comparison",
    ),
    Fix(
        pattern_id="bool_comparison_false",
        search=r"(\w+)\s*==\s*False\b",
        replace=r"not \1",
        description="Use 'not x' instead of 'x == False'",
    ),

    # Type comparison
    Fix(
        pattern_id="type_comparison",
        search=r"type\((\w+)\)\s*==\s*(\w+)",
        replace=r"isinstance(\1, \2)",
        description="Use isinstance() instead of type() ==",
    ),

    # String startswith/endswith
    Fix(
        pattern_id="string_slice_start",
        search=r"(\w+)\[:(\d+)\]\s*==\s*(['\"][^'\"]+['\"])",
        replace=r"\1.startswith(\3)",
        description="Use str.startswith() instead of slice comparison",
    ),

    # Dict get with default None
    Fix(
        pattern_id="dict_get_none",
        search=r"\.get\(([^,)]+),\s*None\)",
        replace=r".get(\1)",
        description="Remove redundant None default in dict.get()",
    ),
]


def get_fix_for_pattern(pattern_id: str) -> Fix | None:
    """Get the fix for a pattern ID if available."""
    for fix in FIXES:
        if fix.pattern_id == pattern_id:
            return fix
    return None


def apply_fix_to_line(line: str, fix: Fix) -> tuple[str, bool]:
    """Apply a fix to a line. Returns (new_line, was_changed)."""
    new_line = re.sub(fix.search, fix.replace, line)
    return new_line, new_line != line


def is_path_safe_for_fix(filepath: str) -> bool:
    """Check if filepath is safe to modify (symlink + path traversal protection)."""
    try:
        cwd = Path.cwd().resolve()
        path = Path(filepath).resolve()
        path.relative_to(cwd)
        return True
    except ValueError:
        return False


def apply_fix_to_file(
    filepath: str,
    fix: Fix,
    dry_run: bool = False,
    backup: bool = True
) -> list[tuple[int, str, str]]:
    """Apply a fix to all matching lines in a file.

    Args:
        filepath: Path to the file to fix
        fix: The Fix to apply
        dry_run: If True, don't write changes
        backup: If True, create .bak backup before writing

    Returns list of (line_number, old_line, new_line) tuples.
    """
    # Symlink + path traversal protection
    if not is_path_safe_for_fix(filepath):
        logger.error("BLOCKED: File path outside project: %s", filepath)
        return []

    path = Path(filepath)
    content = path.read_text()
    lines = content.split("\n")

    changes = []
    new_lines = []

    for i, line in enumerate(lines, 1):
        new_line, changed = apply_fix_to_line(line, fix)
        new_lines.append(new_line)

        if changed:
            changes.append((i, line.strip(), new_line.strip()))

    if changes and not dry_run:
        # Create backup before modifying
        if backup:
            backup_path = Path(f"{filepath}.bak").resolve()
            # Verify backup path is also safe
            try:
                cwd = Path.cwd().resolve()
                backup_path.relative_to(cwd)
                backup_path.write_text(content)
            except ValueError:
                logger.warning("Backup path outside project, skipping backup")

        path.write_text("\n".join(new_lines))

    return changes


def _fix_single_file(filepath: str, config: dict, dry_run: bool, backup: bool) -> int:
    """Apply fixes to a single file. Returns number of fixes applied."""
    from .scanner import scan_file

    results = scan_file(filepath, config)
    file_fixes = 0
    for result in results:
        fix = get_fix_for_pattern(result.pattern_id)
        if not fix:
            continue
        changes = apply_fix_to_file(filepath, fix, dry_run, backup)
        for line_num, old, new in changes:
            label = f"{YELLOW}WOULD FIX{NC}" if dry_run else f"{GREEN}FIXED{NC}"
            logger.info(f"{label} {filepath}:{line_num}")
            logger.info(f"  - {old}")
            logger.info(f"  + {new}")
            file_fixes += 1
    return file_fixes


def run_autofix(
    config: dict,
    files: list[str],
    dry_run: bool = False,
    backup: bool = True,
) -> int:
    """Run auto-fix on files. Returns number of files modified."""
    mode_str = " (dry run)" if dry_run else ""
    backup_str = "" if backup or dry_run else " (no backup)"
    logger.info(f"{BLUE}vibesrails --fix{mode_str}{backup_str}{NC}")
    logger.info("=" * 40)

    total_fixes = 0
    files_modified = 0

    for filepath in files:
        file_fixes = _fix_single_file(filepath, config, dry_run, backup)
        if file_fixes > 0:
            total_fixes += file_fixes
            if not dry_run:
                files_modified += 1

    logger.info("=" * 40)
    if dry_run:
        logger.info(f"Would fix {total_fixes} issue(s)")
    else:
        logger.info(f"Fixed {total_fixes} issue(s) in {files_modified} file(s)")
    return files_modified


def show_fixable_patterns() -> None:
    """Show all patterns that can be auto-fixed."""
    logger.info(f"\n{BLUE}=== Auto-fixable Patterns ==={NC}\n")

    for fix in FIXES:
        logger.info(f"  [{fix.pattern_id}]")
        logger.info(f"    {fix.description}")
        logger.info("")
