"""Tests for pre_deploy_checks.py — pure helper functions."""

from pathlib import Path

from vibesrails.guards_v2.dependency_audit import V2GuardIssue
from vibesrails.guards_v2.pre_deploy_checks import (
    format_location,
    guess_package,
    is_excluded,
    parse_coverage,
)

# ── format_location ────────────────────────────────────


def test_format_location_file_and_line():
    issue = V2GuardIssue(guard="g", severity="warn", message="m", file="app.py", line=10)
    assert format_location(issue) == " (`app.py:10`)"


def test_format_location_file_only():
    issue = V2GuardIssue(guard="g", severity="warn", message="m", file="app.py")
    assert format_location(issue) == " (`app.py`)"


def test_format_location_no_file():
    issue = V2GuardIssue(guard="g", severity="warn", message="m")
    assert format_location(issue) == ""


def test_format_location_line_but_no_file():
    issue = V2GuardIssue(guard="g", severity="warn", message="m", line=5)
    assert format_location(issue) == ""


# ── is_excluded ─────────────────────────────────────────


def test_is_excluded_venv():
    assert is_excluded(Path("venv/lib/python3.12/site.py")) is True


def test_is_excluded_dot_venv():
    assert is_excluded(Path(".venv/lib/python3.12/site.py")) is True


def test_is_excluded_node_modules():
    assert is_excluded(Path("node_modules/something.py")) is True


def test_is_excluded_pycache():
    assert is_excluded(Path("mypkg/__pycache__/module.cpython-312.pyc")) is True


def test_is_excluded_hidden_dir():
    assert is_excluded(Path(".git/hooks/pre-commit")) is True


def test_is_excluded_normal_file():
    assert is_excluded(Path("mypkg/utils.py")) is False


def test_is_excluded_site_packages():
    assert is_excluded(Path("lib/site-packages/pkg/mod.py")) is True


# ── guess_package ───────────────────────────────────────


def test_guess_package_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "my-pkg"\n')
    assert guess_package(tmp_path) == "my_pkg"


def test_guess_package_from_directory(tmp_path):
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    assert guess_package(tmp_path) == "myapp"


def test_guess_package_fallback_src(tmp_path):
    # No pyproject, no package dir
    assert guess_package(tmp_path) == "src"


def test_guess_package_prefers_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "from-toml"\n')
    pkg = tmp_path / "different_name"
    pkg.mkdir()
    (pkg / "__init__.py").touch()
    assert guess_package(tmp_path) == "from_toml"


# ── parse_coverage ──────────────────────────────────────


def test_parse_coverage_standard():
    assert parse_coverage("TOTAL   500    50    90%\n") == 90


def test_parse_coverage_100():
    assert parse_coverage("TOTAL   500    0    100%\n") == 100


def test_parse_coverage_0():
    assert parse_coverage("TOTAL   500    500    0%\n") == 0


def test_parse_coverage_no_match():
    assert parse_coverage("no coverage data here") is None


def test_parse_coverage_embedded():
    output = "collected 50 items\n...\nTOTAL   200    20    90%\n2 passed"
    assert parse_coverage(output) == 90
