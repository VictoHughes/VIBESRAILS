"""Tests for pattern detection."""
import tempfile
from pathlib import Path

from vibesrails.learner.pattern_detector import PatternDetector


def test_detector_finds_test_pattern():
    """Should detect that tests are in tests/ directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create sample structure
        (project / "tests").mkdir()
        (project / "tests" / "test_foo.py").touch()
        (project / "tests" / "test_bar.py").touch()
        (project / "src").mkdir()
        (project / "src" / "foo.py").touch()

        detector = PatternDetector(project)
        patterns = detector.detect()

        # Should find test pattern
        test_pattern = next((p for p in patterns if p.category == "test"), None)
        assert test_pattern is not None
        assert test_pattern.location == "tests/"
        assert test_pattern.confidence >= 0.9
        assert test_pattern.examples == 2


def test_detector_finds_service_pattern():
    """Should detect service organization pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create service structure
        services = project / "backend" / "application" / "services"
        services.mkdir(parents=True)
        (services / "user_service.py").touch()
        (services / "auth_service.py").touch()
        (services / "email_service.py").touch()

        detector = PatternDetector(project)
        patterns = detector.detect()

        # Should find service pattern
        service_pattern = next((p for p in patterns if p.category == "service"), None)
        assert service_pattern is not None
        assert "application/services" in service_pattern.location
        assert service_pattern.confidence >= 0.8


def test_detector_handles_empty_project():
    """Should return empty patterns for empty project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        detector = PatternDetector(project)
        patterns = detector.detect()

        assert patterns == []
