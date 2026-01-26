# VibesRails 1.3 - Smart Learning & Duplication Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add autonomous pattern learning and smart duplication detection to VibesRails with interactive validation during PreToolUse hooks.

**Architecture:**
- `learner/` module scans project structure and learns patterns (test locations, service organization, etc.)
- `guardian/` module validates file placement and detects duplication before creation
- Interactive dialogue through PreToolUse hooks for divergence validation
- All learning stored in `.vibesrails/` cache for fast lookups

**Tech Stack:** Python 3.12+, Pytest, YAML, AST module (stdlib), existing VibesRails scanner

---

## Task 1: Pattern Detector - Learn Project Structure

**Goal:** Scan project and detect where tests, services, models, etc. are located

**Files:**
- Create: `vibesrails/learner/__init__.py`
- Create: `vibesrails/learner/pattern_detector.py`
- Create: `tests/test_pattern_detector.py`

**Step 1: Write the failing test**

Create `tests/test_pattern_detector.py`:

```python
"""Tests for pattern detection."""
import tempfile
from pathlib import Path
import pytest
from vibesrails.learner.pattern_detector import PatternDetector, DetectedPattern


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pattern_detector.py -v`
Expected: FAIL with "No module named 'vibesrails.learner'"

**Step 3: Create learner module structure**

Create `vibesrails/learner/__init__.py`:

```python
"""Pattern learning and structure detection."""

from .pattern_detector import PatternDetector, DetectedPattern

__all__ = ["PatternDetector", "DetectedPattern"]
```

**Step 4: Write minimal implementation**

Create `vibesrails/learner/pattern_detector.py`:

```python
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
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_pattern_detector.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/learner/ tests/test_pattern_detector.py
git commit -m "feat(learner): add pattern detector for project structure

- Detects test file patterns
- Detects service organization patterns
- Returns confidence scores based on consistency
- TDD: 3 tests covering detection and edge cases"
```

---

## Task 2: Signature Indexer - Build Function/Class Index

**Goal:** Create fast index of all functions/classes with their signatures for duplication detection

**Files:**
- Create: `vibesrails/learner/signature_index.py`
- Create: `tests/test_signature_index.py`

**Step 1: Write the failing test**

Create `tests/test_signature_index.py`:

```python
"""Tests for signature indexing."""
import tempfile
from pathlib import Path
import pytest
from vibesrails.learner.signature_index import SignatureIndexer, Signature


def test_indexer_finds_functions():
    """Should index function signatures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Create sample file with functions
        code_file = project / "utils.py"
        code_file.write_text('''
def validate_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email

def parse_config(path: str) -> dict:
    """Parse config file."""
    return {}
''')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Should find both functions
        assert len(index) == 2

        # Check validate_email signature
        validate_sig = next(s for s in index if s.name == "validate_email")
        assert validate_sig.file_path == "utils.py"
        assert validate_sig.line_number == 2
        assert "email" in validate_sig.parameters
        assert validate_sig.return_type == "bool"


def test_indexer_finds_classes():
    """Should index class signatures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        code_file = project / "models.py"
        code_file.write_text('''
class UserValidator:
    """Validates user data."""

    def validate(self, data: dict) -> bool:
        return True
''')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Should find class and method
        class_sig = next(s for s in index if s.name == "UserValidator")
        assert class_sig.signature_type == "class"

        method_sig = next(s for s in index if s.name == "validate")
        assert method_sig.signature_type == "method"
        assert method_sig.parent_class == "UserValidator"


def test_indexer_search_finds_similar():
    """Should find similar function names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        (project / "utils.py").write_text('def validate_email(email: str) -> bool: pass')
        (project / "validators.py").write_text('def email_validator(email: str) -> bool: pass')

        indexer = SignatureIndexer(project)
        index = indexer.build_index()

        # Search for similar names
        similar = indexer.find_similar("validate_email", index)

        assert len(similar) >= 1
        # Should find email_validator as similar
        assert any("email" in s.name.lower() for s in similar)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_signature_index.py -v`
Expected: FAIL with "No module named 'vibesrails.learner.signature_index'"

**Step 3: Write minimal implementation**

Create `vibesrails/learner/signature_index.py`:

```python
"""Function and class signature indexing."""
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class Signature:
    """A function or class signature."""
    name: str
    signature_type: Literal["function", "method", "class"]
    file_path: str  # Relative to project root
    line_number: int
    parameters: list[str]
    return_type: str | None = None
    parent_class: str | None = None  # For methods


class SignatureIndexer:
    """Builds index of all function/class signatures in project."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def build_index(self) -> list[Signature]:
        """Scan all Python files and extract signatures."""
        signatures = []

        for py_file in self.project_root.rglob("*.py"):
            try:
                signatures.extend(self._extract_signatures(py_file))
            except Exception:
                # Skip files with syntax errors
                continue

        return signatures

    def _extract_signatures(self, file_path: Path) -> list[Signature]:
        """Extract signatures from a single file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except Exception:
            return []

        signatures = []
        relative_path = str(file_path.relative_to(self.project_root))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function or method
                params = [arg.arg for arg in node.args.args]
                return_type = None
                if node.returns:
                    return_type = ast.unparse(node.returns)

                # Determine if method (inside class)
                parent_class = self._find_parent_class(tree, node)
                sig_type = "method" if parent_class else "function"

                signatures.append(Signature(
                    name=node.name,
                    signature_type=sig_type,
                    file_path=relative_path,
                    line_number=node.lineno,
                    parameters=params,
                    return_type=return_type,
                    parent_class=parent_class
                ))

            elif isinstance(node, ast.ClassDef):
                signatures.append(Signature(
                    name=node.name,
                    signature_type="class",
                    file_path=relative_path,
                    line_number=node.lineno,
                    parameters=[]
                ))

        return signatures

    def _find_parent_class(self, tree: ast.AST, func_node: ast.FunctionDef) -> str | None:
        """Find parent class of a function node."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if func_node in ast.walk(node):
                    return node.name
        return None

    def find_similar(self, query: str, index: list[Signature]) -> list[Signature]:
        """Find signatures with similar names."""
        query_lower = query.lower()
        similar = []

        for sig in index:
            sig_lower = sig.name.lower()

            # Exact match
            if sig_lower == query_lower:
                continue  # Skip exact matches

            # Contains similar words
            query_words = set(query_lower.replace("_", " ").split())
            sig_words = set(sig_lower.replace("_", " ").split())

            # If they share words, it's similar
            if query_words & sig_words:
                similar.append(sig)

        return similar
```

**Step 4: Update learner __init__.py**

Modify `vibesrails/learner/__init__.py`:

```python
"""Pattern learning and structure detection."""

from .pattern_detector import PatternDetector, DetectedPattern
from .signature_index import SignatureIndexer, Signature

__all__ = ["PatternDetector", "DetectedPattern", "SignatureIndexer", "Signature"]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_signature_index.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/learner/signature_index.py vibesrails/learner/__init__.py tests/test_signature_index.py
git commit -m "feat(learner): add signature indexer for duplication detection

- Extracts function/class signatures using AST
- Indexes name, parameters, return types, location
- Provides similarity search for duplicate detection
- TDD: 3 tests covering functions, classes, search"
```

---

## Task 3: Structure Rules - Generate Learned Patterns YAML

**Goal:** Convert detected patterns into YAML rules that can be validated

**Files:**
- Create: `vibesrails/learner/structure_rules.py`
- Create: `tests/test_structure_rules.py`

**Step 1: Write the failing test**

Create `tests/test_structure_rules.py`:

```python
"""Tests for structure rule generation."""
import tempfile
from pathlib import Path
import pytest
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_structure_rules.py -v`
Expected: FAIL with "No module named 'vibesrails.learner.structure_rules'"

**Step 3: Write minimal implementation**

Create `vibesrails/learner/structure_rules.py`:

```python
"""Generate structure validation rules from detected patterns."""
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .pattern_detector import DetectedPattern


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
                "pattern": f"*_{pattern.category}*.py" if pattern.category == "test" else f"*_{pattern.category}.py"
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
```

**Step 4: Update learner __init__.py**

Modify `vibesrails/learner/__init__.py`:

```python
"""Pattern learning and structure detection."""

from .pattern_detector import PatternDetector, DetectedPattern
from .signature_index import SignatureIndexer, Signature
from .structure_rules import StructureRulesGenerator

__all__ = [
    "PatternDetector",
    "DetectedPattern",
    "SignatureIndexer",
    "Signature",
    "StructureRulesGenerator",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_structure_rules.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/learner/structure_rules.py vibesrails/learner/__init__.py tests/test_structure_rules.py
git commit -m "feat(learner): add structure rules generator

- Converts detected patterns to YAML rules
- Sets enforcement level based on confidence
- Saves learned patterns for validation
- TDD: 3 tests covering generation, enforcement, persistence"
```

---

## Task 4: Placement Guard - Validate File Placement

**Goal:** Check if new file placement matches learned patterns

**Files:**
- Create: `vibesrails/guardian/__init__.py`
- Create: `vibesrails/guardian/placement_guard.py`
- Create: `tests/test_placement_guard.py`

**Step 1: Write the failing test**

Create `tests/test_placement_guard.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_placement_guard.py -v`
Expected: FAIL with "No module named 'vibesrails.guardian'"

**Step 3: Create guardian module**

Create `vibesrails/guardian/__init__.py`:

```python
"""File placement and duplication validation."""

from .placement_guard import PlacementGuard, PlacementResult

__all__ = ["PlacementGuard", "PlacementResult"]
```

**Step 4: Write minimal implementation**

Create `vibesrails/guardian/placement_guard.py`:

```python
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
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_placement_guard.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/guardian/ tests/test_placement_guard.py
git commit -m "feat(guardian): add placement validation guard

- Validates file placement against learned patterns
- Detects divergences with confidence scores
- Provides user-friendly messages
- TDD: 3 tests covering validation, divergence, edge cases"
```

---

## Task 5: Duplication Guard - Detect Similar Code

**Goal:** Search signature index for similar functions/classes before creation

**Files:**
- Create: `vibesrails/guardian/duplication_guard.py`
- Create: `tests/test_duplication_guard.py`

**Step 1: Write the failing test**

Create `tests/test_duplication_guard.py`:

```python
"""Tests for duplication detection."""
import tempfile
from pathlib import Path
import json
import pytest
from vibesrails.guardian.duplication_guard import DuplicationGuard, DuplicationResult
from vibesrails.learner.signature_index import Signature


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_duplication_guard.py -v`
Expected: FAIL with "No module named 'vibesrails.guardian.duplication_guard'"

**Step 3: Write minimal implementation**

Create `vibesrails/guardian/duplication_guard.py`:

```python
"""Detects code duplication by searching signature index."""
import json
from dataclasses import dataclass
from pathlib import Path

from vibesrails.learner.signature_index import Signature


@dataclass
class DuplicationResult:
    """Result of duplication check."""
    has_duplicates: bool
    similar_signatures: list[Signature]


class DuplicationGuard:
    """Detects potential code duplication."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.index_file = cache_dir / "signature_index.json"
        self._index: list[Signature] | None = None

    def check_duplication(self, function_name: str, signature: str) -> DuplicationResult:
        """Check if function/class already exists or similar code present."""
        index = self._load_index()

        if not index:
            return DuplicationResult(has_duplicates=False, similar_signatures=[])

        similar = []
        name_lower = function_name.lower()

        for sig in index:
            # Exact match
            if sig.name.lower() == name_lower:
                similar.append(sig)
                continue

            # Similar names (share words)
            sig_words = set(sig.name.lower().replace("_", " ").split())
            name_words = set(name_lower.replace("_", " ").split())

            if sig_words & name_words:  # Intersection
                similar.append(sig)

        return DuplicationResult(
            has_duplicates=len(similar) > 0,
            similar_signatures=similar
        )

    def _load_index(self) -> list[Signature] | None:
        """Load signature index from cache."""
        if self._index is not None:
            return self._index

        if not self.index_file.exists():
            return None

        with open(self.index_file) as f:
            data = json.load(f)

        # Convert dicts back to Signature objects
        self._index = [
            Signature(
                name=sig["name"],
                signature_type=sig["signature_type"],
                file_path=sig["file_path"],
                line_number=sig["line_number"],
                parameters=sig["parameters"],
                return_type=sig.get("return_type"),
                parent_class=sig.get("parent_class")
            )
            for sig in data
        ]

        return self._index
```

**Step 4: Update guardian __init__.py**

Modify `vibesrails/guardian/__init__.py`:

```python
"""File placement and duplication validation."""

from .placement_guard import PlacementGuard, PlacementResult
from .duplication_guard import DuplicationGuard, DuplicationResult

__all__ = [
    "PlacementGuard",
    "PlacementResult",
    "DuplicationGuard",
    "DuplicationResult",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_duplication_guard.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/guardian/duplication_guard.py vibesrails/guardian/__init__.py tests/test_duplication_guard.py
git commit -m "feat(guardian): add duplication detection guard

- Searches signature index for similar code
- Detects exact matches and similar names
- Fast lookup using pre-built index
- TDD: 3 tests covering exact, similar, unique cases"
```

---

## Task 6: Learn Command - Initial Project Scan

**Goal:** Add CLI command to scan project and learn patterns

**Files:**
- Modify: `vibesrails/cli.py`
- Create: `tests/test_learn_command.py`

**Step 1: Write the failing test**

Create `tests/test_learn_command.py`:

```python
"""Tests for learn command."""
import tempfile
from pathlib import Path
import subprocess
import pytest


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
        assert "backend/tests" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_learn_command.py -v`
Expected: FAIL (command doesn't exist yet)

**Step 3: Add learn command to CLI**

Modify `vibesrails/cli.py` (find the `main()` function and add):

```python
# Add at top of file
from vibesrails.learner import (
    PatternDetector,
    SignatureIndexer,
    StructureRulesGenerator,
)

# Inside main() function, add new command handling:

def handle_learn_command():
    """Learn project structure and create pattern rules."""
    print(f"{BLUE}🧠 Learning project structure...{NC}")

    # Find project root
    project_root = Path.cwd()
    cache_dir = project_root / ".vibesrails"
    cache_dir.mkdir(exist_ok=True)

    # Detect patterns
    print("  Detecting patterns...")
    detector = PatternDetector(project_root)
    patterns = detector.detect()

    if not patterns:
        print(f"{YELLOW}  No clear patterns detected yet.{NC}")
        return 0

    print(f"{GREEN}  Detected patterns:{NC}")
    for pattern in patterns:
        print(f"    - {pattern.category:12} → {pattern.location:30} "
              f"({pattern.confidence:.0%} confidence, {pattern.examples} examples)")

    # Generate rules
    print("\n  Generating structure rules...")
    generator = StructureRulesGenerator()
    patterns_file = cache_dir / "learned_patterns.yaml"
    generator.save_rules(patterns, patterns_file)
    print(f"{GREEN}  ✓ Rules saved to .vibesrails/learned_patterns.yaml{NC}")

    # Build signature index
    print("\n  Building signature index...")
    indexer = SignatureIndexer(project_root)
    signatures = indexer.build_index()

    # Save index to JSON
    import json
    index_file = cache_dir / "signature_index.json"
    index_data = [
        {
            "name": sig.name,
            "signature_type": sig.signature_type,
            "file_path": sig.file_path,
            "line_number": sig.line_number,
            "parameters": sig.parameters,
            "return_type": sig.return_type,
            "parent_class": sig.parent_class,
        }
        for sig in signatures
    ]
    with open(index_file, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"{GREEN}  ✓ Indexed {len(signatures)} signatures{NC}")
    print(f"\n{GREEN}✓ Learning complete!{NC}")
    print(f"  Patterns and signatures cached in .vibesrails/")

    return 0

# Add to argument parser
if len(sys.argv) > 1 and sys.argv[1] == "learn":
    return handle_learn_command()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_learn_command.py -v`
Expected: 2 PASSED

**Step 5: Test manually**

```bash
cd ~/Dev/vibesrails
vibesrails learn
```

Expected output:
```
🧠 Learning project structure...
  Detecting patterns...
  Detected patterns:
    - test         → tests/                           (100% confidence, 10 examples)

  Generating structure rules...
  ✓ Rules saved to .vibesrails/learned_patterns.yaml

  Building signature index...
  ✓ Indexed 150 signatures

✓ Learning complete!
  Patterns and signatures cached in .vibesrails/
```

**Step 6: Commit**

```bash
git add vibesrails/cli.py tests/test_learn_command.py
git commit -m "feat(cli): add learn command for project scanning

- New 'vibesrails learn' command
- Detects patterns and builds signature index
- Saves to .vibesrails/ cache
- TDD: 2 tests covering cache creation, pattern detection"
```

---

## Task 7: Interactive Dialogue - PreToolUse Hook Integration

**Goal:** Add interactive dialogue when divergences detected in hooks

**Files:**
- Create: `vibesrails/guardian/dialogue.py`
- Create: `tests/test_dialogue.py`

**Step 1: Write the failing test**

Create `tests/test_dialogue.py`:

```python
"""Tests for interactive dialogue."""
import pytest
from unittest.mock import patch, MagicMock
from vibesrails.guardian.dialogue import InteractiveDialogue
from vibesrails.guardian.placement_guard import Divergence
from vibesrails.learner.signature_index import Signature


def test_dialogue_presents_placement_options():
    """Should present options when placement divergence detected."""
    divergence = Divergence(
        category="test",
        expected_location="tests/",
        actual_location="src/",
        confidence=0.95,
        message="Tests should be in tests/"
    )

    dialogue = InteractiveDialogue()
    prompt = dialogue.format_placement_prompt("src/test_foo.py", divergence)

    assert "tests/" in prompt
    assert "src/" in prompt
    assert "0.95" in prompt or "95%" in prompt
    assert "1)" in prompt  # Option 1
    assert "2)" in prompt  # Option 2


def test_dialogue_presents_duplication_options():
    """Should present options when similar code detected."""
    similar = [
        Signature(
            name="validate_email",
            signature_type="function",
            file_path="utils/validators.py",
            line_number=10,
            parameters=["email"],
            return_type="bool"
        ),
        Signature(
            name="email_validator",
            signature_type="function",
            file_path="domain/validation/email.py",
            line_number=25,
            parameters=["email_str"],
            return_type="bool"
        )
    ]

    dialogue = InteractiveDialogue()
    prompt = dialogue.format_duplication_prompt("check_email_format", similar)

    assert "validate_email" in prompt
    assert "email_validator" in prompt
    assert "utils/validators.py:10" in prompt
    assert "domain/validation/email.py:25" in prompt


def test_dialogue_records_decision():
    """Should record user decisions to observations log."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".vibesrails"
        cache_dir.mkdir()

        dialogue = InteractiveDialogue(cache_dir)
        dialogue.record_decision(
            file_path="src/test_foo.py",
            decision_type="placement_divergence",
            user_choice="create_here",
            metadata={"expected": "tests/", "actual": "src/"}
        )

        # Should create observations log
        log_file = cache_dir / "observations.jsonl"
        assert log_file.exists()

        # Should contain decision
        content = log_file.read_text()
        assert "placement_divergence" in content
        assert "create_here" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_dialogue.py -v`
Expected: FAIL with "No module named 'vibesrails.guardian.dialogue'"

**Step 3: Write minimal implementation**

Create `vibesrails/guardian/dialogue.py`:

```python
"""Interactive dialogue for validation decisions."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .placement_guard import Divergence
from vibesrails.learner.signature_index import Signature


class InteractiveDialogue:
    """Handles interactive validation prompts."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(".vibesrails")
        self.observations_file = self.cache_dir / "observations.jsonl"

    def format_placement_prompt(self, file_path: str, divergence: Divergence) -> str:
        """Format prompt for placement divergence."""
        prompt = f"""
🤔 Pattern Divergence Detected

File: {file_path}
Expected: {divergence.expected_location}
Actual: {divergence.actual_location}
Confidence: {divergence.confidence:.0%} ({divergence.message})

Options:
  1) Use expected location (create in {divergence.expected_location})
  2) Create here (new pattern - will learn this)
  3) Ignore this time (don't learn)

Choice:"""
        return prompt.strip()

    def format_duplication_prompt(self, function_name: str, similar: list[Signature]) -> str:
        """Format prompt for duplication detection."""
        similar_list = "\n".join([
            f"  • {sig.name} ({sig.signature_type}) in {sig.file_path}:{sig.line_number}"
            for sig in similar
        ])

        prompt = f"""
💡 Similar Code Detected

Creating: {function_name}
Found similar:
{similar_list}

Options:
  1) Use existing (recommended)
  2) Create anyway (different purpose)
  3) Refactor to centralize

Choice:"""
        return prompt.strip()

    def record_decision(
        self,
        file_path: str,
        decision_type: str,
        user_choice: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Record user decision to observations log."""
        observation = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "decision_type": decision_type,
            "user_choice": user_choice,
            "metadata": metadata or {}
        }

        # Append to JSONL file
        self.cache_dir.mkdir(exist_ok=True)
        with open(self.observations_file, "a") as f:
            f.write(json.dumps(observation) + "\n")
```

**Step 4: Update guardian __init__.py**

Modify `vibesrails/guardian/__init__.py`:

```python
"""File placement and duplication validation."""

from .placement_guard import PlacementGuard, PlacementResult
from .duplication_guard import DuplicationGuard, DuplicationResult
from .dialogue import InteractiveDialogue

__all__ = [
    "PlacementGuard",
    "PlacementResult",
    "DuplicationGuard",
    "DuplicationResult",
    "InteractiveDialogue",
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_dialogue.py -v`
Expected: 3 PASSED

**Step 6: Commit**

```bash
git add vibesrails/guardian/dialogue.py vibesrails/guardian/__init__.py tests/test_dialogue.py
git commit -m "feat(guardian): add interactive dialogue for decisions

- Formats prompts for placement divergence
- Formats prompts for duplication detection
- Records user decisions to observations log
- TDD: 3 tests covering formatting, recording"
```

---

## Task 8: Version Bump and Documentation

**Goal:** Update version to 1.3.0 and document new features

**Files:**
- Modify: `vibesrails/__init__.py`
- Modify: `pyproject.toml`
- Create: `RELEASE_NOTES_1.3.0.md`

**Step 1: Update version**

Modify `vibesrails/__init__.py`:

```python
__version__ = "1.3.0"
```

Modify `pyproject.toml`:

```toml
[project]
name = "vibesrails"
version = "1.3.0"
```

**Step 2: Create release notes**

Create `RELEASE_NOTES_1.3.0.md`:

```markdown
# VibesRails 1.3.0 - Smart Learning & Duplication Detection

Release Date: 2026-01-26

## 🎯 Overview

VibesRails 1.3.0 adds autonomous pattern learning and smart duplication detection. The system learns your project structure and validates file placement + code duplication in real-time during development.

## ✨ New Features

### Pattern Learning
- **Auto-detection**: Scans project to learn where tests, services, models are located
- **Confidence scoring**: Patterns have confidence scores based on consistency
- **New command**: `vibesrails learn` to scan and learn project structure
- **Cached learning**: Stores patterns in `.vibesrails/learned_patterns.yaml`

### Smart Validation
- **Placement validation**: Checks if new files match learned patterns
- **Divergence detection**: Alerts when file placement differs from norms
- **Interactive dialogue**: Ask user before enforcing (not dictatorial)

### Duplication Detection
- **Signature indexing**: Fast index of all functions/classes in project
- **Similar code search**: Finds functions with similar names/purposes
- **Pre-creation check**: Validates before file is created (not after)

## 🏗️ Architecture

```
vibesrails/
├── learner/
│   ├── pattern_detector.py    # Learns project structure
│   ├── signature_index.py     # Indexes functions/classes
│   └── structure_rules.py     # Generates validation rules
└── guardian/
    ├── placement_guard.py     # Validates file placement
    ├── duplication_guard.py   # Detects similar code
    └── dialogue.py            # Interactive prompts
```

## 📦 Installation

```bash
pip install vibesrails==1.3.0
```

## 🚀 Usage

### Initial Learning

```bash
# Scan project and learn patterns
vibesrails learn
```

Output:
```
🧠 Learning project structure...
  Detected patterns:
    - test         → tests/                 (95% confidence, 12 examples)
    - service      → app/services/          (90% confidence, 8 examples)

  ✓ Rules saved to .vibesrails/learned_patterns.yaml
  ✓ Indexed 247 signatures
```

### Automatic Validation

Once learned, VibesRails validates automatically via hooks:

```python
# Claude tries to create: src/test_foo.py

🤔 Pattern Divergence Detected
Expected: tests/
Actual: src/
Confidence: 95%

Options:
  1) Use expected location (tests/)
  2) Create here (new pattern)
  3) Ignore this time
```

## 🔄 Migration from 1.2.0

No breaking changes. Learning is opt-in:

```bash
# Add to your workflow
vibesrails learn

# Keep using existing commands
vibesrails --all
vibesrails --staged
```

## 📊 Performance

- Pattern detection: ~2-5s for medium projects (1000 files)
- Signature indexing: ~5-10s for medium projects
- Validation lookup: <100ms (cached)

## 🐛 Bug Fixes

None - new feature release.

## 🙏 Credits

Developed with systematic TDD approach using superpowers workflow.

## 📝 Changelog

### Added
- `vibesrails learn` command for project scanning
- Pattern detection for tests, services, models, etc.
- Signature indexing for duplication detection
- Placement validation guard
- Duplication detection guard
- Interactive dialogue for user decisions
- Observations log for learning from decisions

### Changed
- Version bumped to 1.3.0

### Deprecated
None

### Removed
None

### Fixed
None

### Security
None
```

**Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS

**Step 4: Build package**

```bash
python -m build --wheel
```

Expected: `dist/vibesrails-1.3.0-py3-none-any.whl` created

**Step 5: Commit**

```bash
git add vibesrails/__init__.py pyproject.toml RELEASE_NOTES_1.3.0.md
git commit -m "chore: bump version to 1.3.0 and add release notes

- Update version in __init__.py and pyproject.toml
- Comprehensive release notes documenting new features
- Pattern learning, duplication detection, interactive validation
- Ready for release"
```

---

## Task 9: Integration Test - End-to-End Flow

**Goal:** Test complete flow from learning to validation

**Files:**
- Create: `tests/test_integration_learning.py`

**Step 1: Write integration test**

Create `tests/test_integration_learning.py`:

```python
"""End-to-end integration tests for learning and validation."""
import tempfile
from pathlib import Path
import subprocess
import json
import pytest


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
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_integration_learning.py -v`
Expected: 2 PASSED

**Step 3: Commit**

```bash
git add tests/test_integration_learning.py
git commit -m "test: add end-to-end integration tests

- Tests complete learning and validation flow
- Verifies learn → validate placement → validate duplication
- Tests pattern updates on re-run
- 2 comprehensive integration tests"
```

---

## Final Verification

**Run all tests:**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

**Run on real project:**

```bash
cd ~/Dev/BYO
vibesrails learn
```

Expected output showing detected patterns and signatures.

**Manual validation:**

1. Try creating a test file in wrong location
2. Verify hook would detect divergence
3. Check `.vibesrails/` cache created correctly

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-01-26-vibesrails-1.3-smart-learning.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
