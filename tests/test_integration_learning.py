"""End-to-end integration tests for learning and validation."""
import json
import subprocess
import tempfile
from pathlib import Path

from vibesrails.integration_learning import (
    PatternDetector,  # noqa: F401  # ensures test imports source
)


def test_full_learning_and_validation_flow():
    """Test complete flow: learn → validate placement → validate duplication."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Step 1: Create project structure
        tests_dir = project / "tests"
        tests_dir.mkdir()
        for i in range(5):
            (tests_dir / f"test_{i}.py").write_text(f"def test_{i}(): pass")

        services_dir = project / "app" / "services"
        services_dir.mkdir(parents=True)
        for i in range(3):
            (services_dir / f"{i}_service.py").write_text(
                f"def process_{i}(): pass\ndef validate_{i}(): pass"
            )

        # Step 2: Run learn command
        result = subprocess.run(
            ["vibesrails", "learn"],
            cwd=project,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Detected patterns:" in result.stdout

        # Step 3: Verify learned patterns
        patterns_file = project / ".vibesrails" / "learned_patterns.yaml"
        assert patterns_file.exists()

        import yaml
        with open(patterns_file) as f:
            patterns = yaml.safe_load(f)

        assert "placement" in patterns
        test_rule = next(r for r in patterns["placement"] if r["category"] == "test")
        assert test_rule["expected_location"] == "tests/"
        assert test_rule["confidence"] >= 0.9

        # Step 4: Verify signature index
        index_file = project / ".vibesrails" / "signature_index.json"
        assert index_file.exists()

        with open(index_file) as f:
            signatures = json.load(f)

        # Should have indexed functions from services
        assert len(signatures) >= 6  # 3 process_ + 3 validate_
        validate_funcs = [s for s in signatures if "validate" in s["name"]]
        assert len(validate_funcs) == 3

        # Step 5: Test placement validation
        from vibesrails.guardian import PlacementGuard

        guard = PlacementGuard(project / ".vibesrails")

        # Correct placement should pass
        result = guard.validate_placement("tests/test_new.py")
        assert result.valid is True

        # Wrong placement should fail
        result = guard.validate_placement("src/test_new.py")
        assert result.valid is False
        assert result.divergence is not None
        assert "tests/" in result.divergence.expected_location

        # Step 6: Test duplication detection
        from vibesrails.guardian import DuplicationGuard

        dup_guard = DuplicationGuard(project / ".vibesrails")

        # Similar name should detect duplication
        result = dup_guard.check_duplication("validate_user", "dict -> bool")
        assert result.has_duplicates is True
        assert len(result.similar_signatures) >= 3  # validate_0, validate_1, validate_2

        # Unique name should be clear
        result = dup_guard.check_duplication("authenticate_user", "str -> bool")
        assert result.has_duplicates is False


def test_learning_updates_on_rerun():
    """Re-running learn should update patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Initial structure
        (project / "tests").mkdir()
        (project / "tests" / "test_a.py").touch()

        # First learn
        subprocess.run(["vibesrails", "learn"], cwd=project, capture_output=True)

        import yaml
        patterns_file = project / ".vibesrails" / "learned_patterns.yaml"
        with open(patterns_file) as f:
            patterns1 = yaml.safe_load(f)

        test_rule1 = next(r for r in patterns1["placement"] if r["category"] == "test")
        assert test_rule1["examples"] == 1

        # Add more tests
        (project / "tests" / "test_b.py").touch()
        (project / "tests" / "test_c.py").touch()

        # Re-learn
        subprocess.run(["vibesrails", "learn"], cwd=project, capture_output=True)

        with open(patterns_file) as f:
            patterns2 = yaml.safe_load(f)

        test_rule2 = next(r for r in patterns2["placement"] if r["category"] == "test")
        assert test_rule2["examples"] == 3  # Updated count
