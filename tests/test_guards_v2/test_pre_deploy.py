"""Tests for PreDeployGuard — real filesystem, mock only pytest subprocess."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibesrails.guards_v2.pre_deploy import (
    PreDeployGuard,
    _read_init_version,
    _read_pyproject_version,
)


@pytest.fixture()
def guard():
    return PreDeployGuard(coverage_threshold=80)


@pytest.fixture()
def project(tmp_path):
    """Minimal real project skeleton."""
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "1.0.0"\n'
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 1.0.0\n- Initial release\n"
    )
    (tmp_path / "tests").mkdir()
    return tmp_path


# ── pytest checks (mock subprocess only) ─────────────────


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_passes(mock_run, guard, project):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="TOTAL   100    10    90%\n", stderr=""
    )
    issues = guard._check_pytest(project)
    assert len(issues) == 0


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_fails(mock_run, guard, project):
    mock_run.return_value = MagicMock(
        returncode=1, stdout="TOTAL   100    50    50%\n", stderr=""
    )
    issues = guard._check_pytest(project)
    assert any("failed" in i.message for i in issues)
    assert any(i.severity == "block" for i in issues)


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_low_coverage(mock_run, guard, project):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="TOTAL   100    50    50%\n", stderr=""
    )
    issues = guard._check_pytest(project)
    assert any("Coverage 50%" in i.message for i in issues)


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_not_found(mock_run, guard, project):
    mock_run.side_effect = FileNotFoundError()
    issues = guard._check_pytest(project)
    assert len(issues) == 1
    assert "not found" in issues[0].message


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_timeout(mock_run, guard, project):
    from subprocess import TimeoutExpired
    mock_run.side_effect = TimeoutExpired("pytest", 120)
    issues = guard._check_pytest(project)
    assert len(issues) == 1
    assert "timed out" in issues[0].message


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_pytest_high_coverage_passes(mock_run, guard, project):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="TOTAL   500   10    98%\n", stderr=""
    )
    issues = guard._check_pytest(project)
    assert len(issues) == 0


# ── blocking TODOs (real files) ──────────────────────────


def test_blocking_todo_critical(guard, project):
    src = project / "mypkg" / "foo.py"
    src.write_text("# TODO CRITICAL: fix before release\n")
    issues = guard._check_blocking_todos(project)
    assert len(issues) >= 1
    assert issues[0].severity == "block"


def test_blocking_todo_block_keyword(guard, project):
    src = project / "mypkg" / "bar.py"
    src.write_text("# FIXME BLOCK: must handle edge case\n")
    issues = guard._check_blocking_todos(project)
    assert len(issues) >= 1


def test_normal_todo_ignored(guard, project):
    src = project / "mypkg" / "foo.py"
    src.write_text("# TODO: refactor later\n")
    issues = guard._check_blocking_todos(project)
    assert len(issues) == 0


def test_fixme_without_block_ignored(guard, project):
    src = project / "mypkg" / "foo.py"
    src.write_text("# FIXME: minor cleanup\n")
    issues = guard._check_blocking_todos(project)
    assert len(issues) == 0


# ── version consistency (real files) ─────────────────────


def test_version_match(guard, project):
    issues = guard._check_version_consistency(project)
    assert len(issues) == 0


def test_version_mismatch(guard, project):
    (project / "mypkg" / "__init__.py").write_text('__version__ = "2.0.0"\n')
    issues = guard._check_version_consistency(project)
    assert any("mismatch" in i.message for i in issues)


def test_no_init_version(guard, project):
    (project / "mypkg" / "__init__.py").write_text("# no version\n")
    issues = guard._check_version_consistency(project)
    assert any("No __version__" in i.message for i in issues)


def test_no_pyproject_version(guard, project):
    (project / "pyproject.toml").write_text('[project]\nname = "mypkg"\n')
    issues = guard._check_version_consistency(project)
    assert any("No version" in i.message for i in issues)


# ── changelog (real files) ───────────────────────────────


def test_changelog_present_with_version(guard, project):
    issues = guard._check_changelog(project)
    assert len(issues) == 0


def test_changelog_missing(guard, project):
    (project / "CHANGELOG.md").unlink()
    issues = guard._check_changelog(project)
    assert any("missing" in i.message for i in issues)


def test_changelog_missing_version_entry(guard, project):
    (project / "CHANGELOG.md").write_text("# Changelog\n\n## 0.9.0\n- Old\n")
    issues = guard._check_changelog(project)
    assert any("no entry" in i.message for i in issues)


def test_changelog_with_current_version(guard, project):
    (project / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n- Done\n")
    issues = guard._check_changelog(project)
    assert len(issues) == 0


# ── report generation ────────────────────────────────────


def test_report_all_pass(guard):
    report = guard.generate_report([])
    assert "All checks passed" in report


def test_report_with_blocking_and_warns(guard):
    from vibesrails.guards_v2.dependency_audit import V2GuardIssue
    issues = [
        V2GuardIssue(guard="pre-deploy", severity="block", message="pytest failed"),
        V2GuardIssue(guard="pre-deploy", severity="warn", message="CHANGELOG missing"),
        V2GuardIssue(guard="pre-deploy", severity="info", message="Consider upgrading"),
    ]
    report = guard.generate_report(issues)
    assert "Blocking Issues" in report
    assert "Warnings" in report
    assert "Info" in report
    assert "3 issue(s) found" in report


def test_report_file_location_in_report(guard):
    from vibesrails.guards_v2.dependency_audit import V2GuardIssue
    issues = [
        V2GuardIssue(
            guard="pre-deploy", severity="block", message="Bad TODO",
            file="app.py", line=10,
        ),
    ]
    report = guard.generate_report(issues)
    assert "app.py:10" in report


# ── run_all integration ──────────────────────────────────


@patch("vibesrails.guards_v2.pre_deploy_checks.subprocess.run")
def test_run_all_integrates(mock_run, guard, project):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="TOTAL   100    10    90%\n", stderr=""
    )
    issues = guard.run_all(project)
    assert isinstance(issues, list)


# ── helper functions ─────────────────────────────────────


def test_read_init_version(project):
    assert _read_init_version(project) == "1.0.0"


def test_read_pyproject_version(project):
    assert _read_pyproject_version(project) == "1.0.0"


def test_read_init_version_missing(tmp_path):
    assert _read_init_version(tmp_path) is None


def test_read_pyproject_version_missing(tmp_path):
    assert _read_pyproject_version(tmp_path) is None


def test_parse_coverage(guard):
    assert guard._parse_coverage("TOTAL   500    50    90%\n") == 90


def test_parse_coverage_none(guard):
    assert guard._parse_coverage("no coverage data") is None


def test_parse_coverage_edge_100(guard):
    assert guard._parse_coverage("TOTAL   500    0    100%\n") == 100
