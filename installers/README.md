# VibesRails Installers

Professional security scanner with AI-powered pattern discovery and auto-fix capabilities.

## What VibesRails Does

**Core Functionality:**
- 🔍 **Pattern-based scanning** - Regex + Semgrep dual-engine detection
- 🤖 **AI-powered learning** - Claude discovers patterns from your codebase
- 🔧 **Auto-fix** - Automated fixes for simple patterns
- 📊 **Metrics & Stats** - Track scan history and AI coding blocks
- 👁️ **Live watch mode** - Real-time scanning on file save
- 🎯 **YAML-driven** - Single source of truth for all patterns

**Memory-Safe Architecture:**
- Streaming line-by-line file processing (handles files of any size)
- Timeout protection (60s default)
- Performance logging (track time/memory/files scanned)

## Installation Methods

### By Operating System

| OS | Folder | Scripts |
|----|--------|---------|
| **Linux/macOS** | [unix/](./unix/) | `.sh` |
| **Windows** | [windows/](./windows/) | `.bat` |
| **Any** | [cross-platform/](./cross-platform/) | `.py` |

### By Installation Type

| Type | Description | Use Case |
|------|-------------|----------|
| **pip** | Standard installation | Production use |
| **source** | Development / latest | Contributing or testing |
| **claude-code** | Full integration | Claude Code + auto-setup |

## Quick Start

### Unix/Mac
```bash
# Standard installation
./unix/pip/install.sh

# Development from source
./unix/source/install.sh

# Claude Code integration
./unix/claude-code/install.sh
```

### Windows
```cmd
REM Standard installation
windows\pip\install.bat

REM Development from source
windows\source\install.bat

REM Claude Code integration
windows\claude-code\install.bat
```

### Cross-Platform (Python)
```bash
# Standard installation
python cross-platform/pip/install.py

# Development from source
python cross-platform/source/install.py

# Claude Code integration
python cross-platform/claude-code/install.py
```

## After Installation

### 1. Initialize Your Project
```bash
cd your-project
vibesrails --setup
```

The `--setup` command intelligently:
- Detects your project type
- Creates `vibesrails.yaml` with relevant patterns
- Installs git pre-commit hook
- Suggests Claude Code skill integration

### 2. Scan Your Code
```bash
vibesrails              # Scan staged files (default)
vibesrails --all        # Scan entire project
vibesrails --file path  # Scan specific file
```

### 3. Explore Features
```bash
vibesrails --show       # Show all configured patterns
vibesrails --stats      # View scan statistics
vibesrails --watch      # Live scanning on file save
vibesrails --learn      # AI-powered pattern discovery
```

## Available Commands

### Scanning
- `vibesrails` - Scan staged files (git commit workflow)
- `vibesrails --all` - Scan all Python files in project
- `vibesrails --file FILE` - Scan specific file
- `vibesrails --watch` - Live scanning mode (watches file changes)

### Configuration
- `vibesrails --init` - Create fresh `vibesrails.yaml`
- `vibesrails --setup` - Smart auto-setup (recommended)
- `vibesrails --validate` - Validate YAML config
- `vibesrails --show` - Display all patterns
- `vibesrails --config PATH` - Use custom config file

### Git Integration
- `vibesrails --hook` - Install git pre-commit hook
- `vibesrails --uninstall` - Remove from project (keeps config)

### AI Features
- `vibesrails --learn` - Claude-powered pattern discovery
- `vibesrails --guardian-stats` - Show AI coding block statistics

### Auto-Fix
- `vibesrails --fix` - Automatically fix simple patterns
- `vibesrails --dry-run` - Preview what `--fix` would change
- `vibesrails --fixable` - List auto-fixable patterns
- `vibesrails --no-backup` - Skip `.bak` files (use with caution)

### Metrics
- `vibesrails --stats` - View detailed scan statistics
- Tracks: scans per day, patterns hit, file coverage, trends

## Architecture

```
vibesrails.yaml         ← Single source of truth
       ├── Regex patterns (fast, lightweight)
       └── Semgrep rules (deep semantic analysis)

Scanner (streaming line-by-line)
       ├── Memory-safe for any file size
       ├── Dual-engine: regex + semgrep
       └── Performance logging

Git Hook (pre-commit)
       └── Runs automatically on commit

Claude Code Skill
       └── Guides AI coding practices
```

## System Requirements

- **Python**: 3.10+ (required)
- **pip**: Latest version recommended
- **git**: Required for `--hook` and source installation
- **semgrep**: Auto-installed as dependency

**Supported Platforms:**
- Linux (tested on Ubuntu 20.04+)
- macOS (tested on 11.0+)
- Windows (tested on Windows 10+)

## Performance

**Streaming Architecture:**
- 233KB file scanned in 0.02s with 20.4MB memory (constant)
- No file size limits (line-by-line processing)
- Timeout protection (60s default)

**Typical Scan Times:**
- Small project (<100 files): <1 second
- Medium project (100-1000 files): 1-5 seconds
- Large project (1000+ files): 5-30 seconds

## Troubleshooting

### Command not found
```bash
# Try module invocation
python -m vibesrails --version

# Or reinstall
pip install --user --force-reinstall vibesrails
```

### Permission denied
```bash
pip install --user vibesrails
```

### Semgrep not working
```bash
# Check semgrep installation
semgrep --version

# Reinstall if needed
pip install --upgrade semgrep
```

### Git hook not triggering
```bash
# Check hook is installed
cat .git/hooks/pre-commit

# Reinstall hook
vibesrails --hook --force
```

## What Makes VibesRails Professional

1. **Dual-Engine Detection** - Regex (fast) + Semgrep (semantic)
2. **Memory-Safe Streaming** - Handles files of any size
3. **AI-Powered Learning** - Discovers patterns from your code
4. **Auto-Fix Capability** - Fixes simple issues automatically
5. **Comprehensive Metrics** - Track scans, blocks, trends
6. **Live Watch Mode** - Real-time feedback on file save
7. **YAML-Driven Config** - Single source of truth
8. **Git Integration** - Pre-commit hook automation
9. **Claude Code Ready** - Native skill integration

## Support

- **Documentation**: [docs/](../docs/)
- **GitHub Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Buy Me a Coffee**: https://buymeacoffee.com/vibesrails

## License

MIT - Use it, fork it, improve it.

---

**Ship fast. Ship safe. 🚀**
