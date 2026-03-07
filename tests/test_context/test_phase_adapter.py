"""Tests for phase-aware adapter and hook guards."""

import copy
import json

from vibesrails.context.adapter import (
    PHASE_PROFILES,
    ContextAdapter,
)
from vibesrails.context.mode import SessionMode
from vibesrails.context.phase import ProjectPhase

# ============================================
# PHASE_PROFILES constants
# ============================================


def test_phase_profiles_decide_has_blocks():
    """DECIDE phase has blocking flags."""
    profile = PHASE_PROFILES[ProjectPhase.DECIDE]
    assert profile["block_without_adr"] is True
    assert profile["block_without_contracts"] is True


def test_phase_profiles_skeleton_has_test_first():
    """SKELETON phase has test-first warning."""
    profile = PHASE_PROFILES[ProjectPhase.SKELETON]
    assert profile["warn_test_first"] is True


def test_phase_profiles_stabilize_is_strict():
    """STABILIZE phase has strict thresholds."""
    profile = PHASE_PROFILES[ProjectPhase.STABILIZE]
    assert profile["file_too_long"]["threshold"] == 300
    assert profile["block_new_features"] is True


def test_phase_profiles_deploy_has_diff_limit():
    """DEPLOY phase limits diff size."""
    profile = PHASE_PROFILES[ProjectPhase.DEPLOY]
    assert profile["diff_size"]["warn"] == 50
    assert profile["diff_size"]["block"] == 100


# ============================================
# ContextAdapter.get_phase_profile
# ============================================


def test_get_phase_profile_returns_copy():
    """Each call returns a fresh copy."""
    adapter = ContextAdapter()
    p1 = adapter.get_phase_profile(ProjectPhase.DECIDE)
    p2 = adapter.get_phase_profile(ProjectPhase.DECIDE)
    assert p1 == p2
    p1["block_without_adr"] = False
    assert p2["block_without_adr"] is True


def test_get_phase_profile_flesh_out():
    """FLESH_OUT has warn_test_first."""
    adapter = ContextAdapter()
    profile = adapter.get_phase_profile(ProjectPhase.FLESH_OUT)
    assert profile["warn_test_first"] is True


# ============================================
# ContextAdapter.adapt_full_config
# ============================================


def test_adapt_full_config_mode_then_phase():
    """Phase overrides mode on conflict."""
    config = {"complexity": {"max_file_lines": 400}}
    adapter = ContextAdapter()
    # RND sets threshold=600, STABILIZE sets threshold=300
    adapted = adapter.adapt_full_config(
        SessionMode.RND, ProjectPhase.STABILIZE, config
    )
    # Phase wins: 300 < 600
    assert adapted["complexity"]["max_file_lines"] == 300


def test_adapt_full_config_no_mutation():
    """Original config is not mutated."""
    config = {"complexity": {"max_file_lines": 400}}
    config_copy = copy.deepcopy(config)
    adapter = ContextAdapter()
    adapter.adapt_full_config(SessionMode.RND, ProjectPhase.DECIDE, config)
    assert config == config_copy


def test_adapt_full_config_stores_phase_flags():
    """Phase flags are stored in adapted config for hooks."""
    config = {}
    adapter = ContextAdapter()
    adapted = adapter.adapt_full_config(
        SessionMode.MIXED, ProjectPhase.DECIDE, config
    )
    assert adapted["_phase"] == ProjectPhase.DECIDE.value
    assert adapted["_phase_flags"]["block_without_adr"] is True
    assert adapted["_phase_flags"]["block_without_contracts"] is True


def test_adapt_full_config_empty_phase():
    """Phase with no overrides preserves mode config."""
    config = {"complexity": {"max_file_lines": 400}}
    adapter = ContextAdapter()
    # FLESH_OUT has no threshold overrides, just warn_test_first
    adapted = adapter.adapt_full_config(
        SessionMode.RND, ProjectPhase.FLESH_OUT, config
    )
    # Mode's threshold preserved
    assert adapted["complexity"]["max_file_lines"] == 600


def test_adapt_full_config_deploy_diff_size():
    """DEPLOY phase applies diff_size to guardian config."""
    config = {}
    adapter = ContextAdapter()
    adapted = adapter.adapt_full_config(
        SessionMode.MIXED, ProjectPhase.DEPLOY, config
    )
    assert adapted["guardian"]["diff_size_warn"] == 50
    assert adapted["guardian"]["diff_size_block"] == 100


def test_adapt_full_config_brief_enforcer_merge():
    """Phase brief_enforcer merges with mode brief_enforcer."""
    config = {}
    adapter = ContextAdapter()
    # RND has min_score=30, DECIDE has min_score=80
    adapted = adapter.adapt_full_config(
        SessionMode.RND, ProjectPhase.DECIDE, config
    )
    # Phase wins
    assert adapted["brief_enforcer"]["min_score"] == 80


# ============================================
# pre_tool_use phase blocking
# ============================================


def test_pre_tool_use_blocks_without_adr(tmp_path):
    """Pre-tool blocks Write in DECIDE phase (override) when ADR is missing."""
    import subprocess
    import sys

    import yaml

    # Force DECIDE phase via methodology.yaml (blocking requires override)
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(yaml.dump({"methodology": {"current_phase": 0}}))
    (tmp_path / "README.md").write_text("# Project")

    hook_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_path / "app.py"),
            "content": "print('hello')\n",
        },
    })

    result = subprocess.run(
        [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert result.returncode == 1
    assert "ADR" in result.stdout


def test_pre_tool_use_passes_with_adr(tmp_path):
    """Pre-tool allows Write in DECIDE phase (override) when ADR + contracts exist."""
    import subprocess
    import sys

    import yaml

    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(yaml.dump({"methodology": {"current_phase": 0}}))
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "ADR").mkdir()
    (tmp_path / "ADR" / "001.md").write_text("# ADR")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    for i in range(3):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    hook_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_path / "pkg" / "new.py"),
            "content": "x = 1\n",
        },
    })

    result = subprocess.run(
        [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert result.returncode == 0


def test_pre_tool_use_blocks_new_file_in_stabilize(tmp_path):
    """Pre-tool blocks new .py files in STABILIZE phase (override)."""
    import subprocess
    import sys

    import yaml

    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(yaml.dump({"methodology": {"current_phase": 3}}))

    new_file = tmp_path / "new_feature.py"
    assert not new_file.exists()

    hook_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(new_file),
            "content": "def new_feature():\n    pass\n",
        },
    })

    result = subprocess.run(
        [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert result.returncode == 1
    assert "STABILIZE" in result.stdout
    assert "no new Python files" in result.stdout


def test_pre_tool_use_allows_edit_in_stabilize(tmp_path):
    """Pre-tool allows Edit on existing files in STABILIZE phase (override)."""
    import subprocess
    import sys

    import yaml

    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(yaml.dump({"methodology": {"current_phase": 3}}))

    existing = tmp_path / "app.py"
    existing.write_text("x = 1\n")

    hook_input = json.dumps({
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(existing),
            "old_string": "x = 1",
            "new_string": "x = 2",
        },
    })

    result = subprocess.run(
        [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert result.returncode == 0


def test_pre_tool_use_no_block_without_override(tmp_path):
    """Auto-detected phase does NOT block (only advisory)."""
    import subprocess
    import sys

    # Empty dir = auto-detected DECIDE, but no methodology.yaml = no blocking
    hook_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(tmp_path / "app.py"),
            "content": "x = 1\n",
        },
    })

    result = subprocess.run(
        [sys.executable, "-m", "vibesrails.hooks.pre_tool_use"],
        input=hook_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=10,
    )
    assert result.returncode == 0
