"""Detects patterns in project structure."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class DetectedPattern:
    """A detected pattern in the project structure."""
    category: Literal["test", "service", "model", "controller", "util", "config"]
    location: str  # Relative path pattern
    confidence: float  # 0.0 to 1.0
    examples: int  # Number of files following this pattern


class PatternDetector:
    """Detects structural patterns in a project."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def detect(self) -> list[DetectedPattern]:
        """Scan project and detect patterns."""
        patterns = []

        # Detect test pattern
        test_pattern = self._detect_test_pattern()
        if test_pattern:
            patterns.append(test_pattern)

        # Detect service pattern
        service_pattern = self._detect_service_pattern()
        if service_pattern:
            patterns.append(service_pattern)

        return patterns

    def _detect_test_pattern(self) -> DetectedPattern | None:
        """Find where test files are located."""
        test_files = list(self.project_root.rglob("test_*.py"))

        if not test_files:
            return None

        # Find common parent directory
        common_dirs = {}
        for test_file in test_files:
            # Get first directory after project root
            try:
                relative = test_file.relative_to(self.project_root)
                first_dir = relative.parts[0] if relative.parts else None
                if first_dir:
                    common_dirs[first_dir] = common_dirs.get(first_dir, 0) + 1
            except ValueError:
                continue

        if not common_dirs:
            return None

        # Most common directory
        location = max(common_dirs, key=common_dirs.get)
        count = common_dirs[location]

        # Confidence based on percentage of tests in this location
        confidence = count / len(test_files)

        return DetectedPattern(
            category="test",
            location=f"{location}/",
            confidence=confidence,
            examples=count
        )

    def _detect_service_pattern(self) -> DetectedPattern | None:
        """Find where service files are located."""
        service_files = list(self.project_root.rglob("*_service.py"))

        if len(service_files) < 2:  # Need at least 2 for pattern
            return None

        # Find common parent path
        common_path_parts = {}
        for service_file in service_files:
            try:
                relative = service_file.relative_to(self.project_root)
                # Get full path except filename
                path_parts = relative.parts[:-1]
                if path_parts:
                    path_key = "/".join(path_parts)
                    common_path_parts[path_key] = common_path_parts.get(path_key, 0) + 1
            except ValueError:
                continue

        if not common_path_parts:
            return None

        # Most common path
        location = max(common_path_parts, key=common_path_parts.get)
        count = common_path_parts[location]

        confidence = count / len(service_files)

        return DetectedPattern(
            category="service",
            location=location + "/",
            confidence=confidence,
            examples=count
        )
