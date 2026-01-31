"""PreToolUse hook: scan BEFORE Claude Code writes or executes.

Blocks unsafe patterns in code (secrets, SQL injection, dangerous functions)
and leaked secrets in bash commands.
Run as: python3 -m vibesrails.hooks.pre_tool_use
"""

import json
import re
import sys

CRITICAL_PATTERNS = [
    (
        r"(?:api_key|secret|token|password|passwd)\s*=\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded secret detected",
    ),
    (
        r"(?:AKIA|sk-|ghp_|gho_)[A-Za-z0-9_\-]{10,}",
        "API key detected",
    ),
    (
        r"f['\"](?:SELECT|INSERT|UPDATE|DELETE)\b.*\{",
        "SQL injection via f-string",
    ),
    (
        r"(?:SELECT|INSERT|UPDATE|DELETE)\b.*\.format\s*\(",
        "SQL injection via .format()",
    ),
    (
        r"eval\s*\(",
        "Use of eval() is dangerous",
    ),
    (
        r"exec\s*\(",
        "Use of exec() is dangerous",
    ),
    (
        r"subprocess\.(?:call|run|Popen)\s*\(.*" + r"shell\s*=\s*True",  # vibesrails: ignore
        "shell" + "=True is dangerous",
    ),
]

COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), msg) for p, msg in CRITICAL_PATTERNS]

# Patterns for secrets leaked in bash commands
BASH_SECRET_PATTERNS = [
    (
        r"(?:AKIA|sk-|ghp_|gho_)[A-Za-z0-9_\-]{10,}",
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


def scan_content(content: str) -> list[str]:
    """Scan content for critical patterns. Returns list of issues."""
    issues = []
    for line in content.splitlines():
        if _should_skip_line(line):
            continue
        for pattern, message in COMPILED_PATTERNS:
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
    if not file_path.endswith(".py"):
        sys.exit(0)

    content = tool_input.get("content", "") or tool_input.get("new_string", "") or ""
    if not content:
        sys.exit(0)

    issues = scan_content(content)
    if issues:
        sys.stdout.write(f"\U0001f534 VibesRails BLOCKED ({len(issues)} issue(s)):\n")  # vibesrails: ignore
        sys.stdout.write("\n".join(issues) + "\n")  # vibesrails: ignore
        sys.stdout.write("\nFix the code. Add '# vibesrails: ignore' to suppress.\n")  # vibesrails: ignore
        sys.exit(1)

    basename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
    sys.stdout.write(f"\U0001f7e2 VibesRails: {basename} pre-scan clean\n")  # vibesrails: ignore
    sys.exit(0)


if __name__ == "__main__":
    main()
