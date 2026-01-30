"""Generate structure validation rules from detected patterns."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .pattern_detector import DetectedPattern

logger = logging.getLogger(__name__)


class StructureRulesGenerator:
    """Generates YAML rules from detected patterns."""

    # Confidence thresholds
    ENFORCEMENT_THRESHOLD = 0.9  # Ready to enforce
    OBSERVATION_THRESHOLD = 0.7  # Still observing

    def generate_rules(self, patterns: list[DetectedPattern]) -> dict[str, Any]:
        """Generate rule dictionary from patterns."""
        placement_rules = []

        for pattern in patterns:
            rule = {
                "category": pattern.category,
                "expected_location": pattern.location,
                "confidence": pattern.confidence,
                "examples": pattern.examples,
                "enforcement": self._determine_enforcement(pattern.confidence),
                "ready_for_enforcement": pattern.confidence >= self.ENFORCEMENT_THRESHOLD,
                "pattern": f"{pattern.category}_*.py" if pattern.category == "test" else f"*_{pattern.category}.py"
            }
            placement_rules.append(rule)

        return {
            "placement": placement_rules
        }

    def _determine_enforcement(self, confidence: float) -> str:
        """Determine enforcement level based on confidence."""
        if confidence >= self.ENFORCEMENT_THRESHOLD:
            return "suggest"  # Ready but not forced yet
        elif confidence >= self.OBSERVATION_THRESHOLD:
            return "observe"
        else:
            return "observe"

    def save_rules(self, patterns: list[DetectedPattern], output_path: Path) -> None:
        """Save generated rules to YAML file."""
        rules = self.generate_rules(patterns)

        # Add metadata
        full_config = {
            "version": "1.3",
            "learned_at": datetime.now().isoformat(),
            **rules
        }

        with open(output_path, "w") as f:
            yaml.dump(full_config, f, default_flow_style=False, sort_keys=False)
