"""Tests for vibesrails scanner."""

import tempfile
from pathlib import Path

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


def test_scan_file_detects_blocking_pattern(sample_config, tmp_path):
    """Test that blocking patterns are detected."""
    test_file = tmp_path / "bad.py"
    test_file.write_text('password = "secret123"')

    # Change to tmp_path to make file path safe
    import os
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

    import os
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

    import os
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

    import os
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

    import os
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

    import os
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

    import os
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        results = scan_file(str(test_file), sample_config)
        assert len(results) == 0  # Should be suppressed
    finally:
        os.chdir(original_cwd)
