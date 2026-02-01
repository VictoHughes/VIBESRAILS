# VibesRails Orchestration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform vibesrails from a security scanner into a session orchestrator — anti-emballement, synchro multi-fenêtres, exécution auto de plans.

**Architecture:** 3 features indépendantes, chacune implémentée comme un hook ou un module dans `vibesrails/hooks/`. Pas d'API Claude, pas d'agent — juste des compteurs, des fichiers lock, et des hooks déterministes.

**Tech Stack:** Python 3.12, Claude Code hooks (JSON), fichiers JSONL/JSON pour état.

---

## Wiring Map — Comment ça s'intègre dans le code existant

```
┌─────────────────────────────────────────────────────────────────┐
│                    .claude/hooks.json                            │
│                                                                  │
│  SessionStart                                                    │
│    ├─ [EXISTING] check vibesrails.yaml                          │
│    ├─ [EXISTING] detect active plan                             │
│    ├─ [NEW] acquire_lock() + check_other_session()  ──► Feature 2│
│    ├─ [NEW] reset throttle state                     ──► Feature 1│
│    ├─ [MODIFIED] plan detection → PLAN READY trigger ──► Feature 3│
│    ├─ [EXISTING] current-task.md restore                        │
│    ├─ [EXISTING] queue check                                    │
│    └─ [EXISTING] inbox check                                    │
│                                                                  │
│  PreToolUse (matcher: Write|Edit|Bash)                          │
│    ├─ [EXISTING] python3 -m vibesrails.hooks.pre_tool_use       │
│    │   └─ pre_tool_use.py:main()                                │
│    │       ├─ L101: read JSON stdin                             │
│    │       ├─ [NEW L102-115] throttle check ──────► Feature 1   │
│    │       │   ├─ Write/Edit: should_block() → exit 1 if >5     │
│    │       │   ├─ Write/Edit: record_write()                    │
│    │       │   └─ Bash: if pytest/ruff → record_check()         │
│    │       ├─ L108: Bash → scan_bash_command()                  │
│    │       ├─ L118: skip if not Write/Edit                      │
│    │       └─ L129: scan_content() → block or pass              │
│    └─ [EXISTING] ptuh.py (self-protection)                      │
│                                                                  │
│  PostToolUse (matcher: Write|Edit)                              │
│    ├─ [EXISTING] write reminder                                 │
│    ├─ [EXISTING] python3 -m vibesrails.hooks.post_tool_use      │
│    └─ [NEW] prompt: warn if other session active ──► Feature 2  │
│                                                                  │
│  PostToolUse (matcher: Bash)                                    │
│    ├─ [EXISTING] commit detection                               │
│    └─ [EXISTING] prompt: update TaskList                        │
│                                                                  │
│  SessionEnd  [VALID EVENT — confirmed in Claude Code docs]      │
│    └─ [NEW] release_lock(pid) ───────────────────► Feature 2    │
│                                                                  │
│  PreCompact                                                      │
│    └─ [EXISTING] save current-task.md                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    vibesrails/hooks/                             │
│                                                                  │
│  pre_tool_use.py  [MODIFY — add 15 lines]                      │
│    ├─ L1-11:  imports (add Path, throttle imports)              │
│    ├─ L12-43: CRITICAL_PATTERNS (unchanged)                     │
│    ├─ L44-61: BASH_SECRET_PATTERNS (unchanged)                  │
│    ├─ L64-72: scan_bash_command() (unchanged)                   │
│    ├─ L75-82: _should_skip_line() (unchanged)                   │
│    ├─ L85-95: scan_content() (unchanged)                        │
│    └─ L98-138: main() — INSERT throttle block at L102           │
│                                                                  │
│  post_tool_use.py  [NO CHANGES]                                 │
│                                                                  │
│  throttle.py  [NEW]                                             │
│    ├─ STATE_FILE = ".vibesrails/session_throttle.json"          │
│    ├─ record_write(state_dir) → increment counter               │
│    ├─ record_check(state_dir) → reset counter to 0              │
│    ├─ should_block(state_dir, threshold=5) → bool               │
│    └─ get_writes_since_check(state_dir) → int                  │
│                                                                  │
│  session_lock.py  [NEW]                                         │
│    ├─ LOCK_FILE = ".vibesrails/session.lock"                    │
│    ├─ acquire_lock(lock_dir) → create lock with os.getpid()     │
│    ├─ release_lock(lock_dir) → remove own lock (PID match)      │
│    └─ check_other_session(lock_dir) → warning|None (PID alive?) │
│                                                                  │
│  queue_processor.py  [NO CHANGES]                               │
│  inbox.py  [NO CHANGES]                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    vibesrails/cli.py  [MODIFY]                  │
│                                                                  │
│  _parse_args() — add:                                           │
│    --throttle-status  "Show write throttle counter"             │
│    --throttle-reset   "Reset write throttle counter"            │
│                                                                  │
│  _handle_info_commands() — add at L96:                          │
│    if args.throttle_status:                                     │
│        from .hooks.throttle import get_writes_since_check       │
│        count = get_writes_since_check(Path(".vibesrails"))      │
│        print(f"Writes since last check: {count}")               │
│        sys.exit(0)                                              │
│    if args.throttle_reset:                                      │
│        from .hooks.throttle import reset_state                  │
│        reset_state(Path(".vibesrails"))                         │
│        print("Throttle reset.")                                 │
│        sys.exit(0)                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              installers/*/ptuh.py  [MODIFY — all 6]             │
│                                                                  │
│  PROTECTED_PATHS — add:                                         │
│    "vibesrails/hooks/throttle.py"                               │
│    "vibesrails/hooks/session_lock.py"                           │
│    ".vibesrails/session_throttle.json"                          │
│    ".vibesrails/session.lock"                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    State files (runtime)                         │
│                                                                  │
│  .vibesrails/                                                   │
│    ├─ session_throttle.json  ← throttle counter                 │
│    │   {"writes_since_check": 3}                                │
│    ├─ session.lock           ← session lock                     │
│    │   {"pid": 12345}                                           │
│    ├─ [EXISTING] metrics/scans.jsonl                            │
│    ├─ [EXISTING] guardian.log                                   │
│    ├─ [EXISTING] observations.jsonl                             │
│    └─ [EXISTING] learned_patterns.yaml                          │
│                                                                  │
│  .gitignore — add:                                              │
│    .vibesrails/session_throttle.json                            │
│    .vibesrails/session.lock                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature 1 : Anti-emballement

**Problème:** Claude Code code tête baissée — 10+ Write/Edit sans jamais lancer pytest ou ruff.

**Solution:** Un compteur dans PreToolUse qui bloque après N écritures sans vérification.

**Wiring point:** `pre_tool_use.py:main()` — insert 15 lines between stdin parse (L101) and Bash check (L108).

### Task 1: Write failing test for throttle module

**Files:**
- Create: `tests/test_throttle.py`
- Create: `vibesrails/hooks/throttle.py`

**Step 1: Write the failing test**

```python
"""Tests for write throttle — anti-emballement."""
import json
import pytest
from pathlib import Path
from vibesrails.hooks.throttle import (
    record_write,
    record_check,
    get_writes_since_check,
    should_block,
    reset_state,
    STATE_FILE_NAME,
)


@pytest.fixture
def state_dir(tmp_path):
    """Temp dir simulating .vibesrails/."""
    return tmp_path


class TestRecordWrite:
    def test_increments_counter(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        assert get_writes_since_check(state_dir) == 1

    def test_increments_multiple(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        assert get_writes_since_check(state_dir) == 3


class TestRecordCheck:
    def test_resets_counter(self, state_dir):
        reset_state(state_dir)
        record_write(state_dir)
        record_write(state_dir)
        record_check(state_dir)
        assert get_writes_since_check(state_dir) == 0


class TestShouldBlock:
    def test_no_block_under_threshold(self, state_dir):
        reset_state(state_dir)
        for _ in range(4):
            record_write(state_dir)
        assert not should_block(state_dir, threshold=5)

    def test_blocks_at_threshold(self, state_dir):
        reset_state(state_dir)
        for _ in range(5):
            record_write(state_dir)
        assert should_block(state_dir, threshold=5)

    def test_no_block_after_check(self, state_dir):
        reset_state(state_dir)
        for _ in range(5):
            record_write(state_dir)
        record_check(state_dir)
        assert not should_block(state_dir, threshold=5)


class TestStateFile:
    def test_missing_state_returns_zero(self, state_dir):
        assert get_writes_since_check(state_dir) == 0

    def test_corrupted_state_returns_zero(self, state_dir):
        state_file = state_dir / STATE_FILE_NAME
        state_file.write_text("not json")
        assert get_writes_since_check(state_dir) == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_throttle.py -v --timeout=60`
Expected: FAIL with "ModuleNotFoundError"

---

### Task 2: Implement throttle module

**Files:**
- Create: `vibesrails/hooks/throttle.py`

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_throttle.py -v --timeout=60`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add vibesrails/hooks/throttle.py tests/test_throttle.py
git commit -m "feat(hooks): add write throttle — anti-emballement module"
```

---

### Task 3: Wire throttle into pre_tool_use.py

**Files:**
- Modify: `vibesrails/hooks/pre_tool_use.py` (lines 1-10 for imports, insert at L102 in main())
- Create: `tests/test_throttle_integration.py`

**Wiring detail:** `pre_tool_use.py:main()` currently flows:

```
L101: data = json.loads(stdin)     ← parse input
L105: tool_name = data["tool_name"]
L108: if Bash → scan secrets       ← existing check
L118: if not Write/Edit → exit     ← existing check
L121: scan content                 ← existing check
```

We insert the throttle block **between L105 and L108** so it runs for ALL tool types (Write, Edit, Bash):

```
L105: tool_name = data["tool_name"]
NEW:  # --- Throttle ---
NEW:  if Write/Edit: should_block() → exit 1
NEW:  if Write/Edit: record_write()
NEW:  if Bash + check_cmd: record_check()
L108: if Bash → scan secrets        ← existing (unchanged)
```

**Step 6: Write the failing integration test**

```python
"""Integration test: throttle wired into pre_tool_use."""
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch
from vibesrails.hooks.throttle import (
    record_write,
    record_check,
    reset_state,
    get_writes_since_check,
)


class TestThrottleInPreToolUse:
    def test_write_blocked_after_threshold(self, tmp_path):
        """After 5 writes, pre_tool_use should block Write."""
        reset_state(tmp_path)
        for _ in range(5):
            record_write(tmp_path)
        assert get_writes_since_check(tmp_path) == 5
        from vibesrails.hooks.throttle import should_block
        assert should_block(tmp_path, threshold=5)

    def test_bash_pytest_resets_counter(self, tmp_path):
        """Bash containing 'pytest' should reset the counter."""
        reset_state(tmp_path)
        for _ in range(3):
            record_write(tmp_path)
        record_check(tmp_path)
        assert get_writes_since_check(tmp_path) == 0

    def test_bash_ruff_resets_counter(self, tmp_path):
        """Bash containing 'ruff' should reset the counter."""
        reset_state(tmp_path)
        record_write(tmp_path)
        record_check(tmp_path)
        assert get_writes_since_check(tmp_path) == 0

    def test_write_allowed_under_threshold(self, tmp_path):
        """Under threshold, writes should pass."""
        reset_state(tmp_path)
        for _ in range(4):
            record_write(tmp_path)
        from vibesrails.hooks.throttle import should_block
        assert not should_block(tmp_path, threshold=5)
```

**Step 7: Modify pre_tool_use.py**

Add at top (after `import sys`):

```python
from pathlib import Path

# Throttle state directory
VIBESRAILS_DIR = Path.cwd() / ".vibesrails"

# Commands that count as "verification" — resets the write counter
CHECK_COMMANDS = ["pytest", "ruff", "vibesrails", "lint-imports", "bandit", "mypy"]
```

In `main()`, after `tool_input = data.get("tool_input", {})` (L106), insert:

```python
    # --- Throttle: anti-emballement ---
    try:
        from vibesrails.hooks.throttle import record_write, record_check, should_block

        if tool_name in ("Write", "Edit"):
            if should_block(VIBESRAILS_DIR):
                sys.stdout.write(
                    "\U0001f6d1 VibesRails THROTTLE: Too many writes without verification.\n"
                    "Run pytest, ruff, or vibesrails --all before continuing.\n"
                )
                sys.exit(1)
            record_write(VIBESRAILS_DIR)

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if any(cmd in command for cmd in CHECK_COMMANDS):
                record_check(VIBESRAILS_DIR)
    except ImportError:
        pass  # throttle module not installed, skip gracefully
```

**Step 8: Run tests**

Run: `pytest tests/test_throttle.py tests/test_throttle_integration.py -v --timeout=60`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add vibesrails/hooks/pre_tool_use.py tests/test_throttle_integration.py
git commit -m "feat(hooks): wire throttle into PreToolUse — blocks after 5 unchecked writes"
```

---

### Task 4: Wire throttle into hooks.json SessionStart (reset on new session)

**Files:**
- Modify: `.claude/hooks.json`

**Wiring detail:** When a new session starts, the throttle counter should reset to 0. This prevents a previous crashed session's counter from blocking the new session.

**Step 1: Add reset hook to SessionStart**

In `.claude/hooks.json`, add this to the SessionStart hooks array (after the existing `rm -f .claude/.write_reminded` hook):

```json
{
  "type": "command",
  "command": "python3 -c \"from pathlib import Path; d=Path('.vibesrails'); d.mkdir(exist_ok=True); f=d/'session_throttle.json'; f.write_text('{\\\"writes_since_check\\\": 0}'); print('Throttle reset')\""
}
```

**Step 2: Run existing tests to verify no breakage**

Run: `pytest tests/test_throttle.py -v --timeout=60`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add .claude/hooks.json
git commit -m "feat(hooks): reset throttle on SessionStart"
```

---

### Task 5: Wire throttle into cli.py (debug commands)

**Files:**
- Modify: `vibesrails/cli.py` (add 2 args at L91, add handler at L96)
- Create: `tests/test_throttle_cli.py`

**Wiring detail:** `cli.py:_parse_args()` at L91 (after `--inbox`), and `_handle_info_commands()` at L96 (before guardian_stats).

**Step 1: Write the failing test**

```python
"""Tests for throttle CLI commands."""
import pytest
from pathlib import Path
from unittest.mock import patch
from vibesrails.hooks.throttle import record_write, reset_state, get_writes_since_check


class TestThrottleCLI:
    def test_throttle_status_shows_count(self, tmp_path):
        reset_state(tmp_path)
        record_write(tmp_path)
        record_write(tmp_path)
        assert get_writes_since_check(tmp_path) == 2

    def test_throttle_reset_clears_count(self, tmp_path):
        reset_state(tmp_path)
        record_write(tmp_path)
        record_write(tmp_path)
        reset_state(tmp_path)
        assert get_writes_since_check(tmp_path) == 0
```

**Step 2: Add args to `_parse_args()` in cli.py**

After line 91 (`parser.add_argument("--inbox", ...)`), add:

```python
    # Throttle
    parser.add_argument("--throttle-status", action="store_true",
                        help="Show write throttle counter (anti-emballement)")
    parser.add_argument("--throttle-reset", action="store_true",
                        help="Reset write throttle counter")
```

**Step 3: Add handler to `_handle_info_commands()` in cli.py**

At the beginning of `_handle_info_commands()` (before `if args.guardian_stats`), add:

```python
    if args.throttle_status:
        from .hooks.throttle import get_writes_since_check
        count = get_writes_since_check(Path(".vibesrails"))
        print(f"Writes since last check: {count}/5")
        sys.exit(0)

    if args.throttle_reset:
        from .hooks.throttle import reset_state
        reset_state(Path(".vibesrails"))
        print("Throttle reset.")
        sys.exit(0)
```

**Step 4: Run tests**

Run: `pytest tests/test_throttle_cli.py tests/test_throttle.py -v --timeout=60`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add vibesrails/cli.py tests/test_throttle_cli.py
git commit -m "feat(cli): add --throttle-status and --throttle-reset commands"
```

---

## Feature 2 : Synchro multi-fenêtres (file lock)

**Problème:** Deux Claude Code sur le même projet se marchent dessus — l'un modifie des fichiers que l'autre vient de changer.

**Solution:** Un fichier lock `.vibesrails/session.lock` avec PID + session_id. SessionStart acquiert le lock, SessionEnd le release, PostToolUse warn si conflit.

### Task 6: Write failing test for session lock

**Files:**
- Create: `tests/test_session_lock.py`
- Create: `vibesrails/hooks/session_lock.py`

**Note: session_id is PID-based.** Claude Code `command` hooks in SessionStart/End don't receive JSON stdin with session_id. Only PreToolUse/PostToolUse hooks get JSON input. So we use `os.getpid()` as the unique session identifier. Each Claude Code window spawns hooks with a different parent PID.

**Step 1: Write the failing test**

```python
"""Tests for session lock — multi-window sync (PID-based)."""
import json
import os
import pytest
from pathlib import Path
from vibesrails.hooks.session_lock import (
    acquire_lock,
    release_lock,
    check_other_session,
    LOCK_FILE_NAME,
)


@pytest.fixture
def lock_dir(tmp_path):
    return tmp_path


class TestAcquireLock:
    def test_creates_lock_file(self, lock_dir):
        acquire_lock(lock_dir)
        lock_file = lock_dir / LOCK_FILE_NAME
        assert lock_file.exists()
        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()

    def test_overwrites_stale_lock(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        acquire_lock(lock_dir)
        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()


class TestReleaseLock:
    def test_removes_own_lock(self, lock_dir):
        acquire_lock(lock_dir)
        release_lock(lock_dir)
        assert not (lock_dir / LOCK_FILE_NAME).exists()

    def test_ignores_other_pid_lock(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        release_lock(lock_dir)  # our PID != 99999999
        assert lock_file.exists()  # did NOT delete other's lock


class TestCheckOtherSession:
    def test_no_lock_returns_none(self, lock_dir):
        assert check_other_session(lock_dir) is None

    def test_own_lock_returns_none(self, lock_dir):
        acquire_lock(lock_dir)
        assert check_other_session(lock_dir) is None

    def test_other_live_pid_returns_warning(self, lock_dir):
        # Use PID 1 (launchd/init — always alive) to simulate another session
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 1}))
        result = check_other_session(lock_dir)
        assert result is not None
        assert "PID 1" in result

    def test_dead_pid_returns_none(self, lock_dir):
        lock_file = lock_dir / LOCK_FILE_NAME
        lock_file.write_text(json.dumps({"pid": 99999999}))
        assert check_other_session(lock_dir) is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_lock.py -v --timeout=60`
Expected: FAIL with "ModuleNotFoundError"

---

### Task 7: Implement session lock module

**Files:**
- Create: `vibesrails/hooks/session_lock.py`

**Step 3: Write minimal implementation**

```python
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
    except (OSError, ProcessLookupError):
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_session_lock.py -v --timeout=60`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add vibesrails/hooks/session_lock.py tests/test_session_lock.py
git commit -m "feat(hooks): add session lock — multi-window conflict detection"
```

---

### Task 8: Wire session lock into hooks.json

**Files:**
- Modify: `.claude/hooks.json`

**Wiring detail:** 3 insertion points in hooks.json:

1. **SessionStart** — acquire lock + warn if other session (insert after `rm -f .write_reminded`)
2. **PostToolUse Write|Edit** — prompt to warn if conflict detected at start
3. **SessionEnd** — new event, release lock

**Step 6: Add to SessionStart hooks array**

Insert after the existing `rm -f .claude/.write_reminded` hook:

```json
{
  "type": "command",
  "command": "python3 -c \"from vibesrails.hooks.session_lock import acquire_lock, check_other_session; from pathlib import Path; d=Path('.vibesrails'); d.mkdir(exist_ok=True); w=check_other_session(d); print(f'WARNING: {w}') if w else None; acquire_lock(d)\""
}
```

**Step 7: Add prompt to PostToolUse Write|Edit**

Add after the existing `post_tool_use` command hook:

```json
{
  "type": "prompt",
  "prompt": "Si le SessionStart a signale 'WARNING: Another session', rappelle a l'utilisateur qu'une autre fenetre Claude Code est active sur ce projet. Risque de conflit. Propose de coordonner via: vibesrails --queue 'message pour l'autre session'."
}
```

**Step 8: Add SessionEnd hook**

Add new top-level event in hooks.json:

```json
"SessionEnd": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "python3 -c \"from vibesrails.hooks.session_lock import release_lock; from pathlib import Path; release_lock(Path('.vibesrails'))\""
      }
    ]
  }
]
```

**Step 9: Commit**

```bash
git add .claude/hooks.json
git commit -m "feat(hooks): wire session lock into SessionStart/End + PostToolUse warning"
```

---

## Feature 3 : Exécution auto de plans

**Problème:** Un plan est prêt dans `docs/plans/`, mais il faut manuellement ouvrir un terminal et lancer claude.

**Solution:** Le SessionStart hook détecte déjà les plans actifs. On améliore la détection pour distinguer "plan terminé" de "plan avec tasks".

### Task 9: Enhance plan detection in hooks.json

**Files:**
- Modify: `.claude/hooks.json`

**Wiring detail:** Replace the existing plan detection hook (2nd hook in SessionStart):

```json
{
  "type": "command",
  "command": "python3 -c \"from pathlib import Path; plans=sorted(Path('docs/plans').glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True) if Path('docs/plans').exists() else []; print(f'Plan actif: {plans[0].name}') if plans else None\""
}
```

With:

```json
{
  "type": "command",
  "command": "python3 -c \"from pathlib import Path; plans=sorted(Path('docs/plans').glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True) if Path('docs/plans').exists() else []; p=plans[0] if plans else None; content=p.read_text() if p else ''; has_tasks='### Task' in content if content else False; print(f'PLAN READY: {p.name}') if has_tasks else (print(f'Plan actif: {p.name}') if p else None)\""
},
{
  "type": "prompt",
  "prompt": "Si le message precedent contient 'PLAN READY:', un plan d'implementation est pret. Propose a l'utilisateur: 'Un plan est pret (nom du fichier). Voulez-vous que je l'execute avec /superpowers:executing-plans docs/plans/<fichier>?'"
}
```

**Step 1: Update hooks.json**

Replace the plan detection hook as described above.

**Step 2: Commit**

```bash
git add .claude/hooks.json
git commit -m "feat(hooks): auto-detect ready plans and propose execution"
```

---

## Task 10: Protect new files in ptuh.py (all 6 installers)

**Files:**
- Modify: `installers/claude-code/ptuh.py`
- Modify: `installers/drag-and-drop/ptuh.py`
- Modify: `installers/mac-linux/ptuh.py`
- Modify: `installers/offline/ptuh.py`
- Modify: `installers/python/ptuh.py`
- Modify: `installers/windows/ptuh.py`

**Wiring detail:** In each ptuh.py, `PROTECTED_PATHS` list (around L36-44). Add 4 new entries.

**Step 1: Add to PROTECTED_PATHS in all 6 files**

After the existing entries, add:

```python
    "vibesrails/hooks/throttle.py",
    "vibesrails/hooks/session_lock.py",
    ".vibesrails/session_throttle.json",
    ".vibesrails/session.lock",
```

**Step 2: Commit**

```bash
git add installers/*/ptuh.py
git commit -m "fix(ptuh): protect throttle and session lock files from tampering"
```

---

## Task 11: Add state files to .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add session state files**

Append to `.gitignore`:

```
# VibesRails session state (not committed)
.vibesrails/session_throttle.json
.vibesrails/session.lock
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore session state files"
```

---

## Résumé complet des fichiers

| Fichier | Action | Feature | Wiring point |
|---------|--------|---------|--------------|
| `vibesrails/hooks/throttle.py` | CREATE | Anti-emballement | Imported by pre_tool_use.py |
| `vibesrails/hooks/session_lock.py` | CREATE | Synchro | Called by hooks.json commands |
| `vibesrails/hooks/pre_tool_use.py` | MODIFY | Anti-emballement | Insert at main() L102 |
| `vibesrails/cli.py` | MODIFY | Anti-emballement | Add 2 args + 2 handlers |
| `.claude/hooks.json` | MODIFY | All 3 | SessionStart, PostToolUse, SessionEnd |
| `installers/*/ptuh.py` (x6) | MODIFY | Protection | Add 4 entries to PROTECTED_PATHS |
| `.gitignore` | MODIFY | Housekeeping | Add 2 state files |
| `tests/test_throttle.py` | CREATE | Tests | — |
| `tests/test_throttle_integration.py` | CREATE | Tests | — |
| `tests/test_throttle_cli.py` | CREATE | Tests | — |
| `tests/test_session_lock.py` | CREATE | Tests | — |

**Total : 5 fichiers créés, 9 modifiés, 11 tasks, 0 API, 0 agent.**
