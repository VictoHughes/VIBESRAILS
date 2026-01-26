"""Validates file placement against learned patterns."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Divergence:
    """Details about a placement divergence."""
    category: str
    expected_location: str
    actual_location: str
    confidence: float
    message: str


@dataclass
class PlacementResult:
    """Result of placement validation."""
    valid: bool
    divergence: Divergence | None = None


class PlacementGuard:
    """Validates file placement against learned patterns."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.patterns_file = cache_dir / "learned_patterns.yaml"
        self._patterns: dict[str, Any] | None = None

    def validate_placement(self, file_path: str) -> PlacementResult:
        """Validate if file is being placed in correct location."""
        patterns = self._load_patterns()

        if not patterns or "placement" not in patterns:
            # No patterns learned yet - pass
            return PlacementResult(valid=True)

        # Check each placement rule
        for rule in patterns["placement"]:
            if self._matches_pattern(file_path, rule["pattern"]):
                # Found matching pattern - validate location
                expected_loc = rule["expected_location"]
                actual_loc = self._extract_location(file_path)

                if not actual_loc.startswith(expected_loc.rstrip("/")):
                    # Divergence detected
                    divergence = Divergence(
                        category=rule["category"],
                        expected_location=expected_loc,
                        actual_location=actual_loc + "/",
                        confidence=rule["confidence"],
                        message=self._build_message(rule, file_path)
                    )
                    return PlacementResult(valid=False, divergence=divergence)

        return PlacementResult(valid=True)

    def _load_patterns(self) -> dict[str, Any] | None:
        """Load learned patterns from cache."""
        if self._patterns is not None:
            return self._patterns

        if not self.patterns_file.exists():
            return None

        with open(self.patterns_file) as f:
            self._patterns = yaml.safe_load(f)

        return self._patterns

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches pattern."""
        from fnmatch import fnmatch
        filename = Path(file_path).name
        return fnmatch(filename, pattern)

    def _extract_location(self, file_path: str) -> str:
        """Extract directory location from file path."""
        path = Path(file_path)
        if len(path.parts) > 1:
            return path.parts[0]
        return ""

    def _build_message(self, rule: dict, file_path: str) -> str:
        """Build user-friendly divergence message."""
        enforcement = rule.get("enforcement", "observe")

        if enforcement == "suggest":
            return (
                f"Pattern divergence: {rule['category']} files are usually in "
                f"{rule['expected_location']} ({rule['confidence']:.0%} confidence). "
                f"Suggest placing in correct location."
            )
        else:
            return (
                f"Observed: {rule['category']} files are usually in "
                f"{rule['expected_location']} ({rule['confidence']:.0%} confidence)"
            )
