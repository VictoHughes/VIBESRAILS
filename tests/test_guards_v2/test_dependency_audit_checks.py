"""Tests for dependency_audit_checks.py — typosquat, abandoned, check_package."""

from datetime import datetime, timezone

from vibesrails.guards_v2.dependency_audit_checks import (
    _find_latest_release_date,
    _levenshtein,
    _make_issue,
    check_package,
    check_typosquatting,
    normalize_pkg_name,
)

# ── normalize_pkg_name ──────────────────────────────────


def test_normalize_hyphens():
    assert normalize_pkg_name("my-package") == "my-package"


def test_normalize_underscores():
    assert normalize_pkg_name("my_package") == "my-package"


def test_normalize_dots():
    assert normalize_pkg_name("my.package") == "my-package"


def test_normalize_mixed():
    assert normalize_pkg_name("My_Cool.Package") == "my-cool-package"


def test_normalize_consecutive():
    assert normalize_pkg_name("my__pkg") == "my-pkg"


# ── _levenshtein ────────────────────────────────────────


def test_levenshtein_same():
    assert _levenshtein("abc", "abc") == 0


def test_levenshtein_one_insert():
    assert _levenshtein("abc", "abcd") == 1


def test_levenshtein_one_replace():
    assert _levenshtein("abc", "axc") == 1


def test_levenshtein_empty():
    assert _levenshtein("", "abc") == 3
    assert _levenshtein("abc", "") == 3


def test_levenshtein_completely_different():
    assert _levenshtein("abc", "xyz") == 3


# ── check_typosquatting ────────────────────────────────


def test_typosquat_detected():
    # "reqeusts" is 2 edits from "requests"
    result = check_typosquatting("reqeusts")
    assert result == "requests"


def test_typosquat_exact_match():
    # Exact match with popular package should NOT be flagged
    assert check_typosquatting("requests") is None


def test_typosquat_no_match():
    # Completely different name
    assert check_typosquatting("zzzuniquepkg") is None


def test_typosquat_close_to_flask():
    # "flaask" is 1 edit from "flask"
    result = check_typosquatting("flaask")
    assert result == "flask"


# ── _find_latest_release_date ───────────────────────────


def test_find_latest_release_date_basic():
    releases = {
        "1.0.0": [{"upload_time_iso_8601": "2024-01-01T00:00:00Z"}],
        "2.0.0": [{"upload_time_iso_8601": "2025-06-15T12:00:00Z"}],
    }
    result = _find_latest_release_date(releases)
    assert result is not None
    assert result.year == 2025
    assert result.month == 6


def test_find_latest_release_date_empty():
    assert _find_latest_release_date({}) is None


def test_find_latest_release_date_no_upload_time():
    releases = {"1.0.0": [{"filename": "pkg-1.0.0.tar.gz"}]}
    assert _find_latest_release_date(releases) is None


def test_find_latest_release_date_uses_upload_time_fallback():
    releases = {
        "1.0.0": [{"upload_time": "2024-06-01T00:00:00"}],
    }
    result = _find_latest_release_date(releases)
    assert result is not None
    assert result.year == 2024


# ── _make_issue ─────────────────────────────────────────


def test_make_issue_fields():
    issue = _make_issue("block", "Bad package", "req.txt", 5)
    assert issue.guard == "DependencyAuditGuard"
    assert issue.severity == "block"
    assert issue.message == "Bad package"
    assert issue.file == "req.txt"
    assert issue.line == 5


def test_make_issue_no_line():
    issue = _make_issue("warn", "Unpinned", "req.txt", None)
    assert issue.line is None


# ── check_package ───────────────────────────────────────


def test_check_package_unpinned():
    issues = check_package("somepkg", None, "req.txt", 1, {})
    assert any("Unpinned" in i.message for i in issues)


def test_check_package_known_bad_version():
    issues = check_package("urllib3", "1.24", "req.txt", 1, {})
    assert any("vulnerable" in i.message.lower() for i in issues)


def test_check_package_typosquat():
    issues = check_package("reqeusts", "1.0.0", "req.txt", 1, {})
    assert any("typosquatting" in i.message.lower() for i in issues)


def test_check_package_clean():
    # Normal package, pinned, not typosquat, cache returns None (no PyPI)
    issues = check_package("someuniquepackage", "1.0.0", "req.txt", 1, {"someuniquepackage": None})
    assert len(issues) == 0


def test_check_package_abandoned():
    """Package with no release for >2 years should be flagged."""
    old_date = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
    cache = {
        "old-pkg": {
            "info": {"version": "0.1.0"},
            "releases": {
                "0.1.0": [{"upload_time_iso_8601": old_date}],
            },
        }
    }
    issues = check_package("old-pkg", "0.1.0", "req.txt", 1, cache)
    assert any("abandoned" in i.message.lower() for i in issues)
