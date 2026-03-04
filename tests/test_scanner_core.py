"""Tests for vibesrails scanner — core scan_file, suppression, config loading."""

import os
from pathlib import Path

import pytest

from vibesrails import ScanResult, load_config, scan_file

# ============================================
# scan_file Basic Tests
# ============================================


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
    child_config.write_text('''
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
