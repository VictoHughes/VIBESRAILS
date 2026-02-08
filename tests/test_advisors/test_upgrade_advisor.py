"""Tests for UpgradeAdvisor — real file parsing, mock only PyPI network."""

from unittest.mock import patch

import pytest

from vibesrails.advisors.upgrade_advisor import (
    UpgradeAdvisor,
    _classify_update,
    _parse_version,
)


def _pypi(name, version, summary="", classifiers=None):
    """Build a fake PyPI JSON response."""
    return {
        "info": {
            "name": name,
            "version": version,
            "summary": summary,
            "classifiers": classifiers or [],
        },
        "releases": {},
    }


@pytest.fixture()
def advisor():
    return UpgradeAdvisor()


# ── _parse_version (no mock) ────────────────────────────


def test_parse_version_simple():
    assert _parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_prerelease():
    assert _parse_version("2.0.0rc1") == (2, 0, 0)


def test_parse_version_single():
    assert _parse_version("5") == (5,)


def test_parse_version_with_dash():
    assert _parse_version("1.0.0-beta") == (1, 0, 0)


def test_parse_version_garbage():
    assert _parse_version("abc") == (0,)


# ── _classify_update (no mock) ──────────────────────────


def test_classify_up_to_date():
    assert _classify_update("1.0.0", "1.0.0", "foo") == "up-to-date"


def test_classify_major():
    assert _classify_update("1.0.0", "2.0.0", "foo") == "major"


def test_classify_minor():
    assert _classify_update("1.0.0", "1.1.0", "foo") == "minor"


def test_classify_patch():
    assert _classify_update("1.0.0", "1.0.1", "foo") == "patch"


def test_classify_security_package():
    assert _classify_update("1.0.0", "1.0.1", "cryptography") == "security"


def test_classify_security_up_to_date():
    assert _classify_update("1.0.0", "1.0.0", "cryptography") == "up-to-date"


def test_classify_security_django():
    assert _classify_update("4.0", "4.1", "django") == "security"


# ── Real file parsing (requirements.txt) ─────────────────


def test_parse_requirements_pinned(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\nclick==8.1.7\n")
    results = UpgradeAdvisor._parse_requirements(tmp_path / "requirements.txt")
    assert ("requests", "2.28.0", str(tmp_path / "requirements.txt")) in results
    assert ("click", "8.1.7", str(tmp_path / "requirements.txt")) in results


def test_parse_requirements_unpinned(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    results = UpgradeAdvisor._parse_requirements(tmp_path / "requirements.txt")
    assert results[0][0] == "flask"
    assert results[0][1] is None


def test_parse_requirements_with_extras(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests[security]==2.28.0\n")
    results = UpgradeAdvisor._parse_requirements(tmp_path / "requirements.txt")
    assert results[0][0] == "requests"
    assert results[0][1] == "2.28.0"


def test_parse_requirements_skips_comments(tmp_path):
    (tmp_path / "requirements.txt").write_text("# comment\nflask==3.0\n")
    results = UpgradeAdvisor._parse_requirements(tmp_path / "requirements.txt")
    assert len(results) == 1
    assert results[0][0] == "flask"


def test_parse_requirements_skips_flags(tmp_path):
    (tmp_path / "requirements.txt").write_text("-r base.txt\nflask==3.0\n")
    results = UpgradeAdvisor._parse_requirements(tmp_path / "requirements.txt")
    assert len(results) == 1


# ── Real file parsing (pyproject.toml) ───────────────────


def test_parse_pyproject_pinned(tmp_path):
    toml = '[project]\ndependencies = ["flask==2.0.0", "click==8.0"]\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    results = UpgradeAdvisor._parse_pyproject(tmp_path / "pyproject.toml")
    assert len(results) == 2
    assert results[0][0] == "flask"


def test_parse_pyproject_unpinned(tmp_path):
    toml = '[project]\ndependencies = ["flask"]\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    results = UpgradeAdvisor._parse_pyproject(tmp_path / "pyproject.toml")
    assert results[0][1] is None


def test_parse_pyproject_no_deps(tmp_path):
    toml = '[project]\nname = "foo"\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    results = UpgradeAdvisor._parse_pyproject(tmp_path / "pyproject.toml")
    assert results == []


# ── scan (mock PyPI only) ────────────────────────────────


def test_scan_outdated_security(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    with patch.object(advisor, "_fetch_pypi", return_value=_pypi("requests", "2.31.0")):
        issues = advisor.scan(tmp_path)
    assert len(issues) == 1
    assert "security" in issues[0].message
    assert issues[0].severity == "block"


def test_scan_up_to_date(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("click==8.1.7\n")
    with patch.object(advisor, "_fetch_pypi", return_value=_pypi("click", "8.1.7")):
        issues = advisor.scan(tmp_path)
    assert len(issues) == 0


def test_scan_unpinned(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("click\n")
    with patch.object(advisor, "_fetch_pypi", return_value=_pypi("click", "8.1.7")):
        issues = advisor.scan(tmp_path)
    assert len(issues) == 1
    assert "unpinned" in issues[0].message.lower()


def test_scan_deprecated(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("oldpkg==1.0.0\n")
    with patch.object(
        advisor, "_fetch_pypi",
        return_value=_pypi("oldpkg", "2.0.0", summary="DEPRECATED: use newpkg"),
    ):
        issues = advisor.scan(tmp_path)
    assert any("DEPRECATED" in i.message for i in issues)


def test_scan_pyproject(advisor, tmp_path):
    toml = '[project]\ndependencies = ["flask==2.0.0"]\n'
    (tmp_path / "pyproject.toml").write_text(toml)
    with patch.object(advisor, "_fetch_pypi", return_value=_pypi("flask", "3.0.0")):
        issues = advisor.scan(tmp_path)
    assert len(issues) >= 1


def test_scan_no_deps(advisor, tmp_path):
    assert advisor.scan(tmp_path) == []


def test_scan_pypi_failure(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("somepkg==1.0\n")
    with patch.object(advisor, "_fetch_pypi", return_value=None):
        issues = advisor.scan(tmp_path)
    assert issues == []


# ── generate_report (mock PyPI only) ─────────────────────


def test_report_empty(advisor, tmp_path):
    report = advisor.generate_report(tmp_path)
    assert "No dependencies found" in report


def test_report_table(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\nclick==8.1.7\n")

    def fake(name):
        if "requests" in name:
            return _pypi("requests", "2.31.0")
        return _pypi("click", "8.1.7")

    with patch.object(advisor, "_fetch_pypi", side_effect=fake):
        report = advisor.generate_report(tmp_path)
    assert "| Package" in report
    assert "requests" in report


def test_report_priority_order(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("click==7.0.0\ncryptography==40.0.0\n")

    def fake(name):
        if "cryptography" in name:
            return _pypi("cryptography", "41.0.0")
        return _pypi("click", "8.0.0")

    with patch.object(advisor, "_fetch_pypi", side_effect=fake):
        report = advisor.generate_report(tmp_path)
    lines = [l for l in report.splitlines() if l.startswith("| ")]
    crypto_idx = next(i for i, l in enumerate(lines) if "cryptography" in l)
    click_idx = next(i for i, l in enumerate(lines) if "click" in l)
    assert crypto_idx < click_idx


def test_report_deprecated_note(advisor, tmp_path):
    (tmp_path / "requirements.txt").write_text("oldpkg==1.0\n")
    with patch.object(
        advisor, "_fetch_pypi",
        return_value=_pypi("oldpkg", "2.0", summary="DEPRECATED"),
    ):
        report = advisor.generate_report(tmp_path)
    assert "DEPRECATED" in report


# ── caching ──────────────────────────────────────────────


def test_pypi_cache_used(advisor):
    fake = _pypi("foo", "1.0.0")
    advisor._cache["foo"] = fake
    assert advisor._fetch_pypi("foo") == fake
