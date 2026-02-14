"""Env safety constants — extracted from env_safety.py."""

import re

# Secret patterns — imported from central source of truth
try:
    from core.secret_patterns import SECRET_PATTERN_DEFS
    SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        (label, re.compile(pattern, re.IGNORECASE))
        for pattern, label in SECRET_PATTERN_DEFS
    ]
except ImportError:
    # Fallback if core not available
    SECRET_PATTERNS = [
        ("AWS access key", re.compile(r"""(?:=|:)\s*['"]?(AKIA[0-9A-Z]{16})""")),
        (
            "Hardcoded password",
            re.compile(
                r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{4,}['"]""",
                re.IGNORECASE,
            ),
        ),
        (
            "Hardcoded token",
            re.compile(
                r"""(?:token|secret|api_key)\s*=\s*['"](?:sk-|ghp_|gho_)[^'"]+['"]""",
                re.IGNORECASE,
            ),
        ),
    ]

# Field names that should be masked in __repr__/__str__
SECRET_FIELD_NAMES: set[str] = {
    "api_key", "apikey", "api_secret", "apisecret",
    "openai_api_key", "anthropic_api_key", "google_api_key",
    "secret", "secret_key", "secretkey",
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "auth_token",
    "private_key", "privatekey",
    "aws_secret_access_key", "aws_access_key_id",
    "database_url", "db_password", "db_url",
    "smtp_password", "email_password",
    "encryption_key", "signing_key",
}

# File extensions that should never be tracked in git
SECRET_FILE_EXTS: set[str] = {".pem", ".key", ".p12"}

# Patterns that should be in .gitignore
GITIGNORE_SECRET_PATTERNS: list[str] = [
    "*.pem", "*.key", "*.p12",
]

# Pattern for unsafe os.environ usage
UNSAFE_ENVIRON_RE: re.Pattern[str] = re.compile(
    r"""os\.environ\s*\[\s*['"]([^'"]+)['"]\s*\]"""
)
