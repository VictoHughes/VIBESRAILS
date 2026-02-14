"""Type definitions and constants for vibesrails scanner."""

from typing import NamedTuple

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
