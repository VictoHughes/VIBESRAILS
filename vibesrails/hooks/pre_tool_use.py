"""PreToolUse hook: scan code BEFORE Claude Code writes it to disk.

Blocks unsafe patterns (secrets, SQL injection, dangerous functions) in real-time.
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
        sys.stdout.write(f"BLOCKED by VibesRails ({len(issues)} issue(s) found):\n")  # vibesrails: ignore
        sys.stdout.write("\n".join(issues) + "\n")  # vibesrails: ignore
        sys.stdout.write("\nAdd '# vibesrails: ignore' to suppress a line.\n")  # vibesrails: ignore
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
