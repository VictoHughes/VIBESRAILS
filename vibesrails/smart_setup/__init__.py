"""
vibesrails Smart Setup Package.

Auto-configuration for Claude Code projects.
"""

from .core import run_smart_setup_cli, smart_setup
from .detection import (
    ARCHITECTURE_TOOLS,
    PROJECT_SIGNATURES,
    SECRET_INDICATORS,
    detect_architecture_complexity,
    detect_env_files,
    detect_existing_configs,
    detect_project_language,
    detect_project_type,
    detect_secrets_risk,
)
from .i18n import LANG, MESSAGES, detect_language, msg
from .vibe_mode import (
    VIBE_PROTECTIONS,
    natural_language_to_pattern,
    prompt_user,
    prompt_vibe_protections,
    scan_for_secrets,
)

__all__ = [
    # Core
    "smart_setup",
    "run_smart_setup_cli",
    # Detection
    "detect_project_type",
    "detect_existing_configs",
    "detect_secrets_risk",
    "detect_env_files",
    "detect_project_language",
    "detect_architecture_complexity",
    # Constants
    "PROJECT_SIGNATURES",
    "SECRET_INDICATORS",
    "ARCHITECTURE_TOOLS",
    "VIBE_PROTECTIONS",
    # i18n
    "LANG",
    "MESSAGES",
    "msg",
    "detect_language",
    # Vibe mode
    "scan_for_secrets",
    "natural_language_to_pattern",
    "prompt_user",
    "prompt_vibe_protections",
]
