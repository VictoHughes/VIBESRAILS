"""
vibesrails auto-fix - Automatic fixes for common patterns.

Only fixes patterns with clear, safe transformations.
"""

import re
from pathlib import Path
from dataclasses import dataclass

from .scanner import RED, YELLOW, GREEN, BLUE, NC


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


def apply_fix_to_file(filepath: str, fix: Fix, dry_run: bool = False) -> list[tuple[int, str, str]]:
    """Apply a fix to all matching lines in a file.

    Returns list of (line_number, old_line, new_line) tuples.
    """
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
        path.write_text("\n".join(new_lines))

    return changes


def run_autofix(config: dict, files: list[str], dry_run: bool = False) -> int:
    """Run auto-fix on files.

    Returns number of files modified.
    """
    from .scanner import scan_file

    print(f"{BLUE}vibesrails --fix{' (dry run)' if dry_run else ''}{NC}")
    print("=" * 40)

    total_fixes = 0
    files_modified = 0

    for filepath in files:
        # Scan to find issues
        results = scan_file(filepath, config)

        file_fixes = 0
        for result in results:
            fix = get_fix_for_pattern(result.pattern_id)
            if not fix:
                continue

            changes = apply_fix_to_file(filepath, fix, dry_run)

            for line_num, old, new in changes:
                if dry_run:
                    print(f"{YELLOW}WOULD FIX{NC} {filepath}:{line_num}")
                else:
                    print(f"{GREEN}FIXED{NC} {filepath}:{line_num}")
                print(f"  - {old}")
                print(f"  + {new}")
                file_fixes += 1

        if file_fixes > 0:
            total_fixes += file_fixes
            if not dry_run:
                files_modified += 1

    print("=" * 40)

    if dry_run:
        print(f"Would fix {total_fixes} issue(s)")
    else:
        print(f"Fixed {total_fixes} issue(s) in {files_modified} file(s)")

    return files_modified


def show_fixable_patterns():
    """Show all patterns that can be auto-fixed."""
    print(f"\n{BLUE}=== Auto-fixable Patterns ==={NC}\n")

    for fix in FIXES:
        print(f"  [{fix.pattern_id}]")
        print(f"    {fix.description}")
        print()
