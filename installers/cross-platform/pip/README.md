# pip Installation (Cross-Platform)

Standard installation for production use.

## Quick Start

### Using Installer Script
```bash
python install.py
```

### Direct Installation
```bash
pip install vibesrails
```

### Verify Installation
```bash
vibesrails --version
```

## After Installation

### 1. Initialize Your Project
```bash
cd your-project
vibesrails --setup
```

The `--setup` command will:
- Detect your project type (Django, Flask, FastAPI, etc.)
- Create `vibesrails.yaml` with relevant security patterns
- Install git pre-commit hook automatically
- Suggest Claude Code skill integration

### 2. Start Scanning
```bash
# Scan staged files (pre-commit workflow)
vibesrails

# Scan entire project
vibesrails --all

# View configured patterns
vibesrails --show
```

### 3. Explore Features
```bash
# AI-powered pattern discovery
vibesrails --learn

# Live scanning on file save
vibesrails --watch

# View scan statistics
vibesrails --stats

# Auto-fix simple issues
vibesrails --fix --dry-run  # Preview first
vibesrails --fix            # Apply fixes
```

## What You Get

**Core Features:**
- ✅ Pattern-based security scanning (regex + semgrep)
- ✅ Git pre-commit hook integration
- ✅ Memory-safe streaming (handles files of any size)
- ✅ AI-powered pattern discovery (--learn)
- ✅ Auto-fix capability (--fix)
- ✅ Live watch mode (--watch)
- ✅ Comprehensive metrics (--stats)
- ✅ YAML-driven configuration

**Performance:**
- Scans 233KB files in 0.02s with 20.4MB memory
- No file size limits (streaming architecture)
- Timeout protection (60s default)

## Troubleshooting

### Command not found

If `vibesrails` command is not found after installation:

```bash
# Try module invocation
python -m vibesrails --version

# Add user bin to PATH (macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"

# Or use full path
~/.local/bin/vibesrails --version
```

### Permission denied

If you get permission errors:

```bash
pip install --user vibesrails
```

### Python version error

VibesRails requires Python 3.10+:

```bash
# Check your Python version
python --version

# If too old, install Python 3.10+
# macOS: brew install python@3.10
# Ubuntu: sudo apt install python3.10
# Windows: Download from python.org
```

### Upgrade to latest version

```bash
pip install --upgrade vibesrails
```

## Configuration

After installation, customize `vibesrails.yaml`:

```yaml
version: "1.0"

blocking:
  - id: hardcoded_secret
    name: "Hardcoded Secret"
    regex: "(password|api_key)\\s*=\\s*[\"'][^\"']{4,}"
    flags: "i"
    message: "Move secrets to environment variables"

warning:
  - id: star_import
    name: "Star Import"
    regex: "from\\s+\\S+\\s+import\\s+\\*"
    message: "Consider explicit imports for clarity"
    skip_in_tests: true

exceptions:
  test_files:
    patterns: ["test_*.py", "*_test.py"]
    allowed: ["hardcoded_secret"]
    reason: "Tests can mock sensitive data"
```

## Available Commands

**Scanning:**
- `vibesrails` - Scan staged files
- `vibesrails --all` - Scan all Python files
- `vibesrails --file path.py` - Scan specific file
- `vibesrails --watch` - Live scanning mode

**Configuration:**
- `vibesrails --init` - Create fresh config
- `vibesrails --setup` - Smart auto-setup (recommended)
- `vibesrails --validate` - Validate config
- `vibesrails --show` - Display patterns

**Git Integration:**
- `vibesrails --hook` - Install pre-commit hook
- `vibesrails --uninstall` - Remove from project

**AI Features:**
- `vibesrails --learn` - Discover patterns with Claude
- `vibesrails --guardian-stats` - AI coding statistics

**Auto-Fix:**
- `vibesrails --fix` - Auto-fix issues
- `vibesrails --dry-run` - Preview changes
- `vibesrails --fixable` - List fixable patterns

**Metrics:**
- `vibesrails --stats` - View scan statistics

## Next Steps

1. **Read the docs**: [../../docs/](../../docs/)
2. **Join Discord**: (coming soon)
3. **Star on GitHub**: https://github.com/VictoHughes/VIBESRAILS
4. **Support development**: https://buymeacoffee.com/vibesrails

## Uninstallation

To remove VibesRails from your project (keeps config):

```bash
vibesrails --uninstall
```

To completely uninstall:

```bash
pip uninstall vibesrails
```

---

**Ship fast. Ship safe. 🚀**
