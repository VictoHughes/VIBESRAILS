"""Tests for DependencyAuditGuard — real files, real parsing, only mock network."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from vibesrails.guards_v2.dependency_audit import (
    DependencyAuditGuard,
    V2GuardIssue,
    _levenshtein,
    _normalize_pkg_name,
)


@pytest.fixture
def guard():
    return DependencyAuditGuard()


# ── Levenshtein (real computation) ────────────────────────────────


def test_levenshtein_identical():
    assert _levenshtein("requests", "requests") == 0


def test_levenshtein_one_swap():
    assert _levenshtein("reqeusts", "requests") <= 2


def test_levenshtein_completely_different():
    assert _levenshtein("abcdef", "xyz") > 2


def test_levenshtein_empty_string():
    assert _levenshtein("", "hello") == 5
    assert _levenshtein("hello", "") == 5


def test_levenshtein_single_char_diff():
    assert _levenshtein("flask", "flasks") == 1


# ── Normalize (real computation) ─────────────────────────────────


def test_normalize_underscores():
    assert _normalize_pkg_name("my_package") == "my-package"


def test_normalize_dots():
    assert _normalize_pkg_name("my.package") == "my-package"


def test_normalize_mixed():
    assert _normalize_pkg_name("My_Cool.Package") == "my-cool-package"


# ── Real requirements.txt parsing ────────────────────────────────


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_pinned_deps_no_unpinned_warning(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("flask==2.3.0\nrequests==2.31.0\n")
    issues = guard.scan_requirements_file(req)
    unpinned = [i for i in issues if "Unpinned" in i.message]
    assert len(unpinned) == 0


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_unpinned_deps_detected(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("flask\nrequests>=2.0\n")
    issues = guard.scan_requirements_file(req)
    unpinned = [i for i in issues if "Unpinned" in i.message]
    assert len(unpinned) == 2


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_comments_and_blanks_skipped(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("# comment\n\nflask==2.3.0\n-r other.txt\n")
    issues = guard.scan_requirements_file(req)
    unpinned = [i for i in issues if "Unpinned" in i.message]
    assert len(unpinned) == 0


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_extras_brackets_stripped(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests[security]==2.31.0\n")
    issues = guard.scan_requirements_file(req)
    unpinned = [i for i in issues if "Unpinned" in i.message]
    assert len(unpinned) == 0


# ── Real pyproject.toml parsing ──────────────────────────────────


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_pyproject_deps_parsed(mock_pypi, guard, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "myapp"\ndependencies = [\n'
        '  "flask>=2.0",\n  "requests==2.31.0",\n]\n'
    )
    issues = guard.scan(tmp_path)
    unpinned = [i for i in issues if "Unpinned" in i.message]
    assert len(unpinned) == 1
    assert "flask" in unpinned[0].message


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_pyproject_no_deps_section(mock_pypi, guard, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[build-system]\nrequires = ["setuptools"]\n')
    issues = guard.scan(tmp_path)
    assert len(issues) == 0


# ── Typosquatting detection (real Levenshtein) ───────────────────


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_typosquatting_reqeusts(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("reqeusts==1.0.0\n")
    issues = guard.scan_requirements_file(req)
    typo = [i for i in issues if "typosquatting" in i.message.lower()]
    assert len(typo) == 1
    assert "requests" in typo[0].message


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_no_typosquatting_exact_match(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\n")
    issues = guard.scan_requirements_file(req)
    typo = [i for i in issues if "typosquatting" in i.message.lower()]
    assert len(typo) == 0


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_typosquatting_flaask(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("flaask==1.0.0\n")
    issues = guard.scan_requirements_file(req)
    typo = [i for i in issues if "typosquatting" in i.message.lower()]
    assert len(typo) == 1
    assert "flask" in typo[0].message


# ── Known bad versions (real lookup) ─────────────────────────────


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_known_bad_version_urllib3(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("urllib3==1.24.1\n")
    issues = guard.scan_requirements_file(req)
    cve = [i for i in issues if "vulnerable" in i.message.lower()]
    assert len(cve) == 1


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_safe_version_no_issue(mock_pypi, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("urllib3==2.0.0\n")
    issues = guard.scan_requirements_file(req)
    cve = [i for i in issues if "vulnerable" in i.message.lower()]
    assert len(cve) == 0


# ── Abandoned package (mock PyPI response, real parsing) ─────────


def _make_pypi_response(upload_time: str) -> dict:
    return {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [{"upload_time_iso_8601": upload_time}]
        },
    }


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi")
def test_abandoned_package_detected(mock_pypi, guard, tmp_path):
    mock_pypi.return_value = _make_pypi_response("2020-01-01T00:00:00+00:00")
    req = tmp_path / "requirements.txt"
    req.write_text("oldpackage==1.0.0\n")
    issues = guard.scan_requirements_file(req)
    abandoned = [i for i in issues if "abandoned" in i.message.lower()]
    assert len(abandoned) == 1


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi")
def test_recent_package_not_abandoned(mock_pypi, guard, tmp_path):
    mock_pypi.return_value = _make_pypi_response("2025-12-01T00:00:00+00:00")
    req = tmp_path / "requirements.txt"
    req.write_text("freshpackage==1.0.0\n")
    issues = guard.scan_requirements_file(req)
    abandoned = [i for i in issues if "abandoned" in i.message.lower()]
    assert len(abandoned) == 0


# ── PyPI unreachable (mock network failure) ──────────────────────


@patch("urllib.request.urlopen", side_effect=Exception("network error"))
def test_pypi_unreachable_no_crash(mock_urlopen, tmp_path):
    guard = DependencyAuditGuard()
    req = tmp_path / "requirements.txt"
    req.write_text("somepackage==1.0.0\n")
    issues = guard.scan_requirements_file(req)
    abandoned = [i for i in issues if "abandoned" in i.message.lower()]
    assert len(abandoned) == 0


# ── Full scan finds all dep files ────────────────────────────────


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_scan_finds_requirements_and_pyproject(mock_pypi, guard, tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="x"\ndependencies=["requests>=1.0"]\n'
    )
    issues = guard.scan(tmp_path)
    files = {i.file for i in issues if i.file}
    assert any("requirements.txt" in f for f in files)
    assert any("pyproject.toml" in f for f in files)


@patch("vibesrails.guards_v2.dependency_audit_checks.fetch_pypi", return_value=None)
def test_scan_finds_setup_py(mock_pypi, guard, tmp_path):
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\nsetup(install_requires=['boto3'])\n"
    )
    issues = guard.scan(tmp_path)
    files = {i.file for i in issues if i.file}
    assert any("setup.py" in f for f in files)


# ── pip-audit (mock subprocess only) ─────────────────────────────


@patch("subprocess.run")
def test_pip_audit_reports_cve(mock_run, guard, tmp_path):
    from unittest.mock import MagicMock

    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.19.0\n")
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout=json.dumps({
            "dependencies": [{
                "name": "requests",
                "version": "2.19.0",
                "vulns": [{"id": "CVE-2023-0001", "description": "Test vuln"}],
            }],
        }),
    )
    issues = guard.run_pip_audit(tmp_path)
    assert len(issues) == 1
    assert "CVE-2023-0001" in issues[0].message


@patch("subprocess.run", side_effect=FileNotFoundError)
def test_pip_audit_not_installed_no_crash(mock_run, guard, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.19.0\n")
    issues = guard.run_pip_audit(tmp_path)
    assert len(issues) == 0
