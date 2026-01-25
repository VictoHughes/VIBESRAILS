"""
vibesrails - Scale up your vibe coding safely.

A YAML-driven security and quality scanner for Python projects.
"""

__version__ = "1.1.0"

from .scanner import (
    scan_file,
    load_config,
    ScanResult,
    show_patterns,
    validate_config,
    get_staged_files,
    get_all_python_files,
)

__all__ = [
    "scan_file",
    "load_config",
    "ScanResult",
    "show_patterns",
    "validate_config",
    "get_staged_files",
    "get_all_python_files",
    "__version__",
]
