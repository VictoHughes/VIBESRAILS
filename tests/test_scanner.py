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
