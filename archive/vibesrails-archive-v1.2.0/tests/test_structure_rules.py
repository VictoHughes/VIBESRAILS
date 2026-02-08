"""Tests for structure rule generation."""
import tempfile
from pathlib import Path

import yaml

from vibesrails.learner.pattern_detector import DetectedPattern
from vibesrails.learner.structure_rules import StructureRulesGenerator


def test_generator_creates_yaml_from_patterns():
    """Should generate YAML rules from detected patterns."""
    patterns = [
        DetectedPattern(
            category="test",
            location="tests/",
            confidence=0.95,
            examples=10
        ),
        DetectedPattern(
            category="service",
            location="backend/application/services/",
            confidence=0.85,
            examples=5
        )
    ]

    generator = StructureRulesGenerator()
    rules = generator.generate_rules(patterns)

    # Should have placement rules
    assert "placement" in rules
    assert len(rules["placement"]) == 2

    # Check test rule
    test_rule = next(r for r in rules["placement"] if r["category"] == "test")
    assert test_rule["expected_location"] == "tests/"
    assert test_rule["confidence"] == 0.95
    assert test_rule["enforcement"] == "suggest"  # High confidence but not enforced yet


def test_generator_sets_enforcement_based_on_confidence():
    """High confidence patterns should suggest enforcement."""
    patterns = [
        DetectedPattern(category="test", location="tests/", confidence=0.98, examples=20),
        DetectedPattern(category="service", location="src/services/", confidence=0.6, examples=3),
    ]

    generator = StructureRulesGenerator()
    rules = generator.generate_rules(patterns)

    # High confidence should be ready for enforcement
    test_rule = next(r for r in rules["placement"] if r["category"] == "test")
    assert test_rule["enforcement"] == "suggest"
    assert test_rule["ready_for_enforcement"] is True

    # Low confidence should stay observational
    service_rule = next(r for r in rules["placement"] if r["category"] == "service")
    assert service_rule["enforcement"] == "observe"
    assert service_rule["ready_for_enforcement"] is False


def test_generator_saves_to_yaml():
    """Should save rules to YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "learned_patterns.yaml"

        patterns = [
            DetectedPattern(category="test", location="tests/", confidence=0.9, examples=5)
        ]

        generator = StructureRulesGenerator()
        generator.save_rules(patterns, output_path)

        # File should exist and be valid YAML
        assert output_path.exists()

        with open(output_path) as f:
            saved_rules = yaml.safe_load(f)

        assert "placement" in saved_rules
        assert saved_rules["version"] == "1.3"
        assert "learned_at" in saved_rules
