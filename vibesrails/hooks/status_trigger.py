"""Status trigger — periodic project status reports during coding sessions.

Run as: python -m vibesrails.hooks.status_trigger

Triggers vibesrails --status --quiet when:
- 5 commits since last status
- 1 hour since last status
- Branch changed since last check
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

STATE_FILE = Path(".vibesrails") / ".session_state"
COMMIT_THRESHOLD = 5
TIME_THRESHOLD = 3600  # 1 hour


def _get_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _load_state() -> dict:
    """Load session state from disk."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"commits": 0, "last_status": 0.0, "branch": ""}


def _save_state(state: dict) -> None:
    """Persist session state to disk."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def check_and_trigger() -> bool:
    """Check triggers, update state, return True if status should run."""
    state = _load_state()
    branch = _get_branch()
    now = time.time()
    trigger = False

    state["commits"] = state.get("commits", 0) + 1

    # Every N commits
    if state["commits"] >= COMMIT_THRESHOLD:
        trigger = True

    # Every hour
    if now - state.get("last_status", 0.0) > TIME_THRESHOLD:
        trigger = True

    # Branch change
    if branch and branch != state.get("branch", ""):
        trigger = True

    state["branch"] = branch
    if trigger:
        state["last_status"] = now
        state["commits"] = 0

    _save_state(state)
    return trigger


if __name__ == "__main__":
    if check_and_trigger():
        try:
            subprocess.run(
                [sys.executable, "-m", "vibesrails", "--status", "--quiet"],
                timeout=10,
            )
        except Exception:
            pass  # --status may not exist yet; fail silently
