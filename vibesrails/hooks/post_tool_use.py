"""PostToolUse hook: verify files AFTER Claude writes them using vibesrails scanner.

Warn-only (always exit 0) -- the file is already written, we just report issues.
Run as: python3 -m vibesrails.hooks.post_tool_use
"""

import json
import os
import sys


def main() -> None:
    """CLI entry point -- reads JSON from stdin, always exits 0."""
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

    if not os.path.isfile(file_path):
        sys.exit(0)

    try:
        from vibesrails.scanner import load_config, scan_file
    except ImportError:
        sys.exit(0)

    try:
        config = load_config()
        results = scan_file(file_path, config)
    except Exception:  # noqa: BLE001
        sys.exit(0)

    if results:
        sys.stdout.write(
            f"VibesRails: {len(results)} issue(s) in {file_path}:\n"
        )
        for r in results:
            sys.stdout.write(f"  - L{r.line} [{r.level}] {r.message}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
