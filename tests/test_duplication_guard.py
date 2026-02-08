"""Tests for duplication detection."""
import json
import tempfile
from pathlib import Path

from vibesrails.guardian.duplication_guard import DuplicationGuard


def test_guard_detects_exact_duplicate():
    """Should detect exact duplicate function name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        # Create signature index
        index_file = cache_dir / "signature_index.json"
        signatures = [
            {
                "name": "validate_email",
                "signature_type": "function",
                "file_path": "utils/validators.py",
                "line_number": 10,
                "parameters": ["email"],
                "return_type": "bool"
            }
        ]
        index_file.write_text(json.dumps(signatures))

        guard = DuplicationGuard(cache_dir)
        result = guard.check_duplication("validate_email", "str -> bool")

        assert result.has_duplicates is True
        assert len(result.similar_signatures) == 1
        assert result.similar_signatures[0].name == "validate_email"


def test_guard_detects_similar_functions():
    """Should detect similar function names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        index_file = cache_dir / "signature_index.json"
        signatures = [
            {
                "name": "validate_email",
                "signature_type": "function",
                "file_path": "domain/validation/email.py",
                "line_number": 20,
                "parameters": ["email"],
                "return_type": "bool"
            },
            {
                "name": "email_validator",
                "signature_type": "function",
                "file_path": "utils/validators.py",
                "line_number": 50,
                "parameters": ["email_str"],
                "return_type": "bool"
            }
        ]
        index_file.write_text(json.dumps(signatures))

        guard = DuplicationGuard(cache_dir)
        result = guard.check_duplication("check_email", "str -> bool")

        # Should find both as similar (share "email" word)
        assert result.has_duplicates is True
        assert len(result.similar_signatures) == 2


def test_guard_returns_empty_for_unique():
    """Should return empty result for unique function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        index_file = cache_dir / "signature_index.json"
        signatures = [
            {
                "name": "parse_config",
                "signature_type": "function",
                "file_path": "config/loader.py",
                "line_number": 5,
                "parameters": ["path"],
                "return_type": "dict"
            }
        ]
        index_file.write_text(json.dumps(signatures))

        guard = DuplicationGuard(cache_dir)
        result = guard.check_duplication("validate_email", "str -> bool")

        assert result.has_duplicates is False
        assert len(result.similar_signatures) == 0
