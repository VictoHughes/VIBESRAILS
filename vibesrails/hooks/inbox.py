"""Mobile inbox: a markdown file editable from any device.

On SessionStart, Claude reads it as instructions and clears it.
"""

from __future__ import annotations

import re
from pathlib import Path

_TEMPLATE_HEADER = "<!-- Write instructions below. They will be read on next Claude Code session start. -->\n"
_TEMPLATE_RE = re.compile(r"^\s*<!--.*?-->\s*$")


def check_inbox(inbox_path: Path) -> str:
    """Return meaningful content from the inbox, or '' if nothing actionable."""
    if not inbox_path.exists():
        return ""
    text = inbox_path.read_text(encoding="utf-8")
    if not text.strip():
        return ""
    lines = [line for line in text.splitlines() if not _TEMPLATE_RE.match(line)]
    content = "\n".join(lines).strip()
    return content


def clear_inbox(inbox_path: Path) -> None:
    """Reset inbox to the template header."""
    inbox_path.write_text(_TEMPLATE_HEADER, encoding="utf-8")


def create_inbox(inbox_path: Path) -> None:
    """Create inbox file with template if it doesn't exist."""
    if inbox_path.exists():
        return
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(_TEMPLATE_HEADER, encoding="utf-8")
