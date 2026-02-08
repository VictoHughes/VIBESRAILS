"""Security tests: path traversal prevention and filesystem sandbox.

Tests that validate_path() rejects directory traversal, symlinks,
oversized files, invalid paths, denied roots, and allowed roots.
"""

from __future__ import annotations

import pytest

from core.path_validator import PathValidationError, validate_path

# ── Basic path validation ────────────────────────────────────────────


def test_path_traversal_to_etc_rejected():
    """Reject path that resolves under /etc (denied root)."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/etc/shadow", must_exist=False)


def test_symlink_rejected(tmp_path):
    """Reject symlinks when follow_symlinks=False."""
    target = tmp_path / "real.txt"
    target.write_text("content")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(PathValidationError, match="Symlinks"):
        validate_path(str(link), must_exist=True, must_be_file=True, follow_symlinks=False)


def test_oversized_file_rejected(tmp_path):
    """Reject files exceeding max_size_mb."""
    big = tmp_path / "big.py"
    big.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(PathValidationError, match="too large"):
        validate_path(str(big), must_exist=True, must_be_file=True, max_size_mb=1)


def test_valid_path_accepted(tmp_path):
    """Accept valid existing file."""
    f = tmp_path / "ok.py"
    f.write_text("print('ok')")
    result = validate_path(str(f), must_exist=True, must_be_file=True)
    assert result == f.resolve()


def test_nonexistent_rejected(tmp_path):
    """Reject path that doesn't exist."""
    with pytest.raises(PathValidationError, match="does not exist"):
        validate_path(str(tmp_path / "nope.py"), must_exist=True)


def test_dir_when_file_expected_rejected(tmp_path):
    """Reject directory when must_be_file=True."""
    with pytest.raises(PathValidationError, match="not a file"):
        validate_path(str(tmp_path), must_exist=True, must_be_file=True)


def test_extension_filter(tmp_path):
    """Reject files with disallowed extensions."""
    f = tmp_path / "data.csv"
    f.write_text("a,b,c")
    with pytest.raises(PathValidationError, match="extension not allowed"):
        validate_path(str(f), must_exist=True, must_be_file=True, allowed_extensions={".py"})


def test_empty_string_rejected():
    """Reject empty string paths."""
    with pytest.raises(PathValidationError, match="non-empty string"):
        validate_path("", must_exist=False)


def test_whitespace_only_rejected():
    """Reject whitespace-only paths."""
    with pytest.raises(PathValidationError, match="non-empty string"):
        validate_path("   ", must_exist=False)


# ── Filesystem sandbox: DENIED_ROOTS ─────────────────────────────────


def test_denied_root_etc_rejected():
    """/etc is always denied."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/etc/passwd", must_exist=False)


def test_denied_root_var_log_rejected():
    """/var/log is always denied."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/var/log/syslog", must_exist=False)


def test_denied_root_proc_rejected():
    """/proc is always denied."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/proc/self/environ", must_exist=False)


def test_denied_root_sys_rejected():
    """/sys is always denied."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/sys/class", must_exist=False)


def test_denied_root_dev_rejected():
    """/dev is always denied."""
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path("/dev/null", must_exist=False)


# ── Filesystem sandbox: ALLOWED_ROOTS via env var ────────────────────


def test_allowed_roots_accepts_path_inside(tmp_path, monkeypatch):
    """Path inside ALLOWED_ROOTS is accepted."""
    f = tmp_path / "ok.py"
    f.write_text("x = 1")
    monkeypatch.setenv("VIBESRAILS_ALLOWED_ROOTS", str(tmp_path))
    result = validate_path(str(f), must_exist=True, must_be_file=True)
    assert result == f.resolve()


def test_allowed_roots_rejects_path_outside(tmp_path, monkeypatch):
    """Path outside ALLOWED_ROOTS is rejected."""
    monkeypatch.setenv("VIBESRAILS_ALLOWED_ROOTS", "/opt/allowed_project")
    with pytest.raises(PathValidationError, match="outside allowed roots"):
        validate_path(str(tmp_path / "some.py"), must_exist=False)


def test_allowed_roots_comma_separated(tmp_path, monkeypatch):
    """Multiple comma-separated roots are parsed."""
    f = tmp_path / "ok.py"
    f.write_text("x = 1")
    monkeypatch.setenv("VIBESRAILS_ALLOWED_ROOTS", f"/opt/first,{tmp_path},/opt/third")
    result = validate_path(str(f), must_exist=True, must_be_file=True)
    assert result == f.resolve()


def test_no_allowed_roots_no_restriction(tmp_path, monkeypatch):
    """Without VIBESRAILS_ALLOWED_ROOTS, non-denied paths are allowed."""
    monkeypatch.delenv("VIBESRAILS_ALLOWED_ROOTS", raising=False)
    f = tmp_path / "ok.py"
    f.write_text("x = 1")
    result = validate_path(str(f), must_exist=True, must_be_file=True)
    assert result == f.resolve()
