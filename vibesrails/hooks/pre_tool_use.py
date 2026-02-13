"""PreToolUse hook: scan BEFORE Claude Code writes or executes.

Blocks unsafe patterns in code (secrets, SQL injection, dangerous functions)
and leaked secrets in bash commands.
Run as: python3 -m vibesrails.hooks.pre_tool_use
"""

import json
import re
import sys
from pathlib import Path

# Throttle state directory
VIBESRAILS_DIR = Path.cwd() / ".vibesrails"

# Commands that count as "verification" — resets the write counter
CHECK_COMMANDS = ["pytest", "ruff", "vibesrails", "lint-imports", "bandit", "mypy"]

# Secret patterns — imported from central source of truth
try:
    from core.secret_patterns import SECRET_PATTERN_DEFS
    SECRET_PATTERNS = [(p, label) for p, label in SECRET_PATTERN_DEFS]
except ImportError:
    # Fallback if core not installed (standalone hook usage)
    SECRET_PATTERNS = [
        (
            r"(?:api_key|secret|token|password|passwd)\s*=\s*['\"][^'\"]{8,}['\"]",
            "Hardcoded secret detected",
        ),
        (
            r"(?:AKIA|sk-|ghp_|gho_)[A-Za-z0-9_\-]{10,}",
            "API key detected",
        ),
    ]

# Code patterns — applied to .py files ONLY (not relevant for config files)
CODE_PATTERNS = [
    (
        r"f['\"](?:SELECT|INSERT|UPDATE|DELETE)\b.*\{",
        "SQL injection via f-string",
    ),
    (
        r"(?:SELECT|INSERT|UPDATE|DELETE)\b.*\.format\s*\(",
        "SQL injection via .format()",
    ),
    (  # vibesrails: ignore
        r"eval\s*\(",
        "Use of " + "eval() is dangerous",
    ),
    (  # vibesrails: ignore
        r"exec\s*\(",
        "Use of " + "exec() is dangerous",
    ),
    (
        r"subprocess\.(?:call|run|Popen)\s*\(.*" + r"shell\s*=\s*True",  # vibesrails: ignore
        "shell" + "=True is dangerous",
    ),
]

# Combined for backward compat (used by .py scanning)
CRITICAL_PATTERNS = SECRET_PATTERNS + CODE_PATTERNS

COMPILED_SECRET_PATTERNS = [(re.compile(p, re.IGNORECASE), msg) for p, msg in SECRET_PATTERNS]
COMPILED_CODE_PATTERNS = [(re.compile(p, re.IGNORECASE), msg) for p, msg in CODE_PATTERNS]
COMPILED_PATTERNS = COMPILED_SECRET_PATTERNS + COMPILED_CODE_PATTERNS

# File extensions to scan for secrets (beyond .py)
SCANNABLE_EXTENSIONS = {
    ".py", ".env", ".yaml", ".yml", ".json", ".toml",
    ".cfg", ".ini", ".sh", ".bash", ".zsh",
    ".dockerfile", ".tf", ".tfvars",
}

# Binary extensions to always skip
BINARY_EXTENSIONS = {
    ".whl", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".pdf", ".pyc", ".pyo", ".egg",
    ".db", ".sqlite", ".sqlite3",
}

# Patterns for secrets leaked in bash commands
BASH_SECRET_PATTERNS = [
    (
        r"(?:AKIA|sk-|ghp_|gho_|glpat-|npm_|pypi-|sbp_)[A-Za-z0-9_\-]{10,}",
        "API key leaked in command",
    ),
    (
        r"(?:Bearer|token|Authorization)[:\s]+['\"]?[A-Za-z0-9_\-]{20,}",
        "Auth token leaked in command",
    ),
    (
        r"(?:password|passwd|pwd)[=:\s]+['\"]?[^\s'\"]{8,}",
        "Password leaked in command",
    ),
    (
        r"[0-9]{8,10}:[A-Za-z0-9_\-]{35,}",
        "Telegram bot token leaked in command",
    ),
]

COMPILED_BASH_PATTERNS = [(re.compile(p, re.IGNORECASE), msg) for p, msg in BASH_SECRET_PATTERNS]


def scan_bash_command(command: str) -> list[str]:
    """Scan a bash command for leaked secrets."""
    issues = []
    for pattern, message in COMPILED_BASH_PATTERNS:
        if pattern.search(command):
            # Redact the match in output
            redacted = pattern.sub("[REDACTED]", command)
            issues.append(f"  - {message}: {redacted[:80]}")
    return issues


def _should_skip_line(line: str) -> bool:
    """Return True if the line should be excluded from scanning."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if "vibesrails: ignore" in stripped or "vibesrails: disable" in stripped:
        return True
    return False


def scan_content(content: str, patterns=None) -> list[str]:
    """Scan content for patterns. Returns list of issues.

    Args:
        content: The text content to scan.
        patterns: Compiled patterns to use. Defaults to COMPILED_PATTERNS (all).
    """
    if patterns is None:
        patterns = COMPILED_PATTERNS
    issues = []
    for line in content.splitlines():
        if _should_skip_line(line):
            continue
        for pattern, message in patterns:
            if pattern.search(line):
                issues.append(f"  - {message}: {line.strip()[:80]}")
                break
    return issues


def main() -> None:
    """CLI entry point -- reads JSON from stdin, exits 1 to block."""
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # --- Throttle: anti-emballement ---
    try:
        from vibesrails.hooks.throttle import record_check, record_write, should_block

        if tool_name in ("Write", "Edit"):
            if should_block(VIBESRAILS_DIR):
                msg = (
                    "\U0001f6d1 VibesRails THROTTLE: Too many writes without verification.\n"  # vibesrails: ignore
                    "Run pytest, ruff, or vibesrails --all before continuing.\n"
                )
                reminder_path = Path(".claude") / "rules_reminder.md"
                if reminder_path.exists():
                    msg += "\n" + reminder_path.read_text(encoding="utf-8")
                sys.stdout.write(msg)
                sys.exit(1)
            record_write(VIBESRAILS_DIR)

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if any(cmd in command for cmd in CHECK_COMMANDS):
                record_check(VIBESRAILS_DIR)
    except ImportError:
        pass  # throttle module not installed, skip gracefully

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        issues = scan_bash_command(command) if command else []
        if issues:
            sys.stdout.write("\U0001f534 VibesRails BLOCKED (secret in command):\n")  # vibesrails: ignore
            sys.stdout.write("\n".join(issues) + "\n")  # vibesrails: ignore
            sys.stdout.write("\nUse environment variables instead.\n")  # vibesrails: ignore
            sys.exit(1)
        sys.exit(0)

    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    basename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path

    # Determine file extension and scannability
    ext = Path(file_path).suffix.lower() if file_path else ""

    # Handle dotfiles without real extension (e.g. .env, .env.local, .env.production)
    is_dotenv = basename.startswith(".env")

    # Skip binary files explicitly
    if ext in BINARY_EXTENSIONS:
        sys.exit(0)

    # Determine which patterns to apply
    is_python = ext == ".py"
    is_scannable = is_python or ext in SCANNABLE_EXTENSIONS or is_dotenv

    if not is_scannable:
        sys.exit(0)

    content = tool_input.get("content", "") or tool_input.get("new_string", "") or ""
    if not content:
        sys.exit(0)

    # .py files get full scan (secrets + code patterns); others get secrets only
    if is_python:
        issues = scan_content(content)
    else:
        issues = scan_content(content, patterns=COMPILED_SECRET_PATTERNS)

    if issues:
        sys.stdout.write(f"\U0001f534 VibesRails BLOCKED ({len(issues)} issue(s)):\n")  # vibesrails: ignore
        sys.stdout.write("\n".join(issues) + "\n")  # vibesrails: ignore
        sys.stdout.write("\nFix the code. Add '# vibesrails: ignore' to suppress.\n")  # vibesrails: ignore
        sys.exit(1)

    sys.stdout.write(f"\U0001f7e2 VibesRails: {basename} pre-scan clean\n")  # vibesrails: ignore
    sys.exit(0)


if __name__ == "__main__":
    main()
