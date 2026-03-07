"""Tests for gate checking and phase promotion."""

from unittest import mock

import yaml

from vibesrails.context.phase import ProjectPhase
from vibesrails.gates import (
    GateReport,
    check_gates,
    format_gate_report,
    promote_phase,
    set_phase,
)

# ============================================
# check_gates
# ============================================


def test_check_gates_phase0_empty(tmp_path):
    """Empty project: DECIDE phase, gates incomplete."""
    report = check_gates(tmp_path)
    assert report.current_phase == ProjectPhase.DECIDE
    assert report.target_phase == ProjectPhase.SKELETON
    assert not report.all_met
    assert report.total_count == 3  # readme, decisions, contracts


def test_check_gates_phase0_complete(tmp_path):
    """DECIDE phase (forced) with all gates met."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 0}})
    )
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Dec")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(3):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )
    report = check_gates(tmp_path)
    assert report.current_phase == ProjectPhase.DECIDE
    assert report.all_met
    assert report.met_count == 3


def test_check_gates_at_deploy(tmp_path):
    """DEPLOY phase: no further gates."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 4}})
    )
    report = check_gates(tmp_path)
    assert report.current_phase == ProjectPhase.DEPLOY
    assert report.target_phase is None
    assert report.all_met  # no conditions = all met


def test_check_gates_phase1_partial(tmp_path):
    """SKELETON phase with partial gates."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 1}})
    )
    # 2 modules but no tests
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "b.py").write_text("y = 2\n")

    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("no pytest")
        report = check_gates(tmp_path)

    assert report.current_phase == ProjectPhase.SKELETON
    assert report.target_phase == ProjectPhase.FLESH_OUT
    assert not report.all_met


# ============================================
# format_gate_report
# ============================================


def test_format_gate_report_incomplete():
    """Format shows unmet gates."""
    from vibesrails.gates import GateCondition

    report = GateReport(
        current_phase=ProjectPhase.DECIDE,
        is_override=False,
        target_phase=ProjectPhase.SKELETON,
        gate_name="decide_to_skeleton",
        conditions=[
            GateCondition("has_readme", True),
            GateCondition("has_decisions", False),
            GateCondition("has_contracts", False),
        ],
    )
    output = format_gate_report(report)
    assert "DECIDE" in output
    assert "SKELETON" in output
    assert "CANNOT PROMOTE" in output
    assert "1/3" in output


def test_format_gate_report_complete():
    """Format shows ready to promote."""
    from vibesrails.gates import GateCondition

    report = GateReport(
        current_phase=ProjectPhase.DECIDE,
        is_override=False,
        target_phase=ProjectPhase.SKELETON,
        gate_name="decide_to_skeleton",
        conditions=[
            GateCondition("has_readme", True),
            GateCondition("has_decisions", True),
            GateCondition("has_contracts", True),
        ],
    )
    output = format_gate_report(report)
    assert "READY TO PROMOTE" in output
    assert "3/3" in output


def test_format_gate_report_deploy():
    """Format at DEPLOY shows no further gates."""
    report = GateReport(
        current_phase=ProjectPhase.DEPLOY,
        is_override=False,
        target_phase=None,
        gate_name=None,
        conditions=[],
    )
    output = format_gate_report(report)
    assert "DEPLOY" in output
    assert "no further gates" in output


# ============================================
# promote_phase
# ============================================


def test_promote_success(tmp_path):
    """Promote succeeds when all gates are met (forced DECIDE)."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 0}})
    )
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Dec")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(3):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    result = promote_phase(tmp_path)
    assert result is True

    # Verify methodology.yaml was updated
    meth = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    assert meth["methodology"]["current_phase"] == ProjectPhase.SKELETON.value


def test_promote_blocked(tmp_path):
    """Promote fails when gates are not met."""
    # Empty project — no gates met
    result = promote_phase(tmp_path)
    assert result is False
    # No methodology.yaml should have been created
    assert not (tmp_path / ".vibesrails" / "methodology.yaml").exists()


def test_promote_force(tmp_path):
    """Force promote bypasses gate check."""
    result = promote_phase(tmp_path, force=True)
    assert result is True

    meth = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    assert meth["methodology"]["current_phase"] == ProjectPhase.SKELETON.value


def test_promote_at_deploy(tmp_path):
    """Promote at DEPLOY returns False."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 4}})
    )
    result = promote_phase(tmp_path)
    assert result is False


def test_promote_no_skip(tmp_path):
    """Promote only advances by one phase (0→1, not 0→2)."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 0}})
    )
    (tmp_path / "README.md").write_text("# Project")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decisions.md").write_text("# Dec")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(3):
        (pkg / f"mod{i}.py").write_text(
            f"def func{i}(x: int) -> str:\n    return str(x)\n"
        )

    promote_phase(tmp_path)
    meth = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    # Must be 1 (SKELETON), not 2
    assert meth["methodology"]["current_phase"] == 1


# ============================================
# set_phase
# ============================================


def test_set_phase_override(tmp_path):
    """set_phase creates/updates methodology.yaml."""
    result = set_phase(tmp_path, 2)
    assert result is True

    meth = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    assert meth["methodology"]["current_phase"] == 2


def test_set_phase_auto(tmp_path):
    """set_phase -1 sets 'auto'."""
    result = set_phase(tmp_path, -1)
    assert result is True

    meth = yaml.safe_load(
        (tmp_path / ".vibesrails" / "methodology.yaml").read_text()
    )
    assert meth["methodology"]["current_phase"] == "auto"


def test_set_phase_preserves_existing(tmp_path):
    """set_phase preserves other keys in methodology.yaml."""
    vr = tmp_path / ".vibesrails"
    vr.mkdir()
    (vr / "methodology.yaml").write_text(
        yaml.dump({"methodology": {"current_phase": 0, "rules": {"tdd": True}}})
    )

    set_phase(tmp_path, 3)
    meth = yaml.safe_load((vr / "methodology.yaml").read_text())
    assert meth["methodology"]["current_phase"] == 3
    assert meth["methodology"]["rules"]["tdd"] is True
