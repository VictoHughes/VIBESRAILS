"""Tests for placement validation."""
import tempfile
from pathlib import Path
import pytest
from vibesrails.guardian.placement_guard import PlacementGuard, PlacementResult


def test_guard_validates_correct_placement():
    """Should pass when file is in correct location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        # Create learned patterns
        patterns_file = cache_dir / "learned_patterns.yaml"
        patterns_file.write_text('''
version: "1.3"
placement:
  - category: test
    expected_location: tests/
    confidence: 0.95
    enforcement: suggest
    pattern: test_*.py
''')

        guard = PlacementGuard(cache_dir)
        result = guard.validate_placement("tests/test_foo.py")

        assert result.valid is True
        assert result.divergence is None


def test_guard_detects_divergence():
    """Should detect when file is in wrong location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        patterns_file = cache_dir / "learned_patterns.yaml"
        patterns_file.write_text('''
version: "1.3"
placement:
  - category: test
    expected_location: tests/
    confidence: 0.95
    enforcement: suggest
    pattern: test_*.py
''')

        guard = PlacementGuard(cache_dir)
        result = guard.validate_placement("src/test_foo.py")

        assert result.valid is False
        assert result.divergence is not None
        assert result.divergence.category == "test"
        assert result.divergence.expected_location == "tests/"
        assert result.divergence.actual_location == "src/"
        assert "suggest" in result.divergence.message.lower()


def test_guard_handles_no_learned_patterns():
    """Should pass validation if no patterns learned yet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        guard = PlacementGuard(cache_dir)
        result = guard.validate_placement("anywhere/test_foo.py")

        # No patterns = no validation = pass
        assert result.valid is True
        assert result.divergence is None
