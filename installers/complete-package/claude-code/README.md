# VibesRails Templates - Drag & Drop Installation

**Quick setup for Claude Code users** - No scripts, no commands, just copy files!

## What's Inside

```
claude-code/
├── vibesrails.yaml      # Security patterns config
├── CLAUDE.md            # Claude Code instructions
└── .claude/
    └── hooks.json       # Automation hooks
```

## Installation (3 Easy Steps)

### Step 1: Install VibesRails

```bash
pip install vibesrails
```

**Verify:**
```bash
vibesrails --version
```

### Step 2: Copy Files to Your Project

**Option A: Drag & Drop in Claude Code**
1. Open your project in Claude Code
2. Drag these files into the Claude Code window:
   - `vibesrails.yaml` → Root of project
   - `CLAUDE.md` → Root of project
   - `.claude/hooks.json` → `.claude/` folder (create if needed)

**Option B: Manual Copy (Terminal)**
```bash
# From this directory
cp vibesrails.yaml /path/to/your/project/
cp CLAUDE.md /path/to/your/project/
mkdir -p /path/to/your/project/.claude
cp .claude/hooks.json /path/to/your/project/.claude/
```

### Step 3: Install Git Hook

```bash
cd your-project
vibesrails --hook
```

## What You Get

### 🔒 Security Scanning (Automatic)
- Blocks commits with hardcoded secrets
- Detects SQL injection risks
- Catches command injection vulnerabilities
- Warns about debug mode in production

### 🤖 Claude Code Integration
- **SessionStart**: Shows active plan + current task
- **PreCompact**: Auto-saves state before context compaction
- **PostToolUse**: Reminds about security scanning on first Write

### 📊 Code Quality Warnings
- Star imports detection
- Print statements (suggest logging)
- Bare except clauses
- TODO comments tracking

## Verify Setup

### 1. Check Files Are Copied
```bash
cd your-project
ls -la vibesrails.yaml CLAUDE.md .claude/hooks.json
```

### 2. Test Security Scan
```bash
vibesrails --all
```

### 3. Test Git Hook
```bash
echo "api_key = 'secret123'" > test_security.py
git add test_security.py
git commit -m "test"
# Should BLOCK with security warning!
rm test_security.py
```

## Quick Commands

```bash
# Scan everything
vibesrails --all

# View configured patterns
vibesrails --show

# Scan on file save (live mode)
vibesrails --watch

# AI pattern discovery
vibesrails --learn

# Auto-fix issues
vibesrails --fix --dry-run  # Preview
vibesrails --fix            # Apply

# View statistics
vibesrails --stats
```

## Customization

### Add Your Own Patterns

Edit `vibesrails.yaml`:

```yaml
blocking:
  - id: my_custom_rule
    name: "My Custom Security Rule"
    regex: "dangerous_pattern"
    message: "Explanation for developers"
```

**Validate:**
```bash
vibesrails --validate
```

### Adjust Hooks

Edit `.claude/hooks.json`:
- Add/remove SessionStart commands
- Customize PreCompact auto-save
- Adjust PostToolUse behavior

### Modify CLAUDE.md

Add project-specific security guidelines or coding standards.

## Troubleshooting

### vibesrails command not found
```bash
# Try module invocation
python -m vibesrails --version

# Or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Git hook not working
```bash
# Check hook exists
cat .git/hooks/pre-commit

# Reinstall
vibesrails --hook --force
```

### Hooks not triggering in Claude Code
- Verify `.claude/hooks.json` has correct permissions
- Check JSON syntax: `python -m json.tool .claude/hooks.json`
- Restart Claude Code

### False positive blocking commit
```bash
# Option 1: Add exception in vibesrails.yaml
exceptions:
  my_case:
    patterns: ["path/to/file.py"]
    allowed: ["pattern_id"]
    reason: "Why this is safe"

# Option 2: Bypass once (use sparingly!)
git commit --no-verify
```

## Architecture

```
vibesrails.yaml          ← Security patterns (single source of truth)
       │
       ├──→ vibesrails    ← Scanner (streaming line-by-line)
       │                     - Memory-safe
       │                     - Dual-engine (regex + semgrep)
       │
       ├──→ git hook       ← Runs on commit
       │                     - Scans staged files
       │                     - Blocks if issues found
       │
       └──→ CLAUDE.md      ← Instructions for Claude Code
                              - Context for AI coding
                              - Security guidelines
```

## What Makes This Professional

✅ **Drag & Drop Ready** - No scripts to run, just copy files
✅ **Zero Config** - Works out of the box with sensible defaults
✅ **Memory-Safe** - Streaming architecture handles any file size
✅ **AI-Powered** - Claude integration for smart coding
✅ **Extensible** - Easy to customize patterns and hooks
✅ **Git Integrated** - Pre-commit hook automation
✅ **Multi-Engine** - Regex (fast) + Semgrep (semantic)

## Next Steps

1. **Customize patterns** - Edit `vibesrails.yaml` for project-specific rules
2. **Try AI discovery** - Run `vibesrails --learn` to find patterns
3. **Enable live mode** - Run `vibesrails --watch` during development
4. **Check metrics** - Run `vibesrails --stats` to see scan history
5. **Share with team** - Commit these files so everyone has same setup

## Support

- **Docs**: https://github.com/VictoHughes/VIBESRAILS
- **Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Coffee**: https://buymeacoffee.com/vibesrails

---

**Ship fast. Ship safe. 🚀**
