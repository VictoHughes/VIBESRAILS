"""Hook generator — tiered Claude Code hooks.json for VibesRails.

Tiers:
  minimal  — PreToolUse + PostToolUse security scanning only
  standard — + SessionStart/End, throttle, session lock, status trigger
  full     — + discipline prompts, plan detection, inbox, queue, scope check

Usage:
  vibesrails --init-hooks             # standard tier (default)
  vibesrails --init-hooks minimal     # security hooks only
  vibesrails --init-hooks full        # full methodology enforcement
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

TIERS = ("minimal", "standard", "full")
_VR_MARKER = "vibesrails"


# ── Hook building helpers ──────────────────────────────────────


def _py(module: str) -> str:
    """Build: /path/to/python -m module."""
    return f"{sys.executable} -m {module}"


def _pyc(code: str) -> str:
    """Build: /path/to/python -c 'code' with shell-safe quoting."""
    escaped = code.replace("'", "'\"'\"'")
    return f"{sys.executable} -c '{escaped}'"


def _cmd(command: str) -> dict:
    return {"type": "command", "command": command}


def _prompt(text: str) -> dict:
    return {"type": "prompt", "prompt": text}


def _group(hooks: list[dict], matcher: str | None = None) -> dict:
    g: dict = {"hooks": hooks}
    if matcher:
        g["matcher"] = matcher
    return g


# ── Inline code snippets ──────────────────────────────────────
# Kept as constants to avoid string-building sprawl in tier builders.

_THROTTLE_RESET = (
    "from pathlib import Path; import json; "
    "d=Path('.vibesrails'); d.mkdir(exist_ok=True); "
    "f=d/'session_throttle.json'; "
    "f.write_text(json.dumps({'writes_since_check': 0})); "
    "print('Throttle reset')"
)

_SESSION_LOCK_ACQUIRE = (
    "from vibesrails.hooks.session_lock import acquire_lock, check_other_session; "
    "from pathlib import Path; "
    "d=Path('.vibesrails'); d.mkdir(exist_ok=True); "
    "w=check_other_session(d); "
    "print(f'WARNING: {w}') if w else None; "
    "acquire_lock(d)"
)

_SESSION_LOCK_RELEASE = (
    "from vibesrails.hooks.session_lock import release_lock; "
    "from pathlib import Path; "
    "release_lock(Path('.vibesrails'))"
)

_COMMIT_DETECT = (
    "from pathlib import Path; import subprocess; "
    "d=Path('.claude'); d.mkdir(exist_ok=True); "
    "f=d/'.last_commit_hash'; "
    "old=f.read_text().strip() if f.exists() else ''; "
    "new=subprocess.run(['git','rev-parse','HEAD'],"
    "capture_output=True,text=True).stdout.strip() "
    "if Path('.git').exists() else ''; "
    "changed=old and new and old!=new; "
    "f.write_text(new) if new else None; "
    "print('New commit detected') if changed else None"
)

_WRITE_REMINDER = (
    "from pathlib import Path; "
    "d=Path('.claude'); d.mkdir(exist_ok=True); "
    "f=d/'.write_reminded'; "
    "showed=(print('vibesrails: Code will be scanned on commit') or True) "
    "if not f.exists() and Path('vibesrails.yaml').exists() else False; "
    "f.touch() if showed else None"
)

_PLAN_DETECT = (
    "from pathlib import Path; "
    "plans=sorted(Path('docs/plans').glob('*.md'), "
    "key=lambda p: p.stat().st_mtime, reverse=True) "
    "if Path('docs/plans').exists() else []; "
    "p=plans[0] if plans else None; "
    "content=p.read_text() if p else ''; "
    "has_tasks='### Task' in content if content else False; "
    "print(f'PLAN READY: {p.name}') if has_tasks "
    "else (print(f'Active plan: {p.name}') if p else None)"
)

_TASK_RESTORE = (
    "from pathlib import Path; "
    "p=Path('.claude/current-task.md'); "
    "print(f'Current task: {p.read_text().strip()[:80]}...') "
    "if p.exists() and p.read_text().strip() else None"
)

_QUEUE_CHECK = (
    "from vibesrails.hooks.queue_processor import format_pending_summary; "
    "from pathlib import Path; "
    "s=format_pending_summary(Path('.claude/queue.jsonl')); "
    "print(s) if s else None"
)

_INBOX_CHECK = (
    "from vibesrails.hooks.inbox import check_inbox; "
    "from pathlib import Path; "
    "c=check_inbox(Path('.claude/inbox.md')); "
    "print(f'Inbox instructions:\\n{c}') if c else None"
)


# ── Tier builders ──────────────────────────────────────────────


def _minimal() -> dict[str, list]:
    """Tier 1: Core security hooks only."""
    return {
        "PreToolUse": [
            _group(
                [_cmd(_py("vibesrails.hooks.pre_tool_use"))],
                "Write|Edit|Bash",
            ),
        ],
        "PostToolUse": [
            _group(
                [_cmd(_py("vibesrails.hooks.post_tool_use"))],
                "Write|Edit",
            ),
        ],
    }


def _standard() -> dict[str, list]:
    """Tier 2: Security + session management + status trigger."""
    hooks = _minimal()

    # SessionStart
    hooks["SessionStart"] = [_group([
        _cmd(_py("vibesrails.hooks.session_scan")),
        _prompt(
            "VibesRails is active on this project. "
            "Report the session scan results (files, blocking, warnings) to the user. "
            "If BLOCKING issues exist, flag them immediately."
        ),
        _cmd(_pyc(_THROTTLE_RESET)),
        _cmd(_pyc(_SESSION_LOCK_ACQUIRE)),
        _cmd(
            "rm -f .claude/.write_reminded 2>/dev/null; "
            "mkdir -p .claude; "
            "git rev-parse HEAD 2>/dev/null > .claude/.last_commit_hash || true"
        ),
    ])]

    # PostToolUse Bash: commit detection + scan + status trigger
    hooks["PostToolUse"].append(
        _group([
            _cmd(_pyc(_COMMIT_DETECT)),
            _cmd(_py("vibesrails.hooks.post_tool_use")),
            _cmd(_py("vibesrails.hooks.status_trigger")),
        ], "Bash"),
    )

    # SessionEnd
    hooks["SessionEnd"] = [_group([
        _cmd(_pyc(_SESSION_LOCK_RELEASE)),
    ])]

    return hooks


def _full() -> dict[str, list]:
    """Tier 3: Full methodology enforcement."""
    hooks = _standard()

    # ── Extend SessionStart ──
    start_hooks = hooks["SessionStart"][0]["hooks"]
    start_hooks.extend([
        _prompt(
            "SESSION DISCIPLINE: "
            "1) ARCHITECTURE — Check import rules in pyproject.toml before modifying files. "
            "2) ZERO DUPLICATION — Search codebase before writing. Reuse existing modules. "
            "3) STRUCTURED METHOD — Plan before coding for non-trivial tasks. "
            "4) VERIFICATION — Run tests after every modification."
        ),
        _cmd(_pyc(_PLAN_DETECT)),
        _prompt(
            "If the previous message contains 'PLAN READY:', "
            "ask if the user wants to execute the implementation plan."
        ),
        _cmd(_pyc(_TASK_RESTORE)),
        _prompt(
            "If .claude/current-task.md contains tasks, "
            "recreate the TaskList from its content to restore state."
        ),
        _cmd(_pyc(_QUEUE_CHECK)),
        _cmd(_pyc(_INBOX_CHECK)),
        _prompt(
            "If 'Inbox instructions:' appeared, process them then clear the inbox."
        ),
    ])

    # ── PreCompact ──
    hooks["PreCompact"] = [_group([
        _prompt(
            "BEFORE COMPACTION: Save state to .claude/current-task.md: "
            "1) Active plan, 2) Current step, 3) Next actions, 4) TaskList status."
        ),
    ])]

    # ── Enhance PostToolUse Write|Edit ──
    write_hooks = hooks["PostToolUse"][0]["hooks"]
    write_hooks.insert(0, _cmd(_pyc(_WRITE_REMINDER)))
    write_hooks.append(_prompt(
        "If SessionStart reported 'WARNING: Another session', "
        "remind the user another Claude Code window is active."
    ))

    # ── Enhance PostToolUse Bash ──
    bash_hooks = hooks["PostToolUse"][1]["hooks"]
    bash_hooks.extend([
        _cmd("cat .claude/rules_reminder.md 2>/dev/null || true"),
        _prompt(
            "SCOPE CHECK: A commit was just made. "
            "If the user did not explicitly request this or the next change, "
            "STOP and ASK permission before continuing."
        ),
    ])

    return hooks


# ── Public API ─────────────────────────────────────────────────

_BUILDERS = {"minimal": _minimal, "standard": _standard, "full": _full}


def build_hooks(tier: str = "standard") -> dict:
    """Generate hooks.json content for the given tier.

    Returns a dict ready for json.dumps().
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Choose from: {', '.join(TIERS)}")
    return {"hooks": _BUILDERS[tier]()}


def has_vibesrails_hook(handlers: list[dict]) -> bool:
    """Check if a list of handler groups contains any vibesrails hook."""
    for handler in handlers:
        for hook in handler.get("hooks", []):
            content = hook.get("command", "") + hook.get("prompt", "")
            if _VR_MARKER in content.lower():
                return True
    return False


def merge_hooks(existing: dict, new_hooks: dict) -> dict:
    """Merge new VR hooks into existing config.

    Strategy: for each event, replace all VR handlers with new ones,
    preserve any user-added (non-VR) handlers.
    """
    result = json.loads(json.dumps(existing))  # deep copy

    for event, new_handlers in new_hooks.get("hooks", {}).items():
        if event not in result.get("hooks", {}):
            result.setdefault("hooks", {})[event] = new_handlers
        else:
            # Separate user handlers from VR handlers
            user_handlers = []
            for handler in result["hooks"][event]:
                is_vr = any(
                    _VR_MARKER in (h.get("command", "") + h.get("prompt", "")).lower()
                    for h in handler.get("hooks", [])
                )
                if not is_vr:
                    user_handlers.append(handler)
            # VR first, then user
            result["hooks"][event] = new_handlers + user_handlers

    return result


def install_hooks(root: Path, tier: str = "standard") -> Path:
    """Generate and install hooks.json to .claude/ directory.

    - Creates .claude/ if needed
    - Merges with existing hooks.json (preserves user hooks)
    - Returns path to the written file
    """
    claude_dir = root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    hooks_path = claude_dir / "hooks.json"

    new_hooks = build_hooks(tier)

    if hooks_path.exists():
        try:
            existing = json.loads(hooks_path.read_text())
            merged = merge_hooks(existing, new_hooks)
        except (json.JSONDecodeError, OSError):
            merged = new_hooks
    else:
        merged = new_hooks

    hooks_path.write_text(json.dumps(merged, indent=2) + "\n")

    # Install rules_reminder.md (used by full tier scope check,
    # but always installed so --setup behavior is preserved)
    _install_rules_reminder(claude_dir)

    return hooks_path


def _install_rules_reminder(claude_dir: Path) -> None:
    """Install rules_reminder.md if not present."""
    dest = claude_dir / "rules_reminder.md"
    if dest.exists():
        return
    dest.write_text(
        "POST-COMMIT CHECKPOINT\n\n"
        "1. STOP — did the user explicitly request this commit?\n"
        "2. Is the next change within declared SCOPE?\n"
        "3. \"audit\"/\"diagnose\" = READ only, 0 modifications\n"
        "4. \"fix X\" = fix X, NOTHING else\n"
        "5. No additional commits without user validation\n\n"
        "When in doubt -> ASK before continuing.\n"
    )
