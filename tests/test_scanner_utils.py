"""Tests for vibesrails scanner — utility functions."""

import os
import re
import subprocess
from unittest import mock

# ============================================
# is_git_repo Tests
# ============================================

def test_is_git_repo_true(tmp_path):
    """Test is_git_repo returns True in a git repo."""
    from vibesrails.scanner import is_git_repo

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Initialize a git repo
        subprocess.run(["git", "init"], capture_output=True, cwd=tmp_path)
        assert is_git_repo() is True
    finally:
        os.chdir(original_cwd)


def test_is_git_repo_false(tmp_path):
    """Test is_git_repo returns False outside a git repo."""
    from vibesrails.scanner import is_git_repo

    original_cwd = os.getcwd()
    # Create a subdir that's definitely not a git repo
    non_git_dir = tmp_path / "not_a_repo"
    non_git_dir.mkdir()
    os.chdir(non_git_dir)

    try:
        # Mock git command to fail (no git repo)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1)
            assert is_git_repo() is False
    finally:
        os.chdir(original_cwd)


# ============================================
# get_staged_files Tests
# ============================================

def test_get_staged_files_no_git_repo(tmp_path):
    """Test get_staged_files returns empty list when not in git repo."""
    from vibesrails.scanner import get_staged_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1)
            assert get_staged_files() == []
    finally:
        os.chdir(original_cwd)


def test_get_staged_files_git_command_fails(tmp_path):
    """Test get_staged_files returns empty list when git command fails."""
    from vibesrails.scanner import get_staged_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        call_count = 0
        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # is_git_repo call succeeds
                return mock.Mock(returncode=0)
            # get_staged_files git diff call fails
            return mock.Mock(returncode=1, stdout="")

        with mock.patch("subprocess.run", side_effect=_side_effect):
            assert get_staged_files() == []
    finally:
        os.chdir(original_cwd)


def test_get_staged_files_filters_py_files(tmp_path):
    """Test get_staged_files returns only .py files that exist."""
    from vibesrails.scanner import get_staged_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Create test files
    (tmp_path / "test.py").write_text("# test")
    (tmp_path / "data.json").write_text("{}")

    try:
        call_count = 0
        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # is_git_repo call succeeds
                return mock.Mock(returncode=0)
            # get_staged_files git diff returns file list
            return mock.Mock(
                returncode=0,
                stdout="test.py\ndata.json\nnonexistent.py\n"
            )

        with mock.patch("subprocess.run", side_effect=_side_effect):
            files = get_staged_files()
            assert "test.py" in files
            assert "data.json" not in files
            assert "nonexistent.py" not in files
    finally:
        os.chdir(original_cwd)


# ============================================
# matches_pattern Tests
# ============================================

def test_matches_pattern_recursive_glob():
    """Test ** patterns (recursive)."""
    from vibesrails.scanner import matches_pattern

    assert matches_pattern("src/api/routes.py", ["**/api/**"]) is True
    # Note: Path.match with ** at start requires at least one directory before match
    # "api/routes.py" doesn't match "**/api/**" because Path.match requires parent dirs
    assert matches_pattern("src/utils/helpers.py", ["**/api/**"]) is False
    # Test pattern that matches at root level
    assert matches_pattern("api/routes.py", ["api/**"]) is True


def test_matches_pattern_simple_glob():
    """Test simple glob patterns (fnmatch)."""
    from vibesrails.scanner import matches_pattern

    assert matches_pattern("test_foo.py", ["test_*.py"]) is True
    assert matches_pattern("src/test_foo.py", ["test_*.py"]) is True
    assert matches_pattern("foo_test.py", ["test_*.py"]) is False


def test_matches_pattern_multiple_patterns():
    """Test matching against multiple patterns."""
    from vibesrails.scanner import matches_pattern

    patterns = ["test_*.py", "*_test.py", "**/tests/**"]
    assert matches_pattern("test_foo.py", patterns) is True
    assert matches_pattern("foo_test.py", patterns) is True
    assert matches_pattern("src/tests/helper.py", patterns) is True
    assert matches_pattern("src/main.py", patterns) is False


def test_matches_pattern_empty_patterns():
    """Test empty pattern list."""
    from vibesrails.scanner import matches_pattern

    assert matches_pattern("any_file.py", []) is False


# ============================================
# is_test_file Tests
# ============================================

def test_is_test_file_prefix():
    """Test test_*.py prefix detection."""
    from vibesrails.scanner import is_test_file

    assert is_test_file("test_scanner.py") is True
    assert is_test_file("src/test_scanner.py") is True


def test_is_test_file_suffix():
    """Test *_test.py suffix detection."""
    from vibesrails.scanner import is_test_file

    assert is_test_file("scanner_test.py") is True
    assert is_test_file("src/scanner_test.py") is True


def test_is_test_file_tests_dir():
    """Test /tests/ in path detection."""
    from vibesrails.scanner import is_test_file

    assert is_test_file("src/tests/helper.py") is True
    assert is_test_file("/tests/conftest.py") is True


def test_is_test_file_not_test():
    """Test non-test files."""
    from vibesrails.scanner import is_test_file

    assert is_test_file("scanner.py") is False
    assert is_test_file("src/main.py") is False


# ============================================
# is_line_suppressed Tests
# ============================================

def test_is_line_suppressed_ignore():
    """Test # vibesrails: ignore suppression."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"  # vibesrails: ignore'
    assert is_line_suppressed(line, "any_pattern") is True


def test_is_line_suppressed_disable():
    """Test # vibesrails: disable suppression."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"  # vibesrails: disable'
    assert is_line_suppressed(line, "any_pattern") is True


def test_is_line_suppressed_noqa():
    """Test # noqa: vibesrails suppression."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"  # noqa: vibesrails'
    assert is_line_suppressed(line, "any_pattern") is True


def test_is_line_suppressed_specific_pattern_match():
    """Test pattern-specific suppression when pattern matches."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"  # vibesrails: ignore [my_pattern]'
    assert is_line_suppressed(line, "my_pattern") is True


def test_is_line_suppressed_specific_pattern_no_match():
    """Test pattern-specific suppression when pattern doesn't match."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"  # vibesrails: ignore [other_pattern]'
    assert is_line_suppressed(line, "my_pattern") is False


def test_is_line_suppressed_multiple_patterns():
    """Test pattern-specific suppression with multiple patterns."""
    from vibesrails.scanner import is_line_suppressed

    line = 'code  # vibesrails: ignore [pattern1, pattern2, pattern3]'
    assert is_line_suppressed(line, "pattern1") is True
    assert is_line_suppressed(line, "pattern2") is True
    assert is_line_suppressed(line, "pattern4") is False


def test_is_line_suppressed_next_line():
    """Test # vibesrails: ignore-next-line suppression."""
    from vibesrails.scanner import is_line_suppressed

    current_line = 'password = "secret"'
    prev_line = '# vibesrails: ignore-next-line'
    assert is_line_suppressed(current_line, "any_pattern", prev_line) is True


def test_is_line_suppressed_no_suppression():
    """Test line without suppression."""
    from vibesrails.scanner import is_line_suppressed

    line = 'password = "secret"'
    assert is_line_suppressed(line, "any_pattern") is False


# ============================================
# safe_regex_search Tests
# ============================================

def test_safe_regex_search_normal():
    """Test normal regex search."""
    from vibesrails.scanner import safe_regex_search

    assert safe_regex_search(r"password", "password = secret") is True
    assert safe_regex_search(r"password", "name = value") is False


def test_safe_regex_search_long_text_truncated():
    """Test text longer than 10000 chars is truncated."""
    from vibesrails.scanner import safe_regex_search

    # Pattern at start should be found
    text = "target" + "x" * 20000
    assert safe_regex_search(r"target", text) is True

    # Pattern past 10000 chars should not be found
    text = "x" * 10001 + "target"
    assert safe_regex_search(r"target", text) is False


def test_safe_regex_search_invalid_regex():
    """Test invalid regex returns False."""
    from vibesrails.scanner import safe_regex_search

    # Invalid regex pattern
    assert safe_regex_search(r"[invalid", "text") is False


def test_safe_regex_search_with_flags():
    """Test regex search with flags."""
    from vibesrails.scanner import safe_regex_search

    assert safe_regex_search(r"PASSWORD", "password", re.IGNORECASE) is True
    assert safe_regex_search(r"PASSWORD", "password", 0) is False


# ============================================
# is_path_safe Tests
# ============================================

def test_is_path_safe_within_cwd(tmp_path):
    """Test path within current working directory."""
    from vibesrails.scanner import is_path_safe

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "safe.py"
        test_file.write_text("# safe")
        assert is_path_safe(str(test_file)) is True
    finally:
        os.chdir(original_cwd)


def test_is_path_safe_outside_cwd(tmp_path):
    """Test path outside current working directory (path traversal)."""
    from vibesrails.scanner import is_path_safe

    original_cwd = os.getcwd()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    os.chdir(subdir)

    try:
        # Parent directory path
        assert is_path_safe("../outside.py") is False
        # Absolute path outside cwd
        assert is_path_safe("/etc/passwd") is False
    finally:
        os.chdir(original_cwd)


def test_is_path_safe_traversal_attempt(tmp_path):
    """Test path traversal attack attempt."""
    from vibesrails.scanner import is_path_safe

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        assert is_path_safe("../../../etc/passwd") is False
        assert is_path_safe("/tmp/../etc/passwd") is False
    finally:
        os.chdir(original_cwd)
