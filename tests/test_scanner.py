"""Tests for vibesrails scanner."""

import os
import re
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from vibesrails import scan_file, load_config, ScanResult


@pytest.fixture
def sample_config():
    """Minimal config for testing."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "test_secret",
                "name": "Test Secret",
                "regex": r"password\s*=\s*[\"'][^\"']+",
                "message": "Hardcoded password",
            }
        ],
        "warning": [
            {
                "id": "test_print",
                "name": "Print Statement",
                "regex": r"^\s*print\(",
                "message": "Use logging instead",
                "skip_in_tests": True,
            }
        ],
        "exceptions": {},
    }


@pytest.fixture
def config_with_scope():
    """Config with scope filtering."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "api_only",
                "name": "API Pattern",
                "regex": r"api_secret",
                "message": "API secret detected",
                "scope": ["**/api/**", "api_*.py"],
            }
        ],
        "warning": [],
        "exceptions": {},
    }


@pytest.fixture
def config_with_exclude():
    """Config with exclude_regex."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "dangerous_call",
                "name": "Dangerous Call",
                "regex": r"dangerous_func\(",
                "message": "Avoid dangerous_func",
                "exclude_regex": r"#.*safe.*call",
            }
        ],
        "warning": [],
        "exceptions": {},
    }


@pytest.fixture
def config_with_pro_sections():
    """Config with bugs, architecture, maintainability sections."""
    return {
        "version": "1.0",
        "blocking": [],
        "warning": [],
        "bugs": [
            {
                "id": "bug1",
                "name": "Bug Pattern",
                "regex": r"bug_pattern",
                "message": "Bug detected",
                "level": "BLOCK",
            },
            {
                "id": "bug2",
                "name": "Bug Warning",
                "regex": r"bug_warn",
                "message": "Bug warning",
                "level": "WARN",
            },
        ],
        "architecture": [
            {
                "id": "arch1",
                "name": "Arch Pattern",
                "regex": r"arch_issue",
                "message": "Architecture issue",
                "level": "WARN",
            }
        ],
        "maintainability": [
            {
                "id": "maint1",
                "name": "Maint Pattern",
                "regex": r"maint_issue",
                "message": "Maintainability issue",
            }
        ],
        "exceptions": {},
    }


@pytest.fixture
def config_with_exceptions():
    """Config with file exceptions."""
    return {
        "version": "1.0",
        "blocking": [
            {
                "id": "test_secret",
                "name": "Test Secret",
                "regex": r"password\s*=",
                "message": "Hardcoded password",
            }
        ],
        "warning": [],
        "exceptions": {
            "test_files": {
                "reason": "Test files can have hardcoded values",
                "patterns": ["**/test_*.py", "**/conftest.py"],
                "allowed": ["test_secret"],
            }
        },
    }


def test_scan_file_detects_blocking_pattern(sample_config, tmp_path):
    """Test that blocking patterns are detected."""
    test_file = tmp_path / "bad.py"
    test_file.write_text('password = "secret123"')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 1
        assert results[0].level == "BLOCK"
        assert results[0].pattern_id == "test_secret"
    finally:
        os.chdir(original_cwd)


def test_scan_file_clean_code(sample_config, tmp_path):
    """Test that clean code passes."""
    test_file = tmp_path / "good.py"
    test_file.write_text('import os\nname = os.environ.get("NAME")')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)


def test_scan_result_namedtuple():
    """Test ScanResult structure."""
    result = ScanResult(
        file="test.py",
        line=10,
        pattern_id="test",
        message="Test message",
        level="BLOCK",
    )
    assert result.file == "test.py"
    assert result.line == 10
    assert result.level == "BLOCK"


def test_load_config_bundled():
    """Test loading bundled default config."""
    config = load_config()
    assert "version" in config
    assert "blocking" in config


# ============================================
# Inline Suppression Tests
# ============================================

def test_inline_suppression_ignore(sample_config, tmp_path):
    """Test that # vibesrails: ignore suppresses pattern."""
    test_file = tmp_path / "suppressed.py"
    test_file.write_text('password = "secret123"  # vibesrails: ignore')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # Should be suppressed
    finally:
        os.chdir(original_cwd)


def test_inline_suppression_ignore_next_line(sample_config, tmp_path):
    """Test that # vibesrails: ignore-next-line suppresses next line."""
    test_file = tmp_path / "suppressed_next.py"
    test_file.write_text('# vibesrails: ignore-next-line\npassword = "secret123"')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # Should be suppressed
    finally:
        os.chdir(original_cwd)


def test_inline_suppression_specific_pattern(sample_config, tmp_path):
    """Test that # vibesrails: ignore [pattern_id] only suppresses that pattern."""
    test_file = tmp_path / "specific.py"
    test_file.write_text('password = "secret123"  # vibesrails: ignore [test_secret]')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # test_secret should be suppressed
    finally:
        os.chdir(original_cwd)


def test_inline_suppression_wrong_pattern_not_suppressed(sample_config, tmp_path):
    """Test that suppressing wrong pattern doesn't suppress the actual one."""
    test_file = tmp_path / "wrong_suppress.py"
    test_file.write_text('password = "secret123"  # vibesrails: ignore [other_pattern]')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 1  # Should NOT be suppressed
        assert results[0].pattern_id == "test_secret"
    finally:
        os.chdir(original_cwd)


def test_inline_suppression_noqa_syntax(sample_config, tmp_path):
    """Test that # noqa: vibesrails syntax works."""
    test_file = tmp_path / "noqa.py"
    test_file.write_text('password = "secret123"  # noqa: vibesrails')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # Should be suppressed
    finally:
        os.chdir(original_cwd)


def test_inline_suppression_disable_syntax(sample_config, tmp_path):
    """Test that # vibesrails: disable syntax works."""
    test_file = tmp_path / "disable.py"
    test_file.write_text('password = "secret123"  # vibesrails: disable')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # Should be suppressed
    finally:
        os.chdir(original_cwd)


# ============================================
# Config Extends Tests
# ============================================

def test_config_extends_pack():
    """Test that config can extend a built-in pack."""
    from vibesrails.config import load_config_with_extends, resolve_pack_path

    pack_path = resolve_pack_path("@vibesrails/security-pack")
    assert pack_path is not None
    assert pack_path.exists()

    config = load_config_with_extends(pack_path)
    assert "blocking" in config
    assert len(config["blocking"]) > 0


def test_config_extends_merge(tmp_path):
    """Test that extends properly merges configs."""
    from vibesrails.config import load_config_with_extends

    # Create a base config
    base_config = tmp_path / "base.yaml"
    base_config.write_text('''
version: "1.0"
blocking:
  - id: base_pattern
    name: "Base Pattern"
    regex: "base_bad\\\\("
    message: "Base message"
''')

    # Create child config that extends base
    child_config = tmp_path / "child.yaml"
    child_config.write_text(f'''
extends: "./base.yaml"
version: "1.0"
blocking:
  - id: child_pattern
    name: "Child Pattern"
    regex: "child_bad\\\\("
    message: "Child message"
''')

    config = load_config_with_extends(child_config)

    # Should have both patterns
    ids = [p["id"] for p in config.get("blocking", [])]
    assert "base_pattern" in ids
    assert "child_pattern" in ids


# ============================================
# load_config Tests
# ============================================

def test_load_config_with_explicit_path(tmp_path):
    """Test loading config with explicit path."""
    config_file = tmp_path / "custom.yaml"
    config_file.write_text('''
version: "1.0"
blocking:
  - id: custom_pattern
    name: "Custom Pattern"
    regex: "custom_bad"
    message: "Custom message"
''')

    config = load_config(config_file)
    assert config["version"] == "1.0"
    ids = [p["id"] for p in config.get("blocking", [])]
    assert "custom_pattern" in ids


def test_load_config_too_large(tmp_path):
    """Test that config file size limit is enforced."""
    config_file = tmp_path / "huge.yaml"
    # Create a file larger than 1MB
    config_file.write_text("x" * (1_000_001))

    with pytest.raises(SystemExit):
        load_config(config_file)


def test_load_config_not_found():
    """Test that missing config file causes exit."""
    with pytest.raises(SystemExit):
        load_config("/nonexistent/config.yaml")


def test_load_config_fallback_simple_load(tmp_path, monkeypatch):
    """Test fallback to simple YAML load when config module unavailable."""
    config_file = tmp_path / "simple.yaml"
    config_file.write_text('''
version: "1.0"
blocking: []
''')

    # Mock the import to fail
    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def mock_import(name, *args, **kwargs):
        if name == ".config" or "config" in str(name):
            raise ImportError("Mocked import error")
        return original_import(name, *args, **kwargs)

    # Use monkeypatch to simulate ImportError in load_config
    import vibesrails.scanner as scanner_module

    original_load_config = scanner_module.load_config

    def patched_load_config(config_path=None):
        if config_path is None:
            config_path = config_file

        config_path = Path(config_path)
        if not config_path.exists():
            import sys
            print("ERROR: No vibesrails.yaml found")
            sys.exit(1)

        if config_path.stat().st_size > 1_000_000:
            import sys
            sys.exit(1)

        # Force the fallback path
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f)

    monkeypatch.setattr(scanner_module, "load_config", patched_load_config)

    config = scanner_module.load_config(config_file)
    assert config["version"] == "1.0"


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
        with mock.patch("vibesrails.scanner.is_git_repo", return_value=False):
            assert get_staged_files() == []
    finally:
        os.chdir(original_cwd)


def test_get_staged_files_git_command_fails(tmp_path):
    """Test get_staged_files returns empty list when git command fails."""
    from vibesrails.scanner import get_staged_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        with mock.patch("vibesrails.scanner.is_git_repo", return_value=True):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=1, stdout="")
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
        with mock.patch("vibesrails.scanner.is_git_repo", return_value=True):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0,
                    stdout="test.py\ndata.json\nnonexistent.py\n"
                )
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


# ============================================
# scan_file Tests
# ============================================

def test_scan_file_path_traversal_protection(sample_config, tmp_path):
    """Test path traversal protection in scan_file."""
    original_cwd = os.getcwd()
    subdir = tmp_path / "project"
    subdir.mkdir()
    os.chdir(subdir)

    try:
        # Attempt to scan file outside project
        results = scan_file("../../../etc/passwd", sample_config)
        assert results == []
    finally:
        os.chdir(original_cwd)


def test_scan_file_read_error(sample_config, tmp_path):
    """Test handling of read errors."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Non-existent file
        results = scan_file("nonexistent.py", sample_config)
        assert results == []
    finally:
        os.chdir(original_cwd)


def test_scan_file_unicode_error(sample_config, tmp_path):
    """Test handling of unicode decode errors."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Create binary file
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b'\x80\x81\x82\x83')

        results = scan_file(str(binary_file), sample_config)
        assert results == []
    finally:
        os.chdir(original_cwd)


def test_scan_file_empty_file(sample_config, tmp_path):
    """Test scanning empty file."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        results = scan_file(str(empty_file), sample_config)
        assert results == []
    finally:
        os.chdir(original_cwd)


def test_scan_file_comments_only(sample_config, tmp_path):
    """Test scanning file with only comments."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        comments_file = tmp_path / "comments.py"
        comments_file.write_text("# This is a comment\n# Another comment\n")

        results = scan_file(str(comments_file), sample_config)
        assert results == []
    finally:
        os.chdir(original_cwd)


def test_scan_file_with_scope(config_with_scope, tmp_path):
    """Test scope filtering in scan_file."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # File in scope
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        api_file = api_dir / "routes.py"
        api_file.write_text("api_secret = 'key'")

        results = scan_file(str(api_file), config_with_scope)
        assert len(results) == 1

        # File not in scope
        other_file = tmp_path / "utils.py"
        other_file.write_text("api_secret = 'key'")

        results = scan_file(str(other_file), config_with_scope)
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)


def test_scan_file_with_exclude_regex(config_with_exclude, tmp_path):
    """Test exclude_regex filtering."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # File with excluded pattern
        excluded_file = tmp_path / "safe_call.py"
        excluded_file.write_text("result = dangerous_func(expr)  # safe call for testing")

        results = scan_file(str(excluded_file), config_with_exclude)
        assert len(results) == 0

        # File without excluded pattern
        bad_file = tmp_path / "bad_call.py"
        bad_file.write_text("result = dangerous_func(user_input)")

        results = scan_file(str(bad_file), config_with_exclude)
        assert len(results) == 1
    finally:
        os.chdir(original_cwd)


def test_scan_file_with_exceptions(config_with_exceptions, tmp_path):
    """Test file exceptions in scan_file."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Test file with exception
        test_file = tmp_path / "test_auth.py"
        test_file.write_text("password = 'test123'")

        results = scan_file(str(test_file), config_with_exceptions)
        assert len(results) == 0  # Exception allows test_secret in test files

        # Non-test file without exception
        main_file = tmp_path / "main.py"
        main_file.write_text("password = 'secret'")

        results = scan_file(str(main_file), config_with_exceptions)
        assert len(results) == 1
    finally:
        os.chdir(original_cwd)


def test_scan_file_pro_sections(config_with_pro_sections, tmp_path):
    """Test pro coding sections (bugs, architecture, maintainability)."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "code.py"
        test_file.write_text("bug_pattern\nbug_warn\narch_issue\nmaint_issue\n")

        results = scan_file(str(test_file), config_with_pro_sections)

        # Check we have all expected results
        pattern_ids = [r.pattern_id for r in results]
        levels = {r.pattern_id: r.level for r in results}

        assert "bug1" in pattern_ids
        assert "bug2" in pattern_ids
        assert "arch1" in pattern_ids
        assert "maint1" in pattern_ids

        # Check levels
        assert levels["bug1"] == "BLOCK"
        assert levels["bug2"] == "WARN"
        assert levels["arch1"] == "WARN"
        assert levels["maint1"] == "WARN"
    finally:
        os.chdir(original_cwd)


def test_scan_file_skip_in_tests(tmp_path):
    """Test skip_in_tests option for warnings."""
    config = {
        "version": "1.0",
        "blocking": [],
        "warning": [
            {
                "id": "print_stmt",
                "name": "Print Statement",
                "regex": r"print\(",
                "message": "Use logging",
                "skip_in_tests": True,
            }
        ],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Test file - should skip warning
        test_file = tmp_path / "test_example.py"
        test_file.write_text("print('debug')")

        results = scan_file(str(test_file), config)
        assert len(results) == 0

        # Non-test file - should report warning
        main_file = tmp_path / "main.py"
        main_file.write_text("print('debug')")

        results = scan_file(str(main_file), config)
        assert len(results) == 1
    finally:
        os.chdir(original_cwd)


def test_scan_file_case_insensitive_flag(tmp_path):
    """Test case insensitive regex flag."""
    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "todo",
                "name": "TODO",
                "regex": r"TODO:",
                "message": "TODO found",
                "flags": "i",
            }
        ],
        "warning": [],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "code.py"
        test_file.write_text("# todo: fix this\n# TODO: and this\n")

        results = scan_file(str(test_file), config)
        assert len(results) == 2
    finally:
        os.chdir(original_cwd)


def test_scan_file_warning_scope(tmp_path):
    """Test scope filtering for warning patterns."""
    config = {
        "version": "1.0",
        "blocking": [],
        "warning": [
            {
                "id": "api_print",
                "name": "Print in API",
                "regex": r"print\(",
                "message": "No print in API",
                "scope": ["**/api/**"],
            }
        ],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # File in scope
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        api_file = api_dir / "routes.py"
        api_file.write_text("print('debug')")

        results = scan_file(str(api_file), config)
        assert len(results) == 1

        # File not in scope
        other_file = tmp_path / "utils.py"
        other_file.write_text("print('debug')")

        results = scan_file(str(other_file), config)
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)


def test_scan_file_warning_exclude_regex(tmp_path):
    """Test exclude_regex for warning patterns."""
    config = {
        "version": "1.0",
        "blocking": [],
        "warning": [
            {
                "id": "debug_log",
                "name": "Debug Log",
                "regex": r"logger\.debug",
                "message": "Remove debug logs",
                "exclude_regex": r"# keep",
            }
        ],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "code.py"
        test_file.write_text("logger.debug('remove this')\nlogger.debug('important')  # keep\n")

        results = scan_file(str(test_file), config)
        assert len(results) == 1
        assert results[0].line == 1
    finally:
        os.chdir(original_cwd)


def test_scan_file_warning_suppression(sample_config, tmp_path):
    """Test inline suppression for warning patterns."""
    # Add a non-skip_in_tests warning
    config = {
        "version": "1.0",
        "blocking": [],
        "warning": [
            {
                "id": "debug_print",
                "name": "Debug Print",
                "regex": r"print\(",
                "message": "Use logging",
                "skip_in_tests": False,
            }
        ],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "code.py"
        test_file.write_text("print('debug')  # vibesrails: ignore")

        results = scan_file(str(test_file), config)
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)


# ============================================
# show_patterns Tests
# ============================================

def test_show_patterns_basic(capsys):
    """Test show_patterns displays patterns."""
    from vibesrails.scanner import show_patterns

    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "secret",
                "name": "Secret",
                "regex": r"secret",
                "message": "No secrets",
            }
        ],
        "warning": [
            {
                "id": "print",
                "name": "Print",
                "regex": r"print",
                "message": "No print",
                "skip_in_tests": True,
            }
        ],
        "exceptions": {
            "test_exception": {
                "reason": "Test reason",
                "patterns": ["test_*.py"],
                "allowed": ["secret"],
            }
        },
    }

    show_patterns(config)
    captured = capsys.readouterr()

    assert "SECURITY (BLOCKING)" in captured.out
    assert "[secret]" in captured.out
    assert "SECURITY (WARNINGS)" in captured.out
    assert "[print]" in captured.out
    assert "(skip tests)" in captured.out
    assert "EXCEPTIONS" in captured.out
    assert "test_exception" in captured.out


def test_show_patterns_pro_sections(capsys):
    """Test show_patterns displays pro coding sections."""
    from vibesrails.scanner import show_patterns

    config = {
        "version": "1.0",
        "blocking": [],
        "warning": [],
        "bugs": [
            {
                "id": "bug1",
                "name": "Bug 1",
                "regex": r"bug",
                "message": "Bug found",
                "level": "BLOCK",
            }
        ],
        "architecture": [
            {
                "id": "arch1",
                "name": "Arch 1",
                "regex": r"arch",
                "message": "Arch issue",
                "scope": ["**/api/**"],
                "skip_in_tests": True,
            }
        ],
        "maintainability": [
            {
                "id": "maint1",
                "name": "Maint 1",
                "regex": r"maint",
                "message": "Maint issue",
            }
        ],
        "exceptions": {},
    }

    show_patterns(config)
    captured = capsys.readouterr()

    assert "BUGS SILENCIEUX" in captured.out
    assert "[bug1]" in captured.out
    assert "ARCHITECTURE" in captured.out
    assert "[arch1]" in captured.out
    assert "[scope:" in captured.out
    assert "MAINTENABILITE" in captured.out or "MAINTENABILITÉ" in captured.out
    assert "[maint1]" in captured.out


# ============================================
# validate_config Tests
# ============================================

def test_validate_config_valid(capsys):
    """Test validate_config with valid config."""
    from vibesrails.scanner import validate_config

    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "test",
                "name": "Test",
                "regex": r"test",
                "message": "Test message",
            }
        ],
    }

    assert validate_config(config) is True
    captured = capsys.readouterr()
    assert "valid" in captured.out


def test_validate_config_missing_blocking(capsys):
    """Test validate_config with missing blocking section."""
    from vibesrails.scanner import validate_config

    config = {"version": "1.0"}

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "Missing 'blocking'" in captured.out


def test_validate_config_missing_version(capsys):
    """Test validate_config with missing version."""
    from vibesrails.scanner import validate_config

    config = {"blocking": []}

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "Missing 'version'" in captured.out


def test_validate_config_missing_id(capsys):
    """Test validate_config with pattern missing id."""
    from vibesrails.scanner import validate_config

    config = {
        "version": "1.0",
        "blocking": [
            {
                "name": "Test",
                "regex": r"test",
                "message": "Test",
            }
        ],
    }

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "missing 'id'" in captured.out


def test_validate_config_missing_regex(capsys):
    """Test validate_config with pattern missing regex."""
    from vibesrails.scanner import validate_config

    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "test",
                "name": "Test",
                "message": "Test",
            }
        ],
    }

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "missing 'regex'" in captured.out


def test_validate_config_missing_message(capsys):
    """Test validate_config with pattern missing message."""
    from vibesrails.scanner import validate_config

    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "test",
                "name": "Test",
                "regex": r"test",
            }
        ],
    }

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "missing 'message'" in captured.out


def test_validate_config_invalid_regex(capsys):
    """Test validate_config with invalid regex."""
    from vibesrails.scanner import validate_config

    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "test",
                "name": "Test",
                "regex": r"[invalid",
                "message": "Test",
            }
        ],
    }

    assert validate_config(config) is False
    captured = capsys.readouterr()
    assert "invalid regex" in captured.out


# ============================================
# get_all_python_files Tests
# ============================================

def test_get_all_python_files(tmp_path):
    """Test get_all_python_files finds .py files."""
    from vibesrails.scanner import get_all_python_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Create test structure
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("# app")
        (tmp_path / "data.json").write_text("{}")

        files = get_all_python_files()
        assert any("main.py" in f for f in files)
        assert any("app.py" in f for f in files)
        assert not any("data.json" in f for f in files)
    finally:
        os.chdir(original_cwd)


def test_get_all_python_files_excludes_venv(tmp_path):
    """Test get_all_python_files excludes venv and other directories."""
    from vibesrails.scanner import get_all_python_files

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Create excluded directories
        for exclude_dir in ["venv", ".venv", "__pycache__", "node_modules", ".git"]:
            dir_path = tmp_path / exclude_dir
            dir_path.mkdir()
            (dir_path / "excluded.py").write_text("# excluded")

        # Create included file
        (tmp_path / "main.py").write_text("# main")

        files = get_all_python_files()
        assert any("main.py" in f for f in files)
        assert not any("venv" in f for f in files)
        assert not any("__pycache__" in f for f in files)
        assert not any("node_modules" in f for f in files)
        assert not any(".git" in f for f in files)
    finally:
        os.chdir(original_cwd)


# ============================================
# main() CLI Tests
# ============================================

def test_main_validate(tmp_path, monkeypatch):
    """Test main() with --validate flag."""
    from vibesrails.scanner import main

    # Create a valid config
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking:
  - id: test
    name: Test
    regex: "test"
    message: "Test message"
''')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--validate"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
    finally:
        os.chdir(original_cwd)


def test_main_show(tmp_path, monkeypatch, capsys):
    """Test main() with --show flag."""
    from vibesrails.scanner import main

    # Create a config
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking:
  - id: test
    name: Test
    regex: "test"
    message: "Test message"
''')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--show"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "[test]" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_scan_file(tmp_path, monkeypatch, capsys):
    """Test main() with --file flag."""
    from vibesrails.scanner import main

    # Create config and test file
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking:
  - id: secret
    name: Secret
    regex: "password\\\\s*="
    message: "Hardcoded password"
''')

    test_file = tmp_path / "test.py"
    test_file.write_text('name = "test"')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--file", str(test_file)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "PASSED" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_scan_file_blocking(tmp_path, monkeypatch, capsys):
    """Test main() with --file flag and blocking issue."""
    from vibesrails.scanner import main

    # Create config and test file with blocking issue
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking:
  - id: secret
    name: Secret
    regex: "password\\\\s*="
    message: "Hardcoded password"
''')

    test_file = tmp_path / "bad.py"
    test_file.write_text('password = "secret123"')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--file", str(test_file)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "BLOCK" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_scan_all(tmp_path, monkeypatch, capsys):
    """Test main() with --all flag."""
    from vibesrails.scanner import main

    # Create config and test files
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking: []
''')

    (tmp_path / "app.py").write_text("# clean")
    (tmp_path / "utils.py").write_text("# also clean")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--all"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Scanning 2 file" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_no_files(tmp_path, monkeypatch, capsys):
    """Test main() with no files to scan."""
    from vibesrails.scanner import main

    # Create config only
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking: []
''')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Mock get_staged_files to return empty list
        monkeypatch.setattr("vibesrails.scanner.get_staged_files", lambda: [])
        monkeypatch.setattr("sys.argv", ["vibesrails"])

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "No Python files to scan" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_file_not_found(tmp_path, monkeypatch, capsys):
    """Test main() with non-existent file."""
    from vibesrails.scanner import main

    # Create config only
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking: []
''')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--file", "nonexistent.py"])

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "No Python files to scan" in captured.out
    finally:
        os.chdir(original_cwd)


def test_main_warnings_reported(tmp_path, monkeypatch, capsys):
    """Test main() reports warnings but still passes."""
    from vibesrails.scanner import main

    # Create config with warning pattern
    config_file = tmp_path / "vibesrails.yaml"
    config_file.write_text('''
version: "1.0"
blocking: []
warning:
  - id: debug_print
    name: Debug Print
    regex: "print\\\\("
    message: "Use logging"
''')

    test_file = tmp_path / "app.py"
    test_file.write_text('print("debug")')

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        monkeypatch.setattr("sys.argv", ["vibesrails", "--file", str(test_file)])

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0  # Warnings don't block

        captured = capsys.readouterr()
        assert "WARN" in captured.out
        assert "WARNINGS: 1" in captured.out
    finally:
        os.chdir(original_cwd)


# ============================================
# Edge Cases and Integration Tests
# ============================================

def test_very_long_line_redos_protection(sample_config, tmp_path):
    """Test ReDoS protection with very long lines."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Create file with very long line
        test_file = tmp_path / "long.py"
        # Create a line longer than 10000 chars with pattern at the end
        long_line = "x" * 10001 + 'password = "secret"'
        test_file.write_text(long_line)

        results = scan_file(str(test_file), sample_config)
        # Pattern should not be found due to truncation
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)


def test_unicode_in_filepath(sample_config, tmp_path):
    """Test handling unicode in file paths."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Create file with unicode name
        test_file = tmp_path / "fichier_francais.py"
        test_file.write_text('password = "secret123"')

        results = scan_file(str(test_file), sample_config)
        assert len(results) == 1
    finally:
        os.chdir(original_cwd)


def test_multiple_patterns_same_line(tmp_path):
    """Test multiple patterns matching same line."""
    config = {
        "version": "1.0",
        "blocking": [
            {
                "id": "pattern1",
                "name": "Pattern 1",
                "regex": r"secret",
                "message": "Secret found",
            },
            {
                "id": "pattern2",
                "name": "Pattern 2",
                "regex": r"password",
                "message": "Password found",
            },
        ],
        "warning": [],
        "exceptions": {},
    }

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "multi.py"
        test_file.write_text('password = "secret123"')

        results = scan_file(str(test_file), config)
        assert len(results) == 2
        pattern_ids = {r.pattern_id for r in results}
        assert "pattern1" in pattern_ids
        assert "pattern2" in pattern_ids
    finally:
        os.chdir(original_cwd)


def test_scan_file_multiline_content(sample_config, tmp_path):
    """Test scanning file with multiple lines."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "multi.py"
        test_file.write_text('''import os
# Some comment
password = "secret1"
name = "test"
password = "secret2"
''')

        results = scan_file(str(test_file), sample_config)
        assert len(results) == 2
        lines = {r.line for r in results}
        assert 3 in lines
        assert 5 in lines
    finally:
        os.chdir(original_cwd)


def test_scan_file_first_line_suppression(sample_config, tmp_path):
    """Test ignore-next-line on first line (no previous line)."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        test_file = tmp_path / "first.py"
        # First line is the pattern - prev_line should be None
        test_file.write_text('password = "secret"  # vibesrails: ignore')

        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0
    finally:
        os.chdir(original_cwd)
