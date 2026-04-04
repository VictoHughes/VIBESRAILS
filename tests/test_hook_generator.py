"""Tests for hook_generator — tiered Claude Code hooks generation."""

import json
import sys
import time
from unittest.mock import patch

from vibesrails.hook_generator import (
    TIERS,
    build_hooks,
    has_vibesrails_hook,
    install_hooks,
    merge_hooks,
)

# ── Tier structure tests ───────────────────────────────────────


def test_tiers_constant():
    assert TIERS == ("minimal", "standard", "full")


def test_build_minimal_has_pre_and_post():
    hooks = build_hooks("minimal")
    assert "PreToolUse" in hooks["hooks"]
    assert "PostToolUse" in hooks["hooks"]
    assert len(hooks["hooks"]) == 2


def test_build_standard_has_session_lifecycle():
    hooks = build_hooks("standard")
    events = set(hooks["hooks"].keys())
    assert {"PreToolUse", "PostToolUse", "SessionStart", "SessionEnd"} <= events


def test_build_full_has_precompact():
    hooks = build_hooks("full")
    assert "PreCompact" in hooks["hooks"]


def test_invalid_tier_raises():
    try:
        build_hooks("ultra")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "ultra" in str(e)


# ── Tier inclusion tests ──────────────────────────────────────


def test_standard_includes_minimal():
    """Standard has all events from minimal plus more."""
    minimal = build_hooks("minimal")
    standard = build_hooks("standard")
    for event in minimal["hooks"]:
        assert event in standard["hooks"]
    assert len(standard["hooks"]) > len(minimal["hooks"])


def test_full_includes_standard():
    """Full has all events from standard plus more."""
    standard = build_hooks("standard")
    full = build_hooks("full")
    for event in standard["hooks"]:
        assert event in full["hooks"]
    assert len(full["hooks"]) >= len(standard["hooks"])


# ── sys.executable tests ──────────────────────────────────────


def _collect_commands(hooks_dict: dict) -> list[str]:
    """Extract all command strings from a hooks dict."""
    commands = []
    for handlers in hooks_dict.get("hooks", {}).values():
        for handler in handlers:
            for hook in handler.get("hooks", []):
                if "command" in hook:
                    commands.append(hook["command"])
    return commands


def test_sys_executable_used_in_all_tiers():
    """No bare 'python3' — all Python commands use sys.executable."""
    for tier in TIERS:
        hooks = build_hooks(tier)
        for cmd in _collect_commands(hooks):
            if "python" in cmd.lower() and "-m " in cmd or " -c " in cmd:
                assert sys.executable in cmd, (
                    f"Tier '{tier}' has command without sys.executable: {cmd[:80]}"
                )


def test_no_hardcoded_python3():
    """Commands must not start with 'python3' or 'python'."""
    for tier in TIERS:
        hooks = build_hooks(tier)
        for cmd in _collect_commands(hooks):
            stripped = cmd.strip()
            assert not stripped.startswith("python3 "), (
                f"Tier '{tier}': hardcoded python3 in {cmd[:60]}"
            )
            assert not stripped.startswith("python "), (
                f"Tier '{tier}': hardcoded python in {cmd[:60]}"
            )


# ── Matcher tests ─────────────────────────────────────────────


def test_pre_tool_use_matcher():
    hooks = build_hooks("minimal")
    pre = hooks["hooks"]["PreToolUse"][0]
    assert pre["matcher"] == "Write|Edit|Bash"


def test_post_tool_use_write_matcher():
    hooks = build_hooks("minimal")
    post = hooks["hooks"]["PostToolUse"][0]
    assert post["matcher"] == "Write|Edit"


def test_standard_has_bash_post_tool_use():
    hooks = build_hooks("standard")
    post_groups = hooks["hooks"]["PostToolUse"]
    matchers = [g.get("matcher") for g in post_groups]
    assert "Bash" in matchers


# ── JSON serialization test ───────────────────────────────────


def test_all_tiers_json_serializable():
    for tier in TIERS:
        hooks = build_hooks(tier)
        serialized = json.dumps(hooks, indent=2)
        roundtrip = json.loads(serialized)
        assert roundtrip == hooks


# ── has_vibesrails_hook tests ─────────────────────────────────


def test_has_vibesrails_hook_positive():
    handlers = [{"hooks": [{"type": "command", "command": "python -m vibesrails.hooks.pre_tool_use"}]}]
    assert has_vibesrails_hook(handlers) is True


def test_has_vibesrails_hook_negative():
    handlers = [{"hooks": [{"type": "command", "command": "echo hello"}]}]
    assert has_vibesrails_hook(handlers) is False


def test_has_vibesrails_hook_in_prompt():
    handlers = [{"hooks": [{"type": "prompt", "prompt": "VibesRails is active"}]}]
    assert has_vibesrails_hook(handlers) is True


def test_has_vibesrails_hook_empty():
    assert has_vibesrails_hook([]) is False


# ── Merge tests ───────────────────────────────────────────────


def test_merge_new_event():
    existing = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo user"}]}]}}
    new = {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "vibesrails scan"}]}]}}
    merged = merge_hooks(existing, new)
    assert "PreToolUse" in merged["hooks"]
    assert "SessionStart" in merged["hooks"]


def test_merge_replaces_vr_hooks():
    existing = {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python -m vibesrails.hooks.old"}]},
    ]}}
    new = {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python -m vibesrails.hooks.new"}]},
    ]}}
    merged = merge_hooks(existing, new)
    commands = [h["command"] for g in merged["hooks"]["PreToolUse"] for h in g["hooks"]]
    assert "python -m vibesrails.hooks.new" in commands
    assert "python -m vibesrails.hooks.old" not in commands


def test_merge_preserves_user_hooks():
    existing = {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python -m vibesrails.hooks.old"}]},
        {"hooks": [{"type": "command", "command": "my-custom-linter check"}]},
    ]}}
    new = {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python -m vibesrails.hooks.new"}]},
    ]}}
    merged = merge_hooks(existing, new)
    commands = [h["command"] for g in merged["hooks"]["PreToolUse"] for h in g["hooks"]]
    assert "python -m vibesrails.hooks.new" in commands
    assert "my-custom-linter check" in commands
    assert "python -m vibesrails.hooks.old" not in commands


def test_merge_does_not_mutate_existing():
    existing = {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "echo original"}]},
    ]}}
    import copy
    original = copy.deepcopy(existing)
    merge_hooks(existing, {"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "vibesrails new"}]},
    ]}})
    assert existing == original


# ── Install tests ─────────────────────────────────────────────


def test_install_creates_hooks_json(tmp_path):
    path = install_hooks(tmp_path, "minimal")
    assert path.exists()
    assert path.name == "hooks.json"
    content = json.loads(path.read_text())
    assert "hooks" in content
    assert "PreToolUse" in content["hooks"]


def test_install_creates_claude_dir(tmp_path):
    install_hooks(tmp_path, "minimal")
    assert (tmp_path / ".claude").is_dir()


def test_install_idempotent(tmp_path):
    install_hooks(tmp_path, "standard")
    first = json.loads((tmp_path / ".claude" / "hooks.json").read_text())
    install_hooks(tmp_path, "standard")
    second = json.loads((tmp_path / ".claude" / "hooks.json").read_text())
    assert first == second


def test_install_merges_existing(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    existing = {"hooks": {"CustomEvent": [{"hooks": [{"type": "command", "command": "echo custom"}]}]}}
    (claude_dir / "hooks.json").write_text(json.dumps(existing))
    install_hooks(tmp_path, "minimal")
    result = json.loads((claude_dir / "hooks.json").read_text())
    assert "CustomEvent" in result["hooks"]
    assert "PreToolUse" in result["hooks"]


def test_install_full_creates_rules_reminder(tmp_path):
    install_hooks(tmp_path, "full")
    reminder = tmp_path / ".claude" / "rules_reminder.md"
    assert reminder.exists()
    assert "SCOPE" in reminder.read_text() or "CHECKPOINT" in reminder.read_text()


def test_install_full_preserves_existing_rules_reminder(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "rules_reminder.md").write_text("MY CUSTOM RULES")
    install_hooks(tmp_path, "full")
    assert (claude_dir / "rules_reminder.md").read_text() == "MY CUSTOM RULES"


def test_install_handles_corrupt_json(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "hooks.json").write_text("{invalid json")
    path = install_hooks(tmp_path, "minimal")
    content = json.loads(path.read_text())
    assert "PreToolUse" in content["hooks"]


# ── Status trigger tests ──────────────────────────────────────


def test_status_trigger_first_run_triggers(tmp_path):
    from vibesrails.hooks.status_trigger import check_and_trigger

    with patch("vibesrails.hooks.status_trigger.STATE_FILE", tmp_path / ".session_state"):
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            # First run: branch change from "" to "main" → trigger
            result = check_and_trigger()
            assert result is True


def test_status_trigger_commit_threshold(tmp_path):
    from vibesrails.hooks.status_trigger import COMMIT_THRESHOLD, check_and_trigger

    state_file = tmp_path / ".session_state"
    with patch("vibesrails.hooks.status_trigger.STATE_FILE", state_file):
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            # First call triggers (branch change), resets commits to 0
            check_and_trigger()
            # Next THRESHOLD-1 calls should NOT trigger (commits: 1,2,3,4)
            for i in range(COMMIT_THRESHOLD - 1):
                result = check_and_trigger()
                assert result is False, f"Unexpected trigger at call {i + 2}"
            # This call reaches threshold (commits: 5) → trigger
            result = check_and_trigger()
            assert result is True


def test_status_trigger_branch_change(tmp_path):
    from vibesrails.hooks.status_trigger import check_and_trigger

    state_file = tmp_path / ".session_state"
    with patch("vibesrails.hooks.status_trigger.STATE_FILE", state_file):
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            check_and_trigger()  # first run
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            result = check_and_trigger()
            assert result is False  # same branch, no trigger
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="feat/new"):
            result = check_and_trigger()
            assert result is True  # branch changed → trigger


def test_status_trigger_time_threshold(tmp_path):
    from vibesrails.hooks.status_trigger import TIME_THRESHOLD, check_and_trigger

    state_file = tmp_path / ".session_state"
    with patch("vibesrails.hooks.status_trigger.STATE_FILE", state_file):
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            check_and_trigger()  # first run, resets timer
        # Simulate time passing
        state = json.loads(state_file.read_text())
        state["last_status"] = time.time() - TIME_THRESHOLD - 1
        state_file.write_text(json.dumps(state))
        with patch("vibesrails.hooks.status_trigger._get_branch", return_value="main"):
            result = check_and_trigger()
            assert result is True


# ── Hook content tests ────────────────────────────────────────


def test_standard_session_start_has_scan():
    hooks = build_hooks("standard")
    start_hooks = hooks["hooks"]["SessionStart"][0]["hooks"]
    commands = [h.get("command", "") for h in start_hooks]
    assert any("session_scan" in c for c in commands)


def test_standard_has_status_trigger():
    hooks = build_hooks("standard")
    bash_groups = [g for g in hooks["hooks"]["PostToolUse"] if g.get("matcher") == "Bash"]
    assert len(bash_groups) == 1
    commands = [h.get("command", "") for h in bash_groups[0]["hooks"]]
    assert any("status_trigger" in c for c in commands)


def test_full_has_discipline_prompt():
    hooks = build_hooks("full")
    start_hooks = hooks["hooks"]["SessionStart"][0]["hooks"]
    prompts = [h.get("prompt", "") for h in start_hooks]
    assert any("DISCIPLINE" in p for p in prompts)


def test_full_has_scope_check():
    hooks = build_hooks("full")
    bash_groups = [g for g in hooks["hooks"]["PostToolUse"] if g.get("matcher") == "Bash"]
    prompts = [h.get("prompt", "") for h in bash_groups[0]["hooks"]]
    assert any("SCOPE CHECK" in p for p in prompts)


def test_full_has_plan_detection():
    hooks = build_hooks("full")
    start_hooks = hooks["hooks"]["SessionStart"][0]["hooks"]
    commands = [h.get("command", "") for h in start_hooks]
    assert any("docs/plans" in c for c in commands)
