"""PEV tracker — Plan→Execute→Verify session operation tracking.

Tracks reads, writes, and test writes across a coding session
to enforce methodology discipline:
- Plan: read before write (audit before fix)
- Execute: within scope (handled by context adapter)
- Verify: write tests after code changes

State persisted to .vibesrails/.pev_state (JSON, gitignored).
Reset at each SessionStart.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

STATE_DIR = Path(".vibesrails")
STATE_FILE = STATE_DIR / ".pev_state"

# Patterns for test file detection
_TEST_PATTERNS = [
    re.compile(r"(?:^|/)test_[^/]+\.py$"),       # test_*.py
    re.compile(r"(?:^|/)[^/]+_test\.py$"),         # *_test.py
    re.compile(r"(?:^|/)tests/.*\.py$"),            # tests/**/*.py
    re.compile(r"(?:^|/)spec_[^/]+\.py$"),          # spec_*.py
    re.compile(r"(?:^|/)conftest\.py$"),            # conftest.py
]

# Files that are not "source code" (don't count for verify tracking)
_NON_SOURCE_EXTENSIONS = {
    ".md", ".txt", ".yml", ".yaml", ".toml", ".json", ".cfg",
    ".ini", ".env", ".lock", ".csv", ".html", ".css",
}


def is_test_file(path: str) -> bool:
    """Check if a file path is a test file."""
    normalized = path.replace("\\", "/")
    return any(p.search(normalized) for p in _TEST_PATTERNS)


def is_source_file(path: str) -> bool:
    """Check if a file is source code (not config, docs, or test)."""
    if is_test_file(path):
        return False
    ext = Path(path).suffix.lower()
    if ext in _NON_SOURCE_EXTENSIONS:
        return False
    return ext == ".py"


def _default_state() -> dict:
    return {
        "reads": 0,
        "writes": 0,
        "source_writes": 0,
        "test_writes": 0,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def load_state() -> dict:
    """Load PEV session state from disk."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return _default_state()


def save_state(state: dict) -> None:
    """Persist PEV state to disk."""
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def reset_state() -> dict:
    """Reset PEV state for a new session."""
    state = _default_state()
    save_state(state)
    return state


def record_read(state: dict | None = None) -> dict:
    """Record a Read operation."""
    if state is None:
        state = load_state()
    state["reads"] = state.get("reads", 0) + 1
    save_state(state)
    return state


def record_write(path: str, state: dict | None = None) -> dict:
    """Record a Write/Edit operation, classifying as source or test."""
    if state is None:
        state = load_state()
    state["writes"] = state.get("writes", 0) + 1
    if is_test_file(path):
        state["test_writes"] = state.get("test_writes", 0) + 1
    elif is_source_file(path):
        state["source_writes"] = state.get("source_writes", 0) + 1
    save_state(state)
    return state


# ── PEV check functions (called by hooks) ─────────────────────


def check_plan(mode: str | None, reads: int) -> str | None:
    """Check Plan phase: has the user read code before writing?

    Returns a message string if enforcement triggers, None otherwise.
    mode: "rnd", "mixed", "bugfix", or None
    """
    if reads > 0:
        return None  # At least one read happened

    if mode == "bugfix":
        return (
            "BLOCKED — Audit before fix: read the code first "
            "(PEV: Plan phase missing)\n"
            "Use Read tool to examine the relevant code, then retry."
        )
    if mode == "mixed":
        return (
            "WARNING — No code read this session before writing. "
            "Consider reading the relevant code first (PEV: Plan)."
        )
    # R&D mode: no enforcement
    return None


def check_verify(
    mode: str | None,
    phase: str | None,
    source_writes: int,
    test_writes: int,
) -> str | None:
    """Check Verify phase: are tests being written alongside code?

    Returns a message string if enforcement triggers, None otherwise.
    """
    if source_writes < 3:
        return None  # Not enough writes to judge

    if test_writes > 0:
        return None  # Tests are being written

    # STABILIZE phase: stricter threshold
    if phase in ("STABILIZE", "DEPLOY") and source_writes >= 5:
        return (
            "BLOCKED — Phase {}: {} source files modified, 0 test files. "
            "Write tests before continuing (PEV: Verify phase missing).".format(
                phase, source_writes
            )
        )

    return (
        "WARNING — {} source files modified, 0 test files this session. "
        "Consider writing tests to verify your changes (PEV: Verify).".format(
            source_writes
        )
    )
