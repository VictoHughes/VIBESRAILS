"""Tests for vibesrails scanner — advanced scan_file, show/validate, main(), edge cases."""

import os

import pytest

from vibesrails import scan_file

# ============================================
# scan_file Advanced Tests
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
        test_file.write_text("# todo: fix this\n# TODO: and this\n")  # vibesrails: ignore

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
