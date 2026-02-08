"""Tests for learn command."""
import subprocess
import tempfile
from pathlib import Path

from vibesrails.learn_command import run_learn_mode  # noqa: F401


def test_learn_command_creates_cache():
    """Learn command should create .vibesrails cache with learned patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create sample project structure
        tests_dir = project / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_foo.py").touch()
        (tests_dir / "test_bar.py").touch()

        # Run learn command
        result = subprocess.run(
            ["vibesrails", "learn"],
            cwd=project,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        # Should create cache
        cache_dir = project / ".vibesrails"
        assert cache_dir.exists()
        assert (cache_dir / "learned_patterns.yaml").exists()
        assert (cache_dir / "signature_index.json").exists()


def test_learn_command_detects_patterns():
    """Learn command should detect and report patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create clear pattern
        tests_dir = project / "backend" / "tests"
        tests_dir.mkdir(parents=True)
        for i in range(5):
            (tests_dir / f"test_{i}.py").touch()

        result = subprocess.run(
            ["vibesrails", "learn"],
            cwd=project,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "Detected patterns:" in result.stdout
        assert "test" in result.stdout.lower()
        assert "backend" in result.stdout
