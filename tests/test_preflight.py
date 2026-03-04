"""Tests for vibesrails preflight checks."""

import subprocess
from unittest import mock

from vibesrails.preflight import (
    CheckResult,
    check_ahead_behind,
    check_branch,
    check_config_valid,
    check_decisions_md,
    check_hook_installed,
    check_test_baseline,
    check_uncommitted,
    exit_code,
    format_report,
    run_preflight,
)

# ============================================
# check_branch
# ============================================


def test_check_branch_info(tmp_path):
    """Branch check returns info status with branch name."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "feature/preflight")):
        result = check_branch(tmp_path)
    assert result.status == "info"
    assert result.message == "feature/preflight"
    assert result.name == "Branch"


def test_check_branch_not_git(tmp_path):
    """Branch check warns when not in a git repo."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(False, "")):
        result = check_branch(tmp_path)
    assert result.status == "warn"
    assert "Not a git repository" in result.message


# ============================================
# check_uncommitted
# ============================================


def test_check_uncommitted_clean(tmp_path):
    """No dirty files returns ok."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "")):
        result = check_uncommitted(tmp_path)
    assert result.status == "ok"
    assert "clean" in result.message


def test_check_uncommitted_dirty(tmp_path):
    """Dirty files returns warn with count."""
    porcelain = "M  foo.py\n?? bar.py\nA  baz.py"
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, porcelain)):
        result = check_uncommitted(tmp_path)
    assert result.status == "warn"
    assert "3 uncommitted files" in result.message


def test_check_uncommitted_single_file(tmp_path):
    """Single dirty file uses singular form."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "M  foo.py")):
        result = check_uncommitted(tmp_path)
    assert result.status == "warn"
    assert "1 uncommitted file " in result.message


def test_check_uncommitted_git_fail(tmp_path):
    """Git failure returns warn."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(False, "")):
        result = check_uncommitted(tmp_path)
    assert result.status == "warn"
    assert "Could not check" in result.message


# ============================================
# check_ahead_behind
# ============================================


def test_check_ahead_behind_ok(tmp_path):
    """Few commits ahead returns ok."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "0\t2")):
        result = check_ahead_behind(tmp_path)
    assert result.status == "ok"
    assert "2 ahead" in result.message


def test_check_ahead_behind_warn(tmp_path):
    """Many commits ahead returns warn."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "0\t15")):
        result = check_ahead_behind(tmp_path)
    assert result.status == "warn"
    assert "15 commits ahead" in result.message


def test_check_ahead_behind_no_main(tmp_path):
    """No main branch returns info."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(False, "")):
        result = check_ahead_behind(tmp_path)
    assert result.status == "info"
    assert "Could not compare" in result.message


def test_check_ahead_behind_bad_output(tmp_path):
    """Unexpected output returns info."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "garbage")):
        result = check_ahead_behind(tmp_path)
    assert result.status == "info"
    assert "Could not parse" in result.message


# ============================================
# check_test_baseline
# ============================================


def test_check_test_baseline_pass(tmp_path):
    """Tests passing returns ok."""
    mock_result = mock.Mock(returncode=0)
    with mock.patch("vibesrails.preflight.subprocess.run", return_value=mock_result):
        result = check_test_baseline(tmp_path)
    assert result.status == "ok"
    assert "passing" in result.message


def test_check_test_baseline_fail(tmp_path):
    """Tests failing returns block."""
    mock_result = mock.Mock(returncode=1)
    with mock.patch("vibesrails.preflight.subprocess.run", return_value=mock_result):
        result = check_test_baseline(tmp_path)
    assert result.status == "block"
    assert "failing" in result.message


def test_check_test_baseline_timeout(tmp_path):
    """Tests timing out returns block."""
    with mock.patch(
        "vibesrails.preflight.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=300),
    ):
        result = check_test_baseline(tmp_path)
    assert result.status == "block"
    assert "timed out" in result.message


def test_check_test_baseline_no_pytest(tmp_path):
    """Missing pytest returns warn."""
    with mock.patch(
        "vibesrails.preflight.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        result = check_test_baseline(tmp_path)
    assert result.status == "warn"
    assert "not found" in result.message


# ============================================
# check_config_valid
# ============================================


def test_check_config_valid_ok(tmp_path):
    """Valid config returns ok."""
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text("version: '1.0'\nblocking: []\n")
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", return_value={"version": "1.0", "blocking": []}):
            with mock.patch("vibesrails.preflight.validate_config", return_value=True):
                result = check_config_valid()
    assert result.status == "ok"
    assert "valid" in result.message


def test_check_config_missing():
    """No config returns warn."""
    with mock.patch("vibesrails.preflight.find_config", return_value=None):
        result = check_config_valid()
    assert result.status == "warn"
    assert "No vibesrails.yaml" in result.message


def test_check_config_invalid_load():
    """Config that fails to load returns block."""
    config_file = mock.Mock()
    config_file.exists.return_value = True
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", side_effect=ValueError("bad yaml")):
            result = check_config_valid()
    assert result.status == "block"
    assert "Invalid config" in result.message


def test_check_config_validation_fails():
    """Config that fails validation returns block."""
    config_file = mock.Mock()
    config_file.exists.return_value = True
    config_file.name = "vibesrails.yaml"
    with mock.patch("vibesrails.preflight.find_config", return_value=config_file):
        with mock.patch("vibesrails.preflight.load_config", return_value={}):
            with mock.patch("vibesrails.preflight.validate_config", return_value=False):
                result = check_config_valid()
    assert result.status == "block"
    assert "validation failed" in result.message


# ============================================
# check_hook_installed
# ============================================


def test_check_hook_installed_ok(tmp_path):
    """Hook with vibesrails returns ok."""
    hook_dir = tmp_path / ".git" / "hooks"
    hook_dir.mkdir(parents=True)
    hook = hook_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nvibesrails --all\n")
    result = check_hook_installed(tmp_path)
    assert result.status == "ok"
    assert "installed" in result.message


def test_check_hook_missing(tmp_path):
    """No hook file returns warn."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    result = check_hook_installed(tmp_path)
    assert result.status == "warn"
    assert "No pre-commit hook" in result.message


def test_check_hook_without_vibesrails(tmp_path):
    """Hook without vibesrails mention returns warn."""
    hook_dir = tmp_path / ".git" / "hooks"
    hook_dir.mkdir(parents=True)
    hook = hook_dir / "pre-commit"
    hook.write_text("#!/bin/sh\necho hello\n")
    result = check_hook_installed(tmp_path)
    assert result.status == "warn"
    assert "missing vibesrails" in result.message


# ============================================
# check_decisions_md
# ============================================


def test_check_decisions_exists_docs(tmp_path):
    """decisions.md in docs/ returns ok."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "decisions.md").write_text("# Decisions\n")
    result = check_decisions_md(tmp_path)
    assert result.status == "ok"
    assert "docs/decisions.md" in result.message


def test_check_decisions_exists_root(tmp_path):
    """decisions.md at root returns ok."""
    (tmp_path / "decisions.md").write_text("# Decisions\n")
    result = check_decisions_md(tmp_path)
    assert result.status == "ok"


def test_check_decisions_missing(tmp_path):
    """No decisions.md returns warn."""
    result = check_decisions_md(tmp_path)
    assert result.status == "warn"
    assert "No decisions.md" in result.message


# ============================================
# run_preflight
# ============================================


def test_run_preflight_returns_eight_results(tmp_path):
    """Orchestrator returns exactly 8 results (including assertions)."""
    with mock.patch("vibesrails.preflight.run_git", return_value=(True, "main")):
        with mock.patch("vibesrails.preflight.subprocess.run", return_value=mock.Mock(returncode=0)):
            with mock.patch("vibesrails.preflight.find_config", return_value=None):
                results = run_preflight(tmp_path)
    assert len(results) == 8
    assert all(isinstance(r, CheckResult) for r in results)


# ============================================
# exit_code
# ============================================


def test_exit_code_all_clear():
    """No blockers or warnings returns 0."""
    results = [
        CheckResult("A", "ok", "fine"),
        CheckResult("B", "info", "note"),
    ]
    assert exit_code(results) == 0


def test_exit_code_warnings_only():
    """Warnings without blockers returns 1."""
    results = [
        CheckResult("A", "ok", "fine"),
        CheckResult("B", "warn", "heads up"),
    ]
    assert exit_code(results) == 1


def test_exit_code_blockers():
    """Blockers returns 2."""
    results = [
        CheckResult("A", "block", "stop"),
        CheckResult("B", "warn", "also this"),
    ]
    assert exit_code(results) == 2


# ============================================
# format_report
# ============================================


def test_format_report_contains_header():
    """Report includes the preflight header."""
    results = [CheckResult("Branch", "info", "main")]
    report = format_report(results)
    assert "PREFLIGHT CHECK" in report


def test_format_report_shows_all_results():
    """Report includes every check result."""
    results = [
        CheckResult("Branch", "info", "main"),
        CheckResult("Tests", "ok", "passing"),
        CheckResult("Config", "warn", "missing"),
    ]
    report = format_report(results)
    assert "Branch" in report
    assert "Tests" in report
    assert "Config" in report


def test_format_report_blocker_summary():
    """Report shows blocker count."""
    results = [
        CheckResult("Tests", "block", "failing"),
        CheckResult("Config", "warn", "missing"),
    ]
    report = format_report(results)
    assert "1 blocker" in report
    assert "1 warning" in report


def test_format_report_all_clear():
    """Report shows all clear when no issues."""
    results = [CheckResult("Tests", "ok", "passing")]
    report = format_report(results)
    assert "All clear" in report
