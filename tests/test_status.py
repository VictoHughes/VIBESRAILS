"""Tests for vibesrails --status unified report."""

import json

from vibesrails.status import (
    collect_status,
    exit_code,
    format_full,
    format_json,
    format_quiet,
)

# ── Mock data ──────────────────────────────────────────────────


def _mock_status():
    """Standard mock status data."""
    return {
        "version": "2.3.0",
        "git": {"branch": "main", "dirty_count": 2, "unpushed": 1},
        "context": {
            "mode": "Mixed", "mode_score": 0.55, "mode_confidence": "high",
            "phase": "STABILIZE", "phase_num": 3, "phase_total": 4,
            "phase_missing": ["has_monitoring"], "phase_is_override": False,
        },
        "gates": {"met": 3, "total": 4, "all_met": False, "target": "DEPLOY"},
        "assertions": {"passed": 4, "total": 4},
        "docs": {"claude_md": "synced", "decisions": True},
        "tests": {"declared": 2320},
    }


def _clean_status():
    """All-green mock status."""
    return {
        "version": "2.3.0",
        "git": {"branch": "main", "dirty_count": 0, "unpushed": 0},
        "context": {
            "mode": "R&D", "mode_score": 0.80, "mode_confidence": "high",
            "phase": "FLESH OUT", "phase_num": 2, "phase_total": 4,
            "phase_missing": [], "phase_is_override": False,
        },
        "gates": {"met": 4, "total": 4, "all_met": True, "target": None},
        "assertions": {"passed": 4, "total": 4},
        "docs": {"claude_md": "synced", "decisions": True},
        "tests": {"declared": 2320},
    }


# ── format_quiet tests ────────────────────────────────────────


def test_quiet_under_500_chars():
    output = format_quiet(_mock_status())
    assert len(output) < 500, f"Quiet output too long: {len(output)} chars"


def test_quiet_contains_key_info():
    output = format_quiet(_mock_status())
    assert "VR 2.3.0" in output
    assert "main" in output
    assert "Mixed" in output
    assert "STABILIZE" in output
    assert "gates" in output


def test_quiet_shows_dirty():
    output = format_quiet(_mock_status())
    assert "2 dirty" in output


def test_quiet_shows_unpushed():
    output = format_quiet(_mock_status())
    assert "+1 unpushed" in output


def test_quiet_clean_no_dirty():
    output = format_quiet(_clean_status())
    assert "dirty" not in output
    assert "unpushed" not in output


def test_quiet_shows_missing_gates():
    output = format_quiet(_mock_status())
    assert "has_monitoring" in output


def test_quiet_override_flag():
    data = _mock_status()
    data["context"]["phase_is_override"] = True
    output = format_quiet(data)
    assert "[override]" in output


# ── format_full tests ─────────────────────────────────────────


def test_full_has_sections():
    output = format_full(_mock_status())
    assert "REPO" in output
    assert "CONTEXT" in output
    assert "TESTS" in output
    assert "DOCS" in output
    assert "ACTIONS" in output


def test_full_shows_branch():
    output = format_full(_mock_status())
    assert "main" in output


def test_full_shows_mode_and_phase():
    output = format_full(_mock_status())
    assert "Mixed" in output
    assert "STABILIZE" in output


def test_full_shows_actions():
    output = format_full(_mock_status())
    assert "uncommitted" in output
    assert "not pushed" in output


def test_full_clean_no_blockers():
    output = format_full(_clean_status())
    assert "ready to code" in output


# ── format_json tests ─────────────────────────────────────────


def test_json_roundtrip():
    data = _mock_status()
    output = format_json(data)
    parsed = json.loads(output)
    assert parsed["version"] == "2.3.0"
    assert parsed["git"]["branch"] == "main"


def test_json_has_all_keys():
    data = _mock_status()
    output = format_json(data)
    parsed = json.loads(output)
    assert set(parsed.keys()) == {"version", "git", "context", "gates", "assertions", "docs", "tests"}


# ── exit_code tests ───────────────────────────────────────────


def test_exit_code_clean():
    assert exit_code(_clean_status()) == 0


def test_exit_code_warnings():
    data = _clean_status()
    data["git"]["dirty_count"] = 3
    assert exit_code(data) == 1


def test_exit_code_partial_assertions_is_warning():
    data = _clean_status()
    data["assertions"]["passed"] = 2  # partial
    assert exit_code(data) == 1


def test_exit_code_zero_assertions_is_blocker():
    data = _clean_status()
    data["assertions"]["passed"] = 0
    assert exit_code(data) == 2


# ── collect_status tests ──────────────────────────────────────


def test_collect_status_returns_all_keys(tmp_path):
    """collect_status returns the expected structure (graceful in empty dir)."""
    data = collect_status(tmp_path)
    assert "version" in data
    assert "git" in data
    assert "context" in data
    assert "gates" in data
    assert "assertions" in data
    assert "docs" in data
    assert "tests" in data


def test_collect_status_git_fallback(tmp_path):
    """Non-git directory returns sensible defaults."""
    data = collect_status(tmp_path)
    assert data["git"]["branch"] in ("?", "")


# ── Hook generator integration ────────────────────────────────


def test_session_start_has_status_quiet():
    """Standard tier SessionStart includes --status --quiet."""
    from vibesrails.hook_generator import build_hooks

    hooks = build_hooks("standard")
    start_hooks = hooks["hooks"]["SessionStart"][0]["hooks"]
    commands = [h.get("command", "") for h in start_hooks]
    assert any("--status" in c and "--quiet" in c for c in commands), (
        "SessionStart missing --status --quiet command"
    )
