"""Tests for PEV tracker — Plan→Execute→Verify session tracking."""

from unittest.mock import patch

from vibesrails.pev_tracker import (
    check_plan,
    check_verify,
    is_source_file,
    is_test_file,
    load_state,
    record_read,
    record_write,
    reset_state,
)

# ── is_test_file tests ────────────────────────────────────────


def test_test_file_test_prefix():
    assert is_test_file("test_foo.py") is True
    assert is_test_file("tests/test_foo.py") is True
    assert is_test_file("src/tests/test_bar.py") is True


def test_test_file_test_suffix():
    assert is_test_file("foo_test.py") is True
    assert is_test_file("src/bar_test.py") is True


def test_test_file_tests_dir():
    assert is_test_file("tests/utils.py") is True
    assert is_test_file("tests/conftest.py") is True


def test_test_file_conftest():
    assert is_test_file("conftest.py") is True
    assert is_test_file("src/conftest.py") is True


def test_test_file_spec_prefix():
    assert is_test_file("spec_auth.py") is True


def test_not_test_file():
    assert is_test_file("models.py") is False
    assert is_test_file("config.py") is False
    assert is_test_file("src/main.py") is False
    assert is_test_file("utils/helpers.py") is False


# ── is_source_file tests ──────────────────────────────────────


def test_source_file_py():
    assert is_source_file("app.py") is True
    assert is_source_file("src/main.py") is True


def test_source_file_not_test():
    assert is_source_file("test_app.py") is False
    assert is_source_file("tests/test_app.py") is False


def test_source_file_not_config():
    assert is_source_file("config.yaml") is False
    assert is_source_file("README.md") is False
    assert is_source_file("pyproject.toml") is False


# ── Session state tests ───────────────────────────────────────


def test_session_state_init(tmp_path):
    with patch("vibesrails.pev_tracker.STATE_FILE", tmp_path / ".pev_state"):
        state = load_state()
        assert state["reads"] == 0
        assert state["writes"] == 0
        assert state["source_writes"] == 0
        assert state["test_writes"] == 0


def test_session_reset(tmp_path):
    state_file = tmp_path / ".pev_state"
    with patch("vibesrails.pev_tracker.STATE_FILE", state_file):
        with patch("vibesrails.pev_tracker.STATE_DIR", tmp_path):
            state = reset_state()
            assert state["reads"] == 0
            assert state_file.exists()


def test_increment_reads(tmp_path):
    state_file = tmp_path / ".pev_state"
    with patch("vibesrails.pev_tracker.STATE_FILE", state_file):
        with patch("vibesrails.pev_tracker.STATE_DIR", tmp_path):
            state = record_read()
            assert state["reads"] == 1
            state = record_read()
            assert state["reads"] == 2


def test_increment_writes_source(tmp_path):
    state_file = tmp_path / ".pev_state"
    with patch("vibesrails.pev_tracker.STATE_FILE", state_file):
        with patch("vibesrails.pev_tracker.STATE_DIR", tmp_path):
            state = record_write("src/app.py")
            assert state["writes"] == 1
            assert state["source_writes"] == 1
            assert state["test_writes"] == 0


def test_increment_writes_test(tmp_path):
    state_file = tmp_path / ".pev_state"
    with patch("vibesrails.pev_tracker.STATE_FILE", state_file):
        with patch("vibesrails.pev_tracker.STATE_DIR", tmp_path):
            state = record_write("tests/test_app.py")
            assert state["writes"] == 1
            assert state["source_writes"] == 0
            assert state["test_writes"] == 1


def test_increment_writes_config(tmp_path):
    """Config files count as writes but not source or test."""
    state_file = tmp_path / ".pev_state"
    with patch("vibesrails.pev_tracker.STATE_FILE", state_file):
        with patch("vibesrails.pev_tracker.STATE_DIR", tmp_path):
            state = record_write("config.yaml")
            assert state["writes"] == 1
            assert state["source_writes"] == 0
            assert state["test_writes"] == 0


# ── check_plan tests ──────────────────────────────────────────


def test_read_before_write_bugfix_blocks():
    msg = check_plan("bugfix", reads=0)
    assert msg is not None
    assert "BLOCKED" in msg


def test_read_before_write_bugfix_passes():
    msg = check_plan("bugfix", reads=1)
    assert msg is None


def test_read_before_write_rnd_no_block():
    msg = check_plan("rnd", reads=0)
    assert msg is None


def test_read_before_write_mixed_warns():
    msg = check_plan("mixed", reads=0)
    assert msg is not None
    assert "WARNING" in msg


def test_read_before_write_mixed_passes():
    msg = check_plan("mixed", reads=1)
    assert msg is None


# ── check_verify tests ────────────────────────────────────────


def test_verify_no_warning_few_writes():
    msg = check_verify("mixed", "FLESH_OUT", source_writes=2, test_writes=0)
    assert msg is None


def test_verify_warning_after_3_writes_no_test():
    msg = check_verify("mixed", "FLESH_OUT", source_writes=3, test_writes=0)
    assert msg is not None
    assert "WARNING" in msg


def test_verify_no_warning_when_tests_written():
    msg = check_verify("mixed", "FLESH_OUT", source_writes=5, test_writes=1)
    assert msg is None


def test_stabilize_blocks_after_5_writes_no_test():
    msg = check_verify("mixed", "STABILIZE", source_writes=5, test_writes=0)
    assert msg is not None
    assert "BLOCKED" in msg


def test_stabilize_no_block_under_5():
    msg = check_verify("mixed", "STABILIZE", source_writes=4, test_writes=0)
    assert msg is not None
    assert "WARNING" in msg  # warning, not blocked


def test_deploy_blocks_after_5_writes_no_test():
    msg = check_verify("mixed", "DEPLOY", source_writes=5, test_writes=0)
    assert msg is not None
    assert "BLOCKED" in msg


# ── Hook generator integration ────────────────────────────────


def test_standard_has_read_hook():
    """Standard tier includes Read matcher for PEV tracking."""
    from vibesrails.hook_generator import build_hooks

    hooks = build_hooks("standard")
    pre_groups = hooks["hooks"]["PreToolUse"]
    matchers = [g.get("matcher") for g in pre_groups]
    assert "Read" in matchers


def test_standard_has_pev_reset():
    """Standard tier SessionStart resets PEV state."""
    from vibesrails.hook_generator import build_hooks

    hooks = build_hooks("standard")
    start_hooks = hooks["hooks"]["SessionStart"][0]["hooks"]
    commands = [h.get("command", "") for h in start_hooks]
    assert any("pev_tracker" in c and "reset_state" in c for c in commands)


# ── Status integration ────────────────────────────────────────


def test_status_pev_section_shown():
    from vibesrails.status import format_full

    data = {
        "version": "2.3.0",
        "git": {"branch": "main", "dirty_count": 0, "unpushed": 0},
        "context": {
            "mode": "Mixed", "mode_score": 0.5, "mode_confidence": "high",
            "phase": "FLESH OUT", "phase_num": 2, "phase_total": 4,
            "phase_missing": [], "phase_is_override": False,
        },
        "gates": {"met": 2, "total": 2, "all_met": True, "target": None},
        "assertions": {"passed": 4, "total": 4},
        "docs": {"claude_md": "synced", "decisions": True},
        "tests": {"declared": 100},
        "openspec": {"detected": False, "spec_count": 0, "pending_count": 0,
                     "pending_names": [], "archived_count": 0},
        "pev": {"reads": 5, "writes": 3, "source_writes": 2, "test_writes": 1},
    }
    output = format_full(data)
    assert "PEV LOOP" in output
    assert "Reads" in output
    assert "test coverage active" in output


def test_status_pev_hidden_when_no_writes():
    from vibesrails.status import format_full

    data = {
        "version": "2.3.0",
        "git": {"branch": "main", "dirty_count": 0, "unpushed": 0},
        "context": {
            "mode": "Mixed", "mode_score": 0.5, "mode_confidence": "high",
            "phase": "DECIDE", "phase_num": 0, "phase_total": 4,
            "phase_missing": [], "phase_is_override": False,
        },
        "gates": {"met": 0, "total": 0, "all_met": True, "target": None},
        "assertions": {"passed": 0, "total": 0},
        "docs": {"claude_md": "synced", "decisions": True},
        "tests": {"declared": 0},
        "openspec": {"detected": False, "spec_count": 0, "pending_count": 0,
                     "pending_names": [], "archived_count": 0},
        "pev": {"reads": 0, "writes": 0, "source_writes": 0, "test_writes": 0},
    }
    output = format_full(data)
    assert "PEV" not in output
