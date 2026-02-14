# VibesRails — Security guardrails for AI-assisted development
# ABH AMH — If you know, you know.
"""
vibesrails - Scale up your vibe coding safely.

A YAML-driven security and quality scanner for Python projects.
"""

__version__ = "2.1.1"

from .scanner import (
    ScanResult,
    get_all_python_files,
    get_staged_files,
    load_config,
    scan_file,
    show_patterns,
    validate_config,
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
