# Senior Mode

Senior Mode transforms VibesRails into a teaching tool for AI-assisted development.

## Features

### 1. Architecture Mapper

Auto-generates `ARCHITECTURE.md` so Claude always knows where to put code.

```bash
vibesrails --senior
```

Output includes:
- Project structure tree
- Module analysis (classes, functions, line counts)
- Placement rules (where to put new code)
- Sensitive zones (files requiring careful review)

### 2. Guards

Five concrete checks for common vibe coding issues:

| Guard | Detects | Severity |
|-------|---------|----------|
| DiffSizeGuard | Large commits (>200 lines) | block/warn |
| ErrorHandlingGuard | Bare except, silent failures | warn |
| HallucinationGuard | Imports that don't exist | block |
| DependencyGuard | New dependencies added | warn |
| TestCoverageGuard | Code without tests | warn |

### 3. Claude Review (Targeted)

Only reviews sensitive changes:
- Auth/security files
- Complex control flow (>30 branches)
- Database/payment code

Returns structured feedback:
- Score (1-10)
- Issues found
- Strengths
- Suggestions

## Usage

```bash
# Run Senior Mode
vibesrails --senior

# Scan all files with Senior Mode
vibesrails --senior --all

# Scan specific file
vibesrails --senior -f myfile.py
```

## Example Output

```
============================================================
                  SENIOR MODE REPORT
============================================================

-- GUARDS -------------------------------------------------
  [WARN] [ErrorHandlingGuard] except: pass - silently swallows errors
         -> auth.py:15
  [WARN] [TestCoverageGuard] 45 lines of code added with no tests.

-- CLAUDE REVIEW ------------------------------------------
  Score: 7/10
  Issues:
    - Missing input validation on user parameter
  Strengths:
    + Clear function naming
  Suggestions:
    > Add rate limiting to login attempts

[OK] ARCHITECTURE.md updated

------------------------------------------------------------
Summary: 0 blocking | 2 warnings
```

## Configuration

Add to `vibesrails.yaml`:

```yaml
senior_mode:
  guards:
    diff_size:
      max_lines: 200
      warn_at: 100
    test_coverage:
      min_ratio: 0.3
```

## Integration with Guardian Mode

Senior Mode works automatically with Guardian Mode. When Guardian detects an AI coding session, it can trigger Senior Mode checks automatically.
