# VibesRails - Complete Installation Package

**Everything your teammate needs in one folder!**

This package includes:
- ✅ VibesRails 1.3.0 (wheel file - no internet needed)
- ✅ Ready-to-use templates (config + hooks)
- ✅ Automated installation scripts (Unix + Windows)
- ✅ Complete documentation

## What's Inside

```
complete-package/
├── vibesrails-1.3.0-py3-none-any.whl  # VibesRails package (85KB)
├── INSTALL.sh                          # Unix/Mac installer
├── INSTALL.bat                         # Windows installer
├── README.md                           # This file
└── claude-code/                        # Templates
    ├── vibesrails.yaml                 # Security patterns
    ├── CLAUDE.md                       # Claude Code instructions
    ├── .claude/hooks.json              # Automation hooks
    └── README.md                       # Template guide
```

## Installation (Super Simple!)

### Unix/macOS

```bash
cd your-project
bash /path/to/INSTALL.sh .
```

**Or specify project path:**
```bash
bash /path/to/INSTALL.sh /path/to/your/project
```

### Windows

```cmd
cd your-project
"C:\path\to\INSTALL.bat" .
```

**Or specify project path:**
```cmd
"C:\path\to\INSTALL.bat" C:\path\to\your\project
```

## What the Installer Does

**[1/3] Install VibesRails**
- Installs from included wheel file (no internet needed)
- Installs dependencies (pyyaml, semgrep)
- Verifies installation

**[2/3] Copy Templates**
- `vibesrails.yaml` → Security patterns config
- `CLAUDE.md` → Claude Code instructions
- `.claude/hooks.json` → Automation hooks
- Creates `.git` if needed

**[3/3] Install Git Hook**
- Runs `vibesrails --hook`
- Creates `.git/hooks/pre-commit`
- Enables automatic scanning on commit

## Manual Installation (If Scripts Don't Work)

### Step 1: Install VibesRails

```bash
# Unix/macOS
python3 -m pip install vibesrails-1.3.0-py3-none-any.whl

# Windows
python -m pip install vibesrails-1.3.0-py3-none-any.whl
```

### Step 2: Copy Templates

```bash
# Unix/macOS
cp claude-code/vibesrails.yaml your-project/
cp claude-code/CLAUDE.md your-project/
mkdir -p your-project/.claude
cp claude-code/.claude/hooks.json your-project/.claude/

# Windows
copy claude-code\vibesrails.yaml your-project\
copy claude-code\CLAUDE.md your-project\
mkdir your-project\.claude
copy claude-code\.claude\hooks.json your-project\.claude\
```

### Step 3: Install Git Hook

```bash
cd your-project
vibesrails --hook
```

## Verify Installation

### 1. Check VibesRails is Installed

```bash
vibesrails --version
# Should show: vibesrails 1.3.0
```

### 2. Check Files Are Copied

```bash
ls -la vibesrails.yaml CLAUDE.md .claude/hooks.json
```

### 3. Run a Security Scan

```bash
vibesrails --all
```

### 4. Test Git Hook

```bash
# Create a file with a security issue
echo "password = 'secret123'" > test_security.py

# Try to commit (should BLOCK)
git add test_security.py
git commit -m "test"

# Should show: BLOCK with security warning!

# Clean up
rm test_security.py
```

## Features You Get

### 🔒 Security Scanning (Automatic)
- **Hardcoded secrets** - Blocks API keys, passwords
- **SQL injection** - Detects unsafe queries
- **Command injection** - Catches unsafe system calls
- **Debug mode** - Warns if DEBUG=True in production

### 🤖 Claude Code Integration
- **SessionStart** - Shows active plan + current task
- **PreCompact** - Auto-saves state before compaction
- **PostToolUse** - Detects commits, reminds about scanning

### 📊 Code Quality
- Star import detection
- Print statement warnings (suggest logging)
- Bare except warnings
- TODO comment tracking

### ⚡ Performance
- Memory-safe streaming (handles files of any size)
- 233KB scanned in 0.02s with 20.4MB memory
- Timeout protection (60s default)

## Quick Commands

```bash
# Scan everything
vibesrails --all

# View patterns
vibesrails --show

# Live mode (scan on save)
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

### Add Your Own Security Patterns

Edit `vibesrails.yaml`:

```yaml
blocking:
  - id: my_custom_rule
    name: "My Custom Security Check"
    regex: "dangerous_pattern_here"
    message: "Why this is dangerous and how to fix it"
```

**Validate:**
```bash
vibesrails --validate
```

### Modify Automation Hooks

Edit `.claude/hooks.json`:
- Add/remove SessionStart commands
- Customize PreCompact behavior
- Adjust PostToolUse triggers

### Update CLAUDE.md

Add project-specific:
- Security guidelines
- Coding standards
- Best practices

## Troubleshooting

### vibesrails command not found

```bash
# Try module invocation
python -m vibesrails --version

# Add to PATH (Unix/macOS)
export PATH="$HOME/.local/bin:$PATH"

# Or use full path
~/.local/bin/vibesrails --version
```

### Wheel installation fails

```bash
# Install dependencies first
pip install pyyaml semgrep

# Then install wheel
pip install vibesrails-1.3.0-py3-none-any.whl --force-reinstall
```

### Git hook not triggering

```bash
# Check hook exists
cat .git/hooks/pre-commit

# Check permissions (Unix/macOS)
chmod +x .git/hooks/pre-commit

# Reinstall
vibesrails --hook --force
```

### Permission errors

```bash
# Install for user only
pip install --user vibesrails-1.3.0-py3-none-any.whl
```

### Python version too old

VibesRails requires Python 3.10+:

```bash
# Check version
python --version

# Update Python
# macOS: brew install python@3.10
# Ubuntu: sudo apt install python3.10
# Windows: Download from python.org
```

## System Requirements

- **Python**: 3.10+ (required)
- **pip**: Latest version recommended
- **git**: Required for hooks
- **Disk space**: ~100MB (includes dependencies)

**Platforms:**
- ✅ macOS 11.0+
- ✅ Linux (Ubuntu 20.04+, others)
- ✅ Windows 10+

## Package Contents Details

### vibesrails-1.3.0-py3-none-any.whl (85KB)

**Includes:**
- Dual-engine scanner (regex + semgrep)
- Memory-safe streaming architecture
- AI-powered pattern discovery
- Auto-fix capability
- Live watch mode
- Metrics tracking
- CLI with 15+ commands

**Dependencies (auto-installed):**
- pyyaml >= 6.0
- semgrep >= 1.45.0

### Templates (15KB total)

**vibesrails.yaml** - Pre-configured patterns:
- 4 blocking patterns (secrets, injections)
- 4 warning patterns (code quality)
- 2 exception sets (tests, config)

**CLAUDE.md** - Documentation:
- How VibesRails works
- Command reference
- Customization guide
- Troubleshooting

**.claude/hooks.json** - Automation:
- SessionStart hooks (3 commands + 1 prompt)
- PreCompact hook (auto-save)
- PostToolUse hooks (2 commands)

## Sharing This Package

### Create Zip for Distribution

```bash
cd installers/
zip -r vibesrails-complete-package.zip complete-package/
```

**Share via:**
- Email attachment
- Cloud storage (Dropbox, Google Drive)
- Company intranet
- USB drive
- GitHub release

### Size Information

- **Uncompressed**: ~1.2MB
- **Compressed (zip)**: ~450KB
- **Download time**: <5 seconds on typical connection

## Support

- **GitHub**: https://github.com/VictoHughes/VIBESRAILS
- **Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Discussions**: https://github.com/VictoHughes/VIBESRAILS/discussions
- **Buy Me a Coffee**: https://buymeacoffee.com/vibesrails

## What Makes This Professional

✅ **Zero Internet Required** - Wheel + templates included
✅ **Automated Scripts** - One command installation
✅ **Cross-Platform** - Unix/Mac + Windows scripts
✅ **Manual Fallback** - Step-by-step instructions
✅ **Complete Documentation** - Everything explained
✅ **Verification Tests** - Confirm installation works
✅ **Troubleshooting** - Solutions for common issues

## Version Information

- **VibesRails**: 1.3.0
- **Python Required**: 3.10+
- **Package Date**: January 2026
- **Package Type**: Complete (offline-ready)

---

**Ship fast. Ship safe. 🚀**
