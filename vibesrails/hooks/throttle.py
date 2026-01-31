"""Write throttle — anti-emballement for Claude Code.

Counts Write/Edit operations since last verification (pytest/ruff/vibesrails).
Blocks after threshold is reached, forcing Claude to verify before continuing.

State stored in .vibesrails/session_throttle.json.
"""
import json
from pathlib import Path

STATE_FILE_NAME = "session_throttle.json"
DEFAULT_THRESHOLD = 5


def _state_path(state_dir: Path) -> Path:
    return state_dir / STATE_FILE_NAME


def _read_state(state_dir: Path) -> dict:
    path = _state_path(state_dir)
    if not path.exists():
        return {"writes_since_check": 0}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError):
        return {"writes_since_check": 0}


def _write_state(state_dir: Path, state: dict) -> None:
    path = _state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


def reset_state(state_dir: Path) -> None:
    """Reset throttle state to zero."""
    _write_state(state_dir, {"writes_since_check": 0})


def record_write(state_dir: Path) -> None:
    """Record a Write/Edit operation."""
    state = _read_state(state_dir)
    state["writes_since_check"] = state.get("writes_since_check", 0) + 1
    _write_state(state_dir, state)


def record_check(state_dir: Path) -> None:
    """Record a verification command (pytest/ruff/vibesrails). Resets counter."""
    _write_state(state_dir, {"writes_since_check": 0})


def get_writes_since_check(state_dir: Path) -> int:
    """Get current write count since last check."""
    return _read_state(state_dir).get("writes_since_check", 0)


def should_block(state_dir: Path, threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Return True if writes exceed threshold without verification."""
    return get_writes_since_check(state_dir) >= threshold
