# vibesrails 🛤️

<a href="https://buymeacoffee.com/vibesrails" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40">
</a>

**Scale up your vibe coding - safely.**

Code fast, ship faster. vibesrails catches security issues automatically so you can focus on building.

## Philosophy

Vibe coding = flow state, rapid iteration, creative momentum.

vibesrails **protects your flow** by:
- Catching issues at commit (not in production)
- Zero config to start
- Single YAML to customize
- Works with Claude Code

**You code. vibesrails watches your back.**

## Quick Start

```bash
# Install from GitHub
pip install git+https://github.com/VictoHughes/VIBESRAILS.git

# Initialize in your project
cd your-project
vibesrails --init
vibesrails --hook

# Code freely - vibesrails runs on every commit
```

## Usage

```bash
vibesrails              # Scan staged files (default)
vibesrails --all        # Scan entire project
vibesrails --show       # See what's configured
vibesrails --init       # Start fresh config
vibesrails --hook       # Install git automation
```

## How It Works

```
You code fast → git commit → vibesrails scans → Safe code ships
                                  ↓
                         Issue found? Quick fix, continue.
```

## Configuration

One file: `vibesrails.yaml`

```yaml
version: "1.0"

blocking:
  - id: hardcoded_secret
    name: "Hardcoded Secret"
    regex: "(password|api_key)\\s*=\\s*[\"'][^\"']{4,}"
    flags: "i"
    message: "Move to environment variables"

warning:
  - id: star_import
    name: "Star Import"
    regex: "from\\s+\\S+\\s+import\\s+\\*"
    message: "Consider explicit imports"
    skip_in_tests: true

exceptions:
  test_files:
    patterns: ["test_*.py"]
    allowed: ["hardcoded_secret"]
    reason: "Tests can mock secrets"
```

## Pattern Reference

| Field | Description |
|-------|-------------|
| `id` | Unique key |
| `name` | Display name |
| `regex` | Python regex |
| `message` | Helpful message |
| `flags` | `"i"` = case insensitive |
| `skip_in_tests` | Ignore in test files |

## Claude Code Integration

Drop the skill in your project:

```
skills/vibesrails/SKILL.md
```

Claude will:
1. Check patterns before writing code
2. Respect your exceptions
3. Keep you informed

## Architecture

```
vibesrails.yaml   ← Single source of truth
       │
       ├── Scanner reads YAML
       ├── Skill references YAML
       └── Git hook runs scanner
```

Update one file. Everything stays in sync.

## Why "vibesrails"?

- **Vibe** = coding in flow, fast iteration
- **Rails** = safety guardrails that keep you on track

Not restrictions. **Freedom with protection.**

## Support

VibesRails is free and open source. If it helps you ship safer code, consider supporting:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://buymeacoffee.com/vibesrails)

⭐ **Star this repo** - it helps others discover vibesrails

## Protect vibesrails from AI bypass

AI coding tools (Claude Code, Copilot, etc.) can modify or disable local security tools. vibesrails includes a **self-protection hook** that prevents AI from:

- Deleting or modifying the pre-commit hook
- Changing `vibesrails.yaml` config
- Altering CI workflows
- Using `--no-verify` to skip checks
- Uninstalling vibesrails

### Setup (one time, applies to all Claude Code sessions)

```bash
# 1. Copy the protection hook
mkdir -p ~/.claude/hooks
cp installers/claude-code/hooks/ptuh.py ~/.claude/hooks/ptuh.py

# 2. Add to Claude Code settings (~/.claude/settings.json)
# Add this inside the top-level object:
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "command": "python3 ~/.claude/hooks/ptuh.py"
      }
    ]
  }
}
```

### Why this matters

Without this protection, an AI tool can:
1. Remove the pre-commit hook (`rm .git/hooks/pre-commit`)
2. Use `git commit --no-verify` to skip all checks
3. Modify the config to disable guards
4. Edit CI workflows to remove checks

The protection hook runs **before** any file modification — the AI cannot disable it because the hook blocks modifications to itself.

**For full protection, also enable:**
- GitHub Actions CI (included in `.github/workflows/ci.yml`)
- Branch protection rules (Settings > Branches on GitHub)
- CODEOWNERS file (requires review for security files)

## License

MIT - Use it, fork it, improve it.

---

**Ship fast. Ship safe.**
