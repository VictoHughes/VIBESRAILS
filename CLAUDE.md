# VibesRails - Development Guidelines

> From KIONOS™ (free tools) - Developed by SM

## Project Overview

VibesRails is a YAML-driven security scanner for Python projects. It helps developers catch secrets, security issues, and code quality problems before they reach production.

## Development Rules

### 1. Testing (MANDATORY)

**Minimum coverage: 80%**

```bash
# Run tests with coverage
pytest tests/ --cov=vibesrails --cov-report=term-missing

# Check coverage before commit
pytest tests/ --cov=vibesrails --cov-fail-under=80
```

**Test file naming:**
- `tests/test_<module>.py` for each module
- Test function: `test_<function>_<scenario>`

**Test structure:**
```python
def test_function_happy_path():
    """Test normal operation."""
    ...

def test_function_edge_case():
    """Test boundary conditions."""
    ...

def test_function_error_handling():
    """Test error cases."""
    ...
```

### 2. Code Quality

**Run before commit:**
```bash
# Lint
ruff check vibesrails/ --fix

# Security
bandit -r vibesrails/ -ll

# Self-scan
vibesrails --all
```

### 3. Architecture

**Module dependencies (enforced by import-linter):**
```
scanner.py    → (no dependencies on cli, smart_setup)
config.py     → (no dependencies on cli)
guardian.py   → scanner only
cli.py        → can import all
smart_setup.py → can import all
```

### 4. Commit Standards

**Pre-commit checklist:**
1. [ ] Tests pass: `pytest tests/`
2. [ ] Coverage ≥80%: `pytest --cov-fail-under=80`
3. [ ] Lint clean: `ruff check vibesrails/`
4. [ ] Security clean: `vibesrails --all`
5. [ ] No secrets in code

**Commit message format:**
```
type(scope): description

Co-Authored-By: ...
```

Types: feat, fix, refactor, test, docs, chore, style

### 5. File Structure

```
vibesrails/
├── __init__.py      # Version, public API
├── scanner.py       # Core scanning logic
├── config.py        # Config loading/validation
├── guardian.py      # AI safety features
├── cli.py           # Command-line interface
├── smart_setup.py   # Project setup wizard
├── autofix.py       # Auto-correction
├── watch.py         # File watcher
└── learn.py         # Pattern discovery
```

## Commands

```bash
vibesrails --all        # Scan entire project
vibesrails --show       # Show patterns
vibesrails --setup      # Setup new project
vibesrails --version    # Show version
```

## A.B.H.A.M.H
