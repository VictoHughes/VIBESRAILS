"""Session lock — prevent multi-window conflicts.

Creates .vibesrails/session.lock with PID of the current process.
Uses PID as unique session identifier because SessionStart/End command hooks
don't receive JSON stdin (only PreToolUse/PostToolUse do).
"""
import json
import os
from pathlib import Path

LOCK_FILE_NAME = "session.lock"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we lack permission to signal it
    except OSError:
        return False


def acquire_lock(lock_dir: Path) -> None:
    """Create or overwrite lock file with current PID."""
    lock_file = lock_dir / LOCK_FILE_NAME
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"pid": os.getpid()}))


def release_lock(lock_dir: Path) -> None:
    """Remove lock file only if it belongs to current PID."""
    lock_file = lock_dir / LOCK_FILE_NAME
    if not lock_file.exists():
        return
    try:
        data = json.loads(lock_file.read_text())
        if data.get("pid") == os.getpid():
            lock_file.unlink()
    except (json.JSONDecodeError, ValueError):
        lock_file.unlink()


def check_other_session(lock_dir: Path) -> str | None:
    """Check if another live process holds the lock. Returns warning or None."""
    lock_file = lock_dir / LOCK_FILE_NAME
    if not lock_file.exists():
        return None
    try:
        data = json.loads(lock_file.read_text())
    except (json.JSONDecodeError, ValueError):
        return None

    other_pid = data.get("pid", 0)

    if other_pid == os.getpid():
        return None
    if not _is_pid_alive(other_pid):
        return None

    return f"Another session (PID {other_pid}) is active on this project."
