# Project Security Configuration

This project uses **VibesRails** for automatic security scanning.

## What is VibesRails?

VibesRails is a security scanner that runs automatically on every commit to catch common security issues before they reach production.

**Key Features:**
- 🔒 Detects hardcoded secrets, SQL injection, command injection
- ⚠️ Warns about code quality issues (star imports, bare excepts, TODOs)
- 🎯 YAML-driven configuration (`vibesrails.yaml`)
- 🚀 Memory-safe streaming (handles files of any size)
- 🤖 AI-powered pattern discovery (`vibesrails --learn`)
- 🔧 Auto-fix capability (`vibesrails --fix`)

## How It Works

```
You code → git commit → vibesrails scans → Safe code ships
                              ↓
                     Issue found? Quick fix, continue.
```

**Pre-commit hook:** Automatically scans staged files before each commit.

**Claude Code integration:** Hooks inform you about active plans and task status.

## Configuration

All security patterns are defined in **`vibesrails.yaml`** (single source of truth).

### Pattern Types

**Blocking patterns** (🔒) - Prevent commits:
- Hardcoded secrets (API keys, passwords)
- SQL injection risks
- Command injection risks
- Debug mode in production files

**Warning patterns** (⚠️) - Show warnings:
- Star imports (except in config files)
- Print statements (use logging instead)
- Bare except clauses
- TODO comments

### Exceptions

Test files (`test_*.py`) can use patterns that would normally be blocked:
- Hardcoded secrets (for mocking)
- SQL injection patterns (for testing)
- Command injection patterns (for testing)

## Commands

```bash
# Scan staged files (pre-commit workflow)
vibesrails

# Scan entire project
vibesrails --all

# View configured patterns
vibesrails --show

# AI-powered pattern discovery
vibesrails --learn

# Auto-fix simple issues
vibesrails --fix --dry-run  # Preview first
vibesrails --fix            # Apply fixes

# Live scanning on file save
vibesrails --watch

# View scan statistics
vibesrails --stats
```

## Bypassing Scans

**Only when necessary:**

```bash
# Bypass pre-commit hook (use sparingly!)
git commit --no-verify
```

## Customizing Patterns

Edit `vibesrails.yaml` to:
- Add custom security patterns
- Adjust warning thresholds
- Add file/pattern exceptions
- Scope patterns to specific files

**Example: Add custom pattern**

```yaml
blocking:
  - id: custom_pattern
    name: "Custom Security Check"
    regex: "your_regex_here"
    message: "Helpful message for developers"
    scope: ["specific/path/*.py"]  # Optional
```

**Validate changes:**

```bash
vibesrails --validate
```

## For Claude Code Users

**Hooks are configured in `.claude/hooks.json`:**

- **SessionStart** - Shows active plan and current task
- **PreCompact** - Auto-saves task state before context compaction
- **PostToolUse** - Detects new commits and reminds about security scanning

## Troubleshooting

**Scan failing?**

```bash
# Check what patterns are blocking
vibesrails --all

# Validate configuration
vibesrails --validate

# See detailed patterns
vibesrails --show
```

**False positive?**

Add an exception in `vibesrails.yaml`:

```yaml
exceptions:
  my_special_case:
    patterns: ["path/to/file.py"]
    allowed: ["pattern_id"]
    reason: "Explanation why this is safe"
```

## Support

- **Documentation**: https://github.com/VictoHughes/VIBESRAILS
- **Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Support**: https://buymeacoffee.com/vibesrails

---

**Ship fast. Ship safe. 🚀**
