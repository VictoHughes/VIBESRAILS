# VibesRails - Installation Guide

> Security scanner + Claude Code integration bundle

## What Gets Installed

VibesRails installs **two things**:

| Component | What it does |
|-----------|-------------|
| **vibesrails** (pip) | Security scanner - scans code for secrets, injection, quality issues |
| **Claude Code config** (files) | Hooks, instructions, patterns - makes Claude Code security-aware |

### Files copied to your project

```
your-project/
├── vibesrails.yaml       # Security patterns (blocking + warnings)
├── CLAUDE.md             # Instructions for Claude Code sessions
├── .claude/
│   └── hooks.json        # Session automation (plans, tasks, scan reminders)
└── .git/hooks/
    └── pre-commit        # Auto-scan on every commit
```

## Quick Install

### Option 1: `vibesrails --setup` (recommended)

```bash
pip install vibesrails
cd your-project
vibesrails --setup
```

This single command creates **all 4 files** automatically:
- Detects your project type (Django, FastAPI, Flask, etc.)
- Generates `vibesrails.yaml` with relevant patterns
- Creates `CLAUDE.md` with instructions for Claude Code
- Installs `.claude/hooks.json` for session automation
- Sets up `.git/hooks/pre-commit` for auto-scanning

### Option 2: Installer script

**Mac/Linux:**
```bash
cd your-project
/path/to/vibesrails/installers/unix/claude-code/install.sh .
```

**Any OS (Python):**
```bash
cd your-project
python /path/to/vibesrails/installers/cross-platform/claude-code/install.py .
```

### Option 3: Drag & Drop

1. `pip install vibesrails`
2. Copy these 3 files from `installers/templates/claude-code/` to your project root:
   - `vibesrails.yaml`
   - `CLAUDE.md`
   - `.claude/hooks.json` (create `.claude/` folder first)
3. Run `vibesrails --hook` in your project

## What Claude Code Does After Install

The hooks in `.claude/hooks.json` give Claude Code these behaviors:

| Hook | Trigger | Effect |
|------|---------|--------|
| **SessionStart** | Opening Claude Code | Shows active plan + current task |
| **PreCompact** | Before context compaction | Auto-saves task state |
| **PostToolUse** (Write) | First file edit | Reminds about security scanning |
| **PostToolUse** (Bash) | After commands | Detects new commits |

## Verify Installation

```bash
# Check scanner works
vibesrails --all

# Check files exist
ls vibesrails.yaml CLAUDE.md .claude/hooks.json

# Test the git hook (should block)
echo "api_key = 'secret123'" > test_check.py
git add test_check.py
git commit -m "test"     # Should be blocked!
rm test_check.py
git reset HEAD test_check.py 2>/dev/null
```

## After Install

```bash
vibesrails --all        # Scan entire project
vibesrails --show       # View configured patterns
vibesrails --watch      # Live scanning on file save
vibesrails --learn      # AI-powered pattern discovery
vibesrails --stats      # View scan statistics
vibesrails --fix        # Auto-fix simple issues
```

## Customization

- **Add security patterns**: Edit `vibesrails.yaml`
- **Change Claude behavior**: Edit `.claude/hooks.json`
- **Add project instructions**: Edit `CLAUDE.md`

## Installer Directory Structure

```
installers/
├── README.md                          # This file
├── unix/claude-code/install.sh        # Mac/Linux script
├── cross-platform/claude-code/install.py  # Python script (any OS)
├── templates/claude-code/             # Source templates
│   ├── vibesrails.yaml
│   ├── CLAUDE.md
│   └── .claude/hooks.json
└── complete-package/claude-code/      # Ready-to-copy bundle + README
```

## Support

- **GitHub**: https://github.com/VictoHughes/VIBESRAILS
- **Issues**: https://github.com/VictoHughes/VIBESRAILS/issues

---

**Ship fast. Ship safe.**
