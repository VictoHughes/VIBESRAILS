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
