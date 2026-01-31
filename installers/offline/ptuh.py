#!/usr/bin/env python3
"""Protect vibesrails from being modified by Claude Code.

This hook runs BEFORE any Edit/Write/Bash tool call.
It blocks modifications to:
- .git/hooks/ (pre-commit hook)
- vibesrails.yaml (config)
- .github/workflows/ (CI pipelines)
- site-packages/vibesrails/ (installed package)
- ~/.claude/settings.json (this protection itself)
- ~/.claude/hooks/ (hook scripts)
"""

import json
import re
import sys

# Secret patterns — block commands and file content containing secrets
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?:sk-|sk-proj-)[a-zA-Z0-9]{20,}", "OpenAI/API Secret Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab Personal Access Token"),
    (r"xox[bps]-[a-zA-Z0-9\-]{10,}", "Slack Token"),
    (r"Bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer Token in command"),
    (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
    (r"(?:api_key|apikey|secret_key|secret)\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded API key"),
]
_SECRET_REGEXES = [(re.compile(p), label) for p, label in SECRET_PATTERNS]

PROTECTED_PATHS = [
    ".git/hooks",
    "vibesrails.yaml",
    ".github/workflows",
    "site-packages/vibesrails",
    ".claude/settings.json",
    ".claude/hooks/",
    ".claude/hooks/ptuh.py",
]

# Block dangerous bash commands
BLOCKED_COMMANDS = [
    # Git hooks tampering
    "rm .git/hooks",
    "rm -f .git/hooks",
    "rm -rf .git/hooks",
    "> .git/hooks",
    "chmod 6",
    "chmod 7",
    # Skip pre-commit
    "git commit " + "-n ",
    "git commit " + "--no-verify",
    "--no" + "-verify",
    # Destructive git commands
    "git push " + "--force",
    "git push " + "-f ",
    "git push origin " + "--force",
    "git push origin " + "-f ",
    "git reset " + "--hard",
    "git checkout .",
    "git checkout -- .",
    "git restore .",
    "git restore --staged .",
    "git clean " + "-f",
    "git branch " + "-D ",
    # Vibesrails tampering
    "pip install " + "-e",
    "uninstall vibesrails",
    "pip uninstall vibesrails",
    # Hook self-protection
    "rm ~/.claude/hooks",
    "rm -rf ~/.claude/hooks",
    "rm ~/.claude/hooks",
]


def check_file_path(tool_input):
    """Check if a file path is protected."""
    file_path = tool_input.get("file_path", "")
    for protected in PROTECTED_PATHS:
        if protected in file_path:
            print(
                f"\U0001f534 BLOCKED: Cannot modify protected file: {file_path}\n"
                f"Reason: '{protected}' is protected by vibesrails security hook.\n"
                f"This protection cannot be disabled by Claude Code."
            )
            sys.exit(1)


def check_secrets(text, context):
    """Check if text contains secrets (API keys, tokens, passwords)."""
    for regex, label in _SECRET_REGEXES:
        match = regex.search(text)
        if match:
            # Mask the secret for display
            found = match.group(0)
            masked = found[:8] + "..." + found[-4:] if len(found) > 16 else found[:6] + "..."
            print(
                f"\U0001f534 BLOCKED: Secret detected in {context}.\n"
                f"Type: {label}\n"
                f"Found: {masked}\n"
                f"Never pass secrets in commands or file content.\n"
                f"Use environment variables instead: os.environ.get('KEY')"
            )
            sys.exit(1)


def check_bash_command(tool_input):
    """Check if a bash command targets protected resources or contains secrets."""
    command = tool_input.get("command", "")
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            print(
                f"\U0001f534 BLOCKED: Dangerous command detected.\n"
                f"Pattern: '{blocked}'\n"
                f"This protection cannot be disabled by Claude Code."
            )
            sys.exit(1)
    # Scan command for secrets
    check_secrets(command, "bash command")


def main():
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name in ("Edit", "Write"):
        check_file_path(tool_input)
        # Scan content for secrets
        content = tool_input.get("content", "") or tool_input.get("new_string", "")
        if content:
            check_secrets(content, f"file content ({tool_input.get('file_path', '?')})")
    elif tool_name == "Bash":
        check_bash_command(tool_input)

    # Allow everything else
    sys.exit(0)


if __name__ == "__main__":
    main()
