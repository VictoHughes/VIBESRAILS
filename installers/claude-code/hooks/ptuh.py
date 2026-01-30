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
import sys

PROTECTED_PATHS = [
    ".git/hooks",
    "vibesrails.yaml",
    ".github/workflows",
    "site-packages/vibesrails",
    ".claude/settings.json",
    ".claude/hooks/protect_vibesrails",
]

# Also block dangerous bash commands
BLOCKED_COMMANDS = [
    "rm .git/hooks",
    "rm -f .git/hooks",
    "rm -rf .git/hooks",
    "> .git/hooks",
    "chmod 6",
    "chmod 7",
    "pip install -e",
    "--no-verify",
    "git commit -n ",
    "git commit --no-verify",
    "uninstall vibesrails",
    "pip uninstall vibesrails",
]


def check_file_path(tool_input):
    """Check if a file path is protected."""
    file_path = tool_input.get("file_path", "")
    for protected in PROTECTED_PATHS:
        if protected in file_path:
            print(
                f"BLOCKED: Cannot modify protected file: {file_path}\n"
                f"Reason: '{protected}' is protected by vibesrails security hook.\n"
                f"This protection cannot be disabled by Claude Code."
            )
            sys.exit(1)


def check_bash_command(tool_input):
    """Check if a bash command targets protected resources."""
    command = tool_input.get("command", "")
    for blocked in BLOCKED_COMMANDS:
        if blocked in command:
            print(
                f"BLOCKED: Dangerous command detected.\n"
                f"Pattern: '{blocked}'\n"
                f"This protection cannot be disabled by Claude Code."
            )
            sys.exit(1)


def main():
    data = json.loads(sys.stdin.read())
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name in ("Edit", "Write"):
        check_file_path(tool_input)
    elif tool_name == "Bash":
        check_bash_command(tool_input)

    # Allow everything else
    sys.exit(0)


if __name__ == "__main__":
    main()
