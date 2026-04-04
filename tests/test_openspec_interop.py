"""Tests for OpenSpec interop — detection, phase signals, gates, preflight, status."""


import pytest

from vibesrails.openspec_interop import detect

# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture()
def openspec_project(tmp_path):
    """Create a mock OpenSpec project structure."""
    os_dir = tmp_path / "openspec"
    os_dir.mkdir()
    (os_dir / "project.md").write_text("# My Project\n")

    # 2 specs
    for name in ["auth-login", "checkout-cart"]:
        spec_dir = os_dir / "specs" / name
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text(f"# {name}\n")

    # 1 pending change
    change_dir = os_dir / "changes" / "add-dark-mode"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("# Dark Mode\n")
    (change_dir / "tasks.md").write_text("- [ ] Task 1\n")

    # 1 archived change
    archive_dir = os_dir / "changes" / "archive" / "old-refactor"
    archive_dir.mkdir(parents=True)
    (archive_dir / "proposal.md").write_text("# Old\n")

    return tmp_path


@pytest.fixture()
def empty_project(tmp_path):
    """Project with no OpenSpec."""
    (tmp_path / "README.md").write_text("# Hello\n")
    return tmp_path


# ── Detection tests ───────────────────────────────────────────


def test_detect_openspec_present(openspec_project):
    info = detect(openspec_project)
    assert info.detected is True


def test_detect_openspec_absent(empty_project):
    info = detect(empty_project)
    assert info.detected is False


def test_detect_has_project_md(openspec_project):
    info = detect(openspec_project)
    assert info.has_project_md is True


def test_detect_no_project_md(tmp_path):
    (tmp_path / "openspec").mkdir()
    info = detect(tmp_path)
    assert info.detected is True
    assert info.has_project_md is False


def test_count_specs(openspec_project):
    info = detect(openspec_project)
    assert info.spec_count == 2
    assert set(info.spec_names) == {"auth-login", "checkout-cart"}


def test_count_pending_changes(openspec_project):
    info = detect(openspec_project)
    assert info.pending_count == 1
    assert info.pending_names == ["add-dark-mode"]


def test_count_archived(openspec_project):
    info = detect(openspec_project)
    assert info.archived_count == 1


def test_empty_openspec_dir(tmp_path):
    (tmp_path / "openspec").mkdir()
    info = detect(tmp_path)
    assert info.detected is True
    assert info.spec_count == 0
    assert info.pending_count == 0
    assert info.archived_count == 0


def test_hidden_dirs_ignored(tmp_path):
    os_dir = tmp_path / "openspec"
    os_dir.mkdir()
    (os_dir / "specs").mkdir()
    (os_dir / "specs" / ".hidden").mkdir()
    (os_dir / "specs" / "real-spec").mkdir()
    info = detect(tmp_path)
    assert info.spec_count == 1


# ── Phase signal tests ────────────────────────────────────────


def test_phase_signals_with_openspec(openspec_project):
    from vibesrails.context.phase import PhaseDetector

    detector = PhaseDetector(openspec_project)
    signals = detector.collect_signals()
    assert signals.has_openspec is True
    assert signals.openspec_has_project is True
    assert signals.openspec_spec_count == 2
    assert signals.openspec_pending_count == 1


def test_phase_signals_without_openspec(empty_project):
    from vibesrails.context.phase import PhaseDetector

    detector = PhaseDetector(empty_project)
    signals = detector.collect_signals()
    assert signals.has_openspec is False
    assert signals.openspec_spec_count == 0


# ── Effective gates tests ─────────────────────────────────────


def test_effective_gates_without_openspec():
    from vibesrails.context.phase import _GATES, PhaseSignals, get_effective_gates

    signals = PhaseSignals()  # has_openspec=False
    effective = get_effective_gates(signals)
    # Should be identical to _GATES
    for gate_name in _GATES:
        assert len(effective[gate_name]) == len(_GATES[gate_name])


def test_effective_gates_with_openspec():
    from vibesrails.context.phase import _GATES, PhaseSignals, get_effective_gates

    signals = PhaseSignals(has_openspec=True)
    effective = get_effective_gates(signals)
    # decide_to_skeleton should have 1 extra condition
    assert len(effective["decide_to_skeleton"]) == len(_GATES["decide_to_skeleton"]) + 1
    # skeleton_to_flesh should have 1 extra
    assert len(effective["skeleton_to_flesh"]) == len(_GATES["skeleton_to_flesh"]) + 1
    # flesh_to_stabilize should have 1 extra
    assert len(effective["flesh_to_stabilize"]) == len(_GATES["flesh_to_stabilize"]) + 1
    # stabilize_to_deploy unchanged (no OpenSpec gate)
    assert len(effective["stabilize_to_deploy"]) == len(_GATES["stabilize_to_deploy"])


def test_openspec_gate_blocks_without_project_md():
    from vibesrails.context.phase import PhaseSignals, get_effective_gates

    signals = PhaseSignals(
        has_openspec=True, openspec_has_project=False,
        has_readme=True, has_adr=True, has_contracts=True,
    )
    effective = get_effective_gates(signals)
    # All base conditions met, but openspec: project.md is not
    conditions = effective["decide_to_skeleton"]
    results = [(label, bool(check(signals))) for label, check in conditions]
    failed = [label for label, met in results if not met]
    assert "openspec: project.md" in failed


def test_openspec_gate_passes_with_project_md():
    from vibesrails.context.phase import PhaseSignals, get_effective_gates

    signals = PhaseSignals(
        has_openspec=True, openspec_has_project=True,
        has_readme=True, has_adr=True, has_contracts=True,
    )
    effective = get_effective_gates(signals)
    conditions = effective["decide_to_skeleton"]
    assert all(bool(check(signals)) for _, check in conditions)


def test_pending_changes_block_stabilize_gate():
    from vibesrails.context.phase import PhaseSignals, get_effective_gates

    signals = PhaseSignals(
        has_openspec=True, openspec_pending_count=2,
        test_count=100, has_ci=True, has_changelog=True,
    )
    effective = get_effective_gates(signals)
    conditions = effective["flesh_to_stabilize"]
    failed = [label for label, check in conditions if not bool(check(signals))]
    assert "openspec: no pending changes" in failed


# ── Preflight test ────────────────────────────────────────────


def test_preflight_openspec_detected(openspec_project):
    from vibesrails.preflight import check_openspec

    result = check_openspec(openspec_project)
    assert result is not None
    assert "OpenSpec" in result.name
    assert "2 specs" in result.message
    assert "1 pending" in result.message


def test_preflight_openspec_not_detected(empty_project):
    from vibesrails.preflight import check_openspec

    result = check_openspec(empty_project)
    assert result is None


def test_preflight_openspec_pending_is_warning(openspec_project):
    from vibesrails.preflight import check_openspec

    result = check_openspec(openspec_project)
    assert result.status == "warn"


def test_preflight_openspec_clean_is_ok(tmp_path):
    """OpenSpec with no pending changes → ok status."""
    os_dir = tmp_path / "openspec"
    os_dir.mkdir()
    (os_dir / "project.md").write_text("# P\n")
    (os_dir / "specs" / "auth").mkdir(parents=True)
    from vibesrails.preflight import check_openspec

    result = check_openspec(tmp_path)
    assert result.status == "ok"


# ── Status report tests ───────────────────────────────────────


def test_status_openspec_section_present():
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
        "openspec": {
            "detected": True, "spec_count": 5,
            "pending_count": 1, "pending_names": ["add-dark-mode"],
            "archived_count": 3,
        },
    }
    output = format_full(data)
    assert "SPECS" in output
    assert "OpenSpec" in output
    assert "5 specs" in output
    assert "add-dark-mode" in output


def test_status_openspec_section_absent_when_not_detected():
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
    }
    output = format_full(data)
    assert "SPECS" not in output
    assert "OpenSpec" not in output


def test_quiet_includes_openspec():
    from vibesrails.status import format_quiet

    data = {
        "version": "2.3.0",
        "git": {"branch": "main", "dirty_count": 0, "unpushed": 0},
        "context": {
            "mode": "R&D", "mode_score": 0.8, "mode_confidence": "high",
            "phase": "FLESH OUT", "phase_num": 2, "phase_total": 4,
            "phase_missing": [], "phase_is_override": False,
        },
        "gates": {"met": 2, "total": 2, "all_met": True, "target": None},
        "assertions": {"passed": 4, "total": 4},
        "docs": {"claude_md": "synced", "decisions": True},
        "tests": {"declared": 100},
        "openspec": {
            "detected": True, "spec_count": 3,
            "pending_count": 0, "pending_names": [],
            "archived_count": 1,
        },
    }
    output = format_quiet(data)
    assert "OpenSpec" in output
    assert "3 specs" in output
