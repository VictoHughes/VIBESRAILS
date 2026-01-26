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

## License

MIT - Use it, fork it, improve it.

---

**Ship fast. Ship safe. 🚀**
